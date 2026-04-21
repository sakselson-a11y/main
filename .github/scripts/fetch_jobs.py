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
    headers = {
        "Authorization": f'Token token="{api_key}"',
        "X-Api-Version": "20210218",
        "Content-Type": "application/vnd.api+json",
    }
    jobs: list[dict] = []
    url = f"{TEAMTAILOR_BASE}/jobs"
    params: dict = {
        "filter[status]": "open",
        "include": "department,locations",
        "page[size]": 100,
    }

    while url:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        body = resp.json()

        # Build lookup for included resources
        included = {
            f"{item['type']}/{item['id']}": item
            for item in body.get("included", [])
        }

        for job in body.get("data", []):
            attrs = job.get("attributes", {})
            rels = job.get("relationships", {})
            links = job.get("links", {})

            dept = ""
            dept_ref = rels.get("department", {}).get("data") or {}
            if dept_ref:
                dept_item = included.get(f"departments/{dept_ref.get('id')}", {})
                dept = dept_item.get("attributes", {}).get("name", "")

            location = ""
            loc_refs = rels.get("locations", {}).get("data") or []
            if loc_refs:
                loc_item = included.get(f"locations/{loc_refs[0].get('id')}", {})
                loc_attrs = loc_item.get("attributes", {})
                location = loc_attrs.get("city") or loc_attrs.get("name", "")

            jobs.append(
                {
                    "id": f"tt-{job['id']}",
                    "title": attrs.get("title", ""),
                    "department": dept,
                    "location": location,
                    "url": links.get("careersite-job-url", ""),
                    "source": "Teamtailor",
                    "published_at": attrs.get("created-at", ""),
                }
            )

        # Follow pagination
        url = body.get("links", {}).get("next") or None
        params = {}

    return jobs


def fetch_homerun(api_key: str) -> list[dict]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    # Try v2 first, fall back to v1
    for endpoint in [f"{HOMERUN_BASE}/jobs", "https://api.homerun.co/v1/jobs"]:
        try:
            resp = requests.get(endpoint, headers=headers, timeout=15)
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            body = resp.json()
            break
        except requests.HTTPError:
            continue
    else:
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
