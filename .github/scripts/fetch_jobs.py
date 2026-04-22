"""
Fetches job listings from Teamtailor and Homerun, merges them into
a single normalized jobs.json consumed by joblisting/index.html.
"""

import json
import os
import sys
from datetime import datetime, timezone

import requests

TEAMTAILOR_BASE = "https://api.teamtailor.com/v1"
HOMERUN_BASE = "https://api.homerun.co/v2"


def fetch_teamtailor(api_key: str) -> tuple[list[dict], dict]:
    """Returns (jobs, raw_first_job) for debugging."""
    first_url = f"{TEAMTAILOR_BASE}/jobs"

    # Step 1: find which auth format works
    auth_candidates = [
        {"Authorization": f'Token token="{api_key}"', "X-Api-Version": "20210218"},
        {"Authorization": f'Token token="{api_key}"'},
        {"Authorization": f"Bearer {api_key}"},
    ]
    working_headers = None
    for hdrs in auth_candidates:
        resp = requests.get(first_url, headers=hdrs, timeout=15)
        print(f"Teamtailor auth probe → {resp.status_code}", file=sys.stderr)
        if resp.ok:
            working_headers = hdrs
            break
        print(f"  body: {resp.text[:300]}", file=sys.stderr)

    if working_headers is None:
        raise RuntimeError("All Teamtailor auth attempts failed — check API key")

    # Step 2: find the best param combo that includes location/dept data
    param_candidates = [
        {"include": "department,locations"},                              # no page size
        {"include": "locations"},                                         # location only
        {"include": "department,locations", "page[size]": 30},           # smaller page
        {"include": "department,locations", "page[size]": 100},          # original
        {},                                                               # bare fallback
    ]
    use_params: dict = {}
    for p in param_candidates:
        r = requests.get(first_url, headers=working_headers, params=p, timeout=15)
        print(f"Teamtailor params {list(p.keys())} → {r.status_code}", file=sys.stderr)
        if r.ok:
            use_params = p
            # Check if included resources are actually present
            has_included = bool(r.json().get("included"))
            print(f"  has included={has_included}", file=sys.stderr)
            if has_included or not p:
                break
            # Keep trying for a combo that returns included data
    else:
        use_params = {}

    # Step 3: paginate and collect
    jobs: list[dict] = []
    raw_first: dict = {}
    url: str | None = first_url
    params = use_params.copy()

    while url:
        resp = requests.get(url, headers=working_headers, params=params, timeout=15)
        resp.raise_for_status()
        body = resp.json()

        included = {
            f"{item['type']}/{item['id']}": item
            for item in body.get("included", [])
        }

        for job in body.get("data", []):
            if not raw_first:
                raw_first = job  # save for debug

            attrs = job.get("attributes", {})
            rels  = job.get("relationships", {})
            links = job.get("links", {})

            dept = ""
            dept_ref = (rels.get("department") or {}).get("data") or {}
            if dept_ref:
                dept_item = included.get(f"departments/{dept_ref.get('id')}", {})
                dept = dept_item.get("attributes", {}).get("name", "")
            if not dept:
                dept = attrs.get("department-name", "")

            location = ""
            loc_refs = (rels.get("locations") or {}).get("data") or []
            if loc_refs:
                loc_item = included.get(f"locations/{loc_refs[0].get('id')}", {})
                loc_attrs = loc_item.get("attributes", {})
                city    = loc_attrs.get("city", "")
                country = loc_attrs.get("country", "") or loc_attrs.get("country-code", "")
                location = ", ".join(filter(None, [city, country]))
            if not location:
                location = attrs.get("location-name", "") or attrs.get("city", "")

            jobs.append({
                "id": f"tt-{job['id']}",
                "title": attrs.get("title", ""),
                "department": dept,
                "location": location,
                "url": links.get("careersite-job-url", ""),
                "source": "Teamtailor",
                "published_at": attrs.get("created-at", ""),
            })

        url = (body.get("links") or {}).get("next") or None
        params = {}

    return jobs, raw_first


def _parse_location(val) -> str:
    """Normalise a location field that may be a string, dict, or list."""
    if not val:
        return ""
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        city    = val.get("city") or val.get("name") or ""
        country = val.get("country") or val.get("country_name") or val.get("country_code") or ""
        return ", ".join(filter(None, [city, country]))
    if isinstance(val, list) and val:
        return _parse_location(val[0])
    return ""


def _parse_department(val) -> str:
    if not val:
        return ""
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        return val.get("name") or val.get("title") or ""
    return ""


