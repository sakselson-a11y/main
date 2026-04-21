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


def fetch_teamtailor(api_key: str) -> list[dict]:
    # Try progressively simpler requests to find what Teamtailor accepts
    attempts = [
        {
            "headers": {
                "Authorization": f'Token token="{api_key}"',
                "X-Api-Version": "20210218",
            },
            "params": {"include": "department,locations", "page[size]": 100},
        },
        {
            "headers": {
                "Authorization": f'Token token="{api_key}"',
                "X-Api-Version": "20210218",
            },
            "params": {},
        },
        {
            "headers": {"Authorization": f'Token token="{api_key}"'},
            "params": {},
        },
        {
            "headers": {"Authorization": f"Bearer {api_key}"},
            "params": {},
        },
    ]

    first_url = f"{TEAMTAILOR_BASE}/jobs"
    working_headers = None
    working_params: dict = {}

    for attempt in attempts:
        resp = requests.get(first_url, headers=attempt["headers"], params=attempt["params"], timeout=15)
        print(f"Teamtailor attempt headers={list(attempt['headers'].keys())} params={list(attempt['params'].keys())} → {resp.status_code}", file=sys.stderr)
        if not resp.ok:
            print(f"  body: {resp.text[:400]}", file=sys.stderr)
            continue
        working_headers = attempt["headers"]
        working_params = attempt["params"]
        break

    if working_headers is None:
        raise RuntimeError("All Teamtailor auth attempts failed — check API key")

    # Now paginate with the working configuration
    jobs: list[dict] = []
    url: str | None = first_url
    params = working_params.copy()

    while url:
        resp = requests.get(url, headers=working_headers, params=params, timeout=15)
        resp.raise_for_status()
        body = resp.json()

        included = {
            f"{item['type']}/{item['id']}": item
            for item in body.get("included", [])
        }

        for job in body.get("data", []):
            attrs = job.get("attributes", {})
            rels  = job.get("relationships", {})
            links = job.get("links", {})

            dept = ""
            dept_ref = (rels.get("department") or {}).get("data") or {}
            if dept_ref:
                dept_item = included.get(f"departments/{dept_ref.get('id')}", {})
                dept = dept_item.get("attributes", {}).get("name", "")

            location = ""
            loc_refs = (rels.get("locations") or {}).get("data") or []
            if loc_refs:
                loc_item = included.get(f"locations/{loc_refs[0].get('id')}", {})
                loc_attrs = loc_item.get("attributes", {})
                location = loc_attrs.get("city") or loc_attrs.get("name", "")

            # Fall back to attributes if include wasn't supported
            if not dept:
                dept = attrs.get("department-name", "")
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

    return jobs


def fetch_homerun(api_key: str) -> list[dict]:
    bearer_headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    token_headers = {
        "Authorization": f"Token {api_key}",
        "Accept": "application/json",
    }

    endpoints = [
        ("https://api.homerun.co/v2/jobs",       bearer_headers),
        ("https://api.homerun.co/v1/jobs",        bearer_headers),
        ("https://api.homerun.co/v2/vacancies",   bearer_headers),
        ("https://api.homerun.co/v1/vacancies",   bearer_headers),
        ("https://api.homerun.co/v2/jobs",        token_headers),
        ("https://api.homerun.co/v1/jobs",        token_headers),
    ]

    body = None
    for endpoint, hdrs in endpoints:
        try:
            resp = requests.get(endpoint, headers=hdrs, timeout=15)
            print(f"Homerun {endpoint} → {resp.status_code}", file=sys.stderr)
            if resp.status_code in (401, 403, 404, 405, 422):
                print(f"  body: {resp.text[:300]}", file=sys.stderr)
                continue
            resp.raise_for_status()
            body = resp.json()
            break
        except (requests.HTTPError, requests.ConnectionError):
            continue

    if body is None:
        raise RuntimeError("No working Homerun endpoint found")

    # Normalise: body may be a list or wrapped in data/jobs/vacancies
    if isinstance(body, list):
        items = body
    else:
        items = (
            body.get("data")
            or body.get("jobs")
            or body.get("vacancies")
            or []
        )

    jobs: list[dict] = []
    for job in items:
        jobs.append(
            {
                "id": f"hr-{job.get('id', '')}",
                "title": job.get("title") or job.get("name", ""),
                "department": job.get("department") or job.get("team", ""),
                "location": job.get("location") or job.get("city", ""),
                "url": (
                    job.get("url")
                    or job.get("application_url")
                    or job.get("link", "")
                ),
                "source": "Homerun",
                "published_at": job.get("published_at") or job.get("created_at", ""),
            }
        )

    return jobs


def main() -> None:
    tt_key = os.environ.get("TEAMTAILOR_API_KEY", "").strip()
    hr_key = os.environ.get("HOMERUN_API_KEY", "").strip()

    all_jobs: list[dict] = []
    errors: list[str] = []

    if tt_key:
        try:
            tt_jobs = fetch_teamtailor(tt_key)
            all_jobs.extend(tt_jobs)
            print(f"Teamtailor: {len(tt_jobs)} jobs fetched")
        except Exception as exc:
            msg = f"Teamtailor fetch failed: {exc}"
            print(msg, file=sys.stderr)
            errors.append(msg)
    else:
        print("TEAMTAILOR_API_KEY not set — skipping", file=sys.stderr)

    if hr_key:
        try:
            hr_jobs = fetch_homerun(hr_key)
            all_jobs.extend(hr_jobs)
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
    }

    out_path = "joblisting/jobs.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(output, fh, ensure_ascii=False, indent=2)

    print(f"Done — {len(all_jobs)} total jobs written to {out_path}")


if __name__ == "__main__":
    main()