def fetch_homerun(api_key: str) -> tuple[list[dict], dict]:
    bearer_headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    token_headers  = {"Authorization": f"Token {api_key}",  "Accept": "application/json"}

    endpoints = [
        ("https://api.homerun.co/v2/jobs",      bearer_headers),
        ("https://api.homerun.co/v1/jobs",       bearer_headers),
        ("https://api.homerun.co/v2/vacancies",  bearer_headers),
        ("https://api.homerun.co/v1/vacancies",  bearer_headers),
        ("https://api.homerun.co/v2/jobs",       token_headers),
        ("https://api.homerun.co/v1/jobs",       token_headers),
    ]

    working_url     = None
    working_headers = None
    for endpoint, hdrs in endpoints:
        try:
            resp = requests.get(endpoint, headers=hdrs, timeout=15)
            print(f"Homerun {endpoint} → {resp.status_code}", file=sys.stderr)
            if not resp.ok:
                print(f"  body: {resp.text[:300]}", file=sys.stderr)
                continue
            working_url     = endpoint
            working_headers = hdrs
            break
        except (requests.HTTPError, requests.ConnectionError):
            continue

    if working_url is None:
        raise RuntimeError("No working Homerun endpoint found")

    # Paginate through all pages
    jobs: list[dict] = []
    raw_first: dict = {}
    raw_first_detail: dict = {}
    page = 1

    while True:
        resp = requests.get(
            working_url,
            headers=working_headers,
            params={"page": page, "per_page": 100},
            timeout=15,
        )
        resp.raise_for_status()
        body = resp.json()

        # Capture first raw item + fetch its detail endpoint for debug
        if page == 1:
            raw_items_debug = body if isinstance(body, list) else (
                body.get("data") or body.get("jobs") or body.get("vacancies") or []
            )
            if raw_items_debug:
                raw_first = raw_items_debug[0]
                # Try to fetch individual job detail to see full field set
                first_id = raw_first.get("id", "")
                if first_id:
                    dr = requests.get(
                        f"{working_url}/{first_id}",
                        headers=working_headers, timeout=15,
                    )
                    print(f"Homerun detail/{first_id} → {dr.status_code}", file=sys.stderr)
                    if dr.ok:
                        raw_first_detail = dr.json()

        if isinstance(body, list):
            items    = body
            has_more = False  # no pagination info in plain list
        else:
            items = (
                body.get("data")
                or body.get("jobs")
                or body.get("vacancies")
                or []
            )
            meta     = body.get("meta") or {}
            has_more = (
                bool((body.get("links") or {}).get("next"))
                or (meta.get("current_page", page) < meta.get("last_page", page))
                or (len(items) == 100)
            )

        if not items:
            break

        for job in items:
            raw_loc  = (
                job.get("location")
                or job.get("city")
                or job.get("office")
                or job.get("location_name")
            )
            raw_dept = (
                job.get("department")
                or job.get("team")
                or job.get("category")
            )
            raw_url  = (
                job.get("url")
                or job.get("application_url")
                or job.get("job_url")
                or job.get("public_url")
                or job.get("link")
                or job.get("career_page_url")
            )

            jobs.append({
                "id":           f"hr-{job.get('id', '')}",
                "title":        job.get("title") or job.get("name", ""),
                "department":   _parse_department(raw_dept),
                "location":     _parse_location(raw_loc),
                "url":          raw_url or "",
                "source":       "Homerun",
                "published_at": job.get("published_at") or job.get("created_at", ""),
            })

        if not has_more:
            break
        page += 1

    return jobs, {"list_item": raw_first, "detail_item": raw_first_detail}


def main() -> None:
    tt_key = os.environ.get("TEAMTAILOR_API_KEY", "").strip()
    hr_key = os.environ.get("HOMERUN_API_KEY", "").strip()

    all_jobs: list[dict] = []
    errors: list[str] = []
    debug: dict = {}

    if tt_key:
        try:
            tt_jobs, tt_raw = fetch_teamtailor(tt_key)
            all_jobs.extend(tt_jobs)
            debug["teamtailor_first_raw"] = tt_raw
            print(f"Teamtailor: {len(tt_jobs)} jobs fetched")
        except Exception as exc:
            msg = f"Teamtailor fetch failed: {exc}"
            print(msg, file=sys.stderr)
            errors.append(msg)
    else:
        print("TEAMTAILOR_API_KEY not set — skipping", file=sys.stderr)

    if hr_key:
        try:
            hr_jobs, hr_raw = fetch_homerun(hr_key)
            all_jobs.extend(hr_jobs)
            debug["homerun_first_raw"] = hr_raw
            print(f"Homerun: {len(hr_jobs)} jobs fetched")
        except Exception as exc:
            msg = f"Homerun fetch failed: {exc}"
            print(msg, file=sys.stderr)
            errors.append(msg)
    else:
        print("HOMERUN_API_KEY not set — skipping", file=sys.stderr)

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(all_jobs),
        "jobs": all_jobs,
        "errors": errors if errors else None,
        "debug": debug,
    }

    out_path = "joblisting/jobs.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=2)

    print(f"Done — {len(all_jobs)} total jobs written to {out_path}")


if __name__ == "__main__":
    main()
