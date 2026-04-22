"""
Fetches job listings from Teamtailor and Homerun, merges them into
a single normalized jobs.json consumed by joblisting/index.html.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

import requests

LOCATION_CORRECTIONS = {
    "Rotterdan": "Rotterdam",
}


def _correct_location(loc: str) -> str:
    for wrong, right in LOCATION_CORRECTIONS.items():
        loc = loc.replace(wrong, right)
    return loc


SCRAPE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
}


def _extract_job_posting(data: dict | list) -> dict | None:
    """Recursively find a JobPosting node in a JSON-LD tree."""
    if isinstance(data, list):
        for item in data:
            found = _extract_job_posting(item)
            if found:
                return found
    elif isinstance(data, dict):
        if data.get("@type") == "JobPosting":
            return data
        # Handle @graph wrapper
        for val in data.values():
            if isinstance(val, (dict, list)):
                found = _extract_job_posting(val)
                if found:
                    return found
    return None


def scrape_job_page(job_url: str) -> tuple[str, str]:
    """Fetch a Homerun job page and return (location, department)."""
    if not job_url:
        return "", ""
    try:
        resp = requests.get(job_url, headers=SCRAPE_HEADERS, timeout=15)
        if not resp.ok:
            print(f"  scrape {job_url} → {resp.status_code}", file=sys.stderr)
            return "", ""

        html = resp.text
        location   = ""
        department = ""

        # 1. JSON-LD blocks (handles @graph, nested arrays, plain JobPosting)
        ld_pattern = r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        for raw in re.findall(ld_pattern, html, re.DOTALL | re.IGNORECASE):
            try:
                posting = _extract_job_posting(json.loads(raw.strip()))
            except ValueError:
                continue
            if not posting:
                continue

            if not location:
                loc = posting.get("jobLocation") or {}
                if isinstance(loc, list):
                    loc = loc[0] if loc else {}
                addr    = loc.get("address") or {}
                city    = addr.get("addressLocality", "")
                country = addr.get("addressCountry", "")
                location = ", ".join(filter(None, [city, country]))
                if location:
                    print(f"  scraped location via JSON-LD: {location}", file=sys.stderr)

            if not department:
                cat = posting.get("occupationalCategory") or ""
                if isinstance(cat, list):
                    cat = cat[0] if cat else ""
                department = str(cat).strip()
                if department:
                    print(f"  scraped department via JSON-LD: {department}", file=sys.stderr)

            if location and department:
                return location, department

        # 2. Bare JSON properties anywhere in the page
        if not location:
            m_city = re.search(r'"addressLocality"\s*:\s*"([^"]+)"', html)
            if m_city:
                city = m_city.group(1)
                m_country = re.search(r'"addressCountry"\s*:\s*"([^"]+)"', html)
                country = m_country.group(1) if m_country else ""
                location = ", ".join(filter(None, [city, country]))
                if location:
                    print(f"  scraped location via regex: {location}", file=sys.stderr)

        if not department:
            m_dept = re.search(r'"occupationalCategory"\s*:\s*"([^"]+)"', html)
            if m_dept:
                department = m_dept.group(1).strip()
                if department:
                    print(f"  scraped department via regex: {department}", file=sys.stderr)

        # 3. Meta tags for location
        if not location:
            for pattern in [
                r'<meta[^>]+name=["\']location["\'][^>]+content=["\']([^"\']+)["\']',
                r'<meta[^>]+property=["\']og:location["\'][^>]+content=["\']([^"\']+)["\']',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']location["\']',
            ]:
                m = re.search(pattern, html, re.IGNORECASE)
                if m:
                    location = m.group(1).strip()
                    if location:
                        print(f"  scraped location via meta: {location}", file=sys.stderr)
                        break

        # 4. Homerun HTML patterns for location
        if not location:
            for pattern in [
                r'class=["\'][^"\']*location[^"\']*["\'][^>]*>\s*<[^>]+>\s*([^<]{3,60})</[^>]+>',
                r'class=["\'][^"\']*location[^"\']*["\'][^>]*>\s*([^<]{3,60})</',
                r'data-location=["\']([^"\']+)["\']',
            ]:
                m = re.search(pattern, html, re.IGNORECASE)
                if m:
                    result = m.group(1).strip()
                    if result and len(result) < 60:
                        location = result
                        print(f"  scraped location via HTML pattern: {location}", file=sys.stderr)
                        break

        # 5. Homerun HTML patterns for department
        if not department:
            for pattern in [
                r'class=["\'][^"\']*department[^"\']*["\'][^>]*>\s*<[^>]+>\s*([^<]{2,60})</[^>]+>',
                r'class=["\'][^"\']*department[^"\']*["\'][^>]*>\s*([^<]{2,60})</',
                r'class=["\'][^"\']*team[^"\']*["\'][^>]*>\s*([^<]{2,60})</',
                r'class=["\'][^"\']*category[^"\']*["\'][^>]*>\s*([^<]{2,60})</',
                r'data-department=["\']([^"\']+)["\']',
                r'data-team=["\']([^"\']+)["\']',
            ]:
                m = re.search(pattern, html, re.IGNORECASE)
                if m:
                    result = m.group(1).strip()
                    if result and len(result) < 60:
                        department = result
                        print(f"  scraped department via HTML pattern: {department}", file=sys.stderr)
                        break

        if not location:
            print(f"  no location found for {job_url}", file=sys.stderr)

    except Exception as exc:
        print(f"  scrape error for {job_url}: {exc}", file=sys.stderr)
        return "", ""
    return location, department

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
                raw_first = job

            attrs = job.get("attributes", {})
            rels  = job.get("relationships", {})
            links = job.get("links", {})

            # Department — try included first, then fetch directly
            dept = ""
            dept_ref = (rels.get("department") or {}).get("data") or {}
            if dept_ref:
                dept_item = included.get(f"departments/{dept_ref.get('id')}", {})
                dept = dept_item.get("attributes", {}).get("name", "")
            if not dept:
                dept_url = ((rels.get("department") or {}).get("links") or {}).get("related", "")
                if dept_url:
                    dr = requests.get(dept_url, headers=working_headers, timeout=10)
                    if dr.ok:
                        dd = dr.json().get("data") or {}
                        dept = (dd.get("attributes") or {}).get("name", "")

            # Location — try included first, then fetch directly
            location = ""
            loc_refs = (rels.get("locations") or {}).get("data") or []
            if loc_refs:
                loc_item = included.get(f"locations/{loc_refs[0].get('id')}", {})
                loc_attrs = loc_item.get("attributes", {})
                if loc_attrs:
                    city    = loc_attrs.get("city", "")
                    country = loc_attrs.get("country", "") or loc_attrs.get("country-code", "")
                    location = ", ".join(filter(None, [city, country]))
            if not location:
                loc_url = ((rels.get("locations") or {}).get("links") or {}).get("related", "")
                if loc_url:
                    lr = requests.get(loc_url, headers=working_headers, timeout=10)
                    if lr.ok:
                        ld = lr.json().get("data") or []
                        if ld:
                            la = (ld[0].get("attributes") or {}) if isinstance(ld, list) else (ld.get("attributes") or {})
                            city    = la.get("city", "")
                            country = la.get("country", "") or la.get("country-code", "")
                            location = ", ".join(filter(None, [city, country]))

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


def fetch_homerun(api_key: str, overrides: dict) -> tuple[list[dict], dict]:
    bearer_headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    token_headers  = {"Authorization": f"Token {api_key}",  "Accept": "application/json"}
    no_headers     = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}

    # Try public career-page JSON feeds first — these include location data
    # Extract company slug from the API key prefix or try known slug "varo"
    public_feeds = [
        ("https://varo.homerun.co/jobs.json",      no_headers),
        ("https://varo.homerun.co/vacancies.json",  no_headers),
        ("https://varo.homerun.co/feed.json",       no_headers),
    ]
    authenticated = [
        ("https://api.homerun.co/v2/jobs",      bearer_headers),
        ("https://api.homerun.co/v1/jobs",       bearer_headers),
        ("https://api.homerun.co/v2/vacancies",  bearer_headers),
        ("https://api.homerun.co/v1/vacancies",  bearer_headers),
        ("https://api.homerun.co/v2/jobs",       token_headers),
        ("https://api.homerun.co/v1/jobs",       token_headers),
    ]

    working_url     = None
    working_headers = None
    for endpoint, hdrs in public_feeds + authenticated:
        try:
            resp = requests.get(endpoint, headers=hdrs, timeout=15)
            print(f"Homerun {endpoint} → {resp.status_code}", file=sys.stderr)
            if not resp.ok:
                print(f"  body: {resp.text[:300]}", file=sys.stderr)
                continue
            # Verify it's actually JSON before accepting
            try:
                resp.json()
            except ValueError:
                print(f"  not JSON, skipping", file=sys.stderr)
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
            raw_url = (
                job.get("job_url")
                or job.get("url")
                or job.get("application_url")
                or job.get("public_url")
                or job.get("link")
                or job.get("career_page_url")
                or ""
            )

            # Try API fields first; fall back to scraping the job page
            api_loc  = _parse_location(job.get("location") or job.get("city") or job.get("office"))
            api_dept = _parse_department(job.get("department") or job.get("team") or job.get("category"))

            scraped_loc, scraped_dept = ("", "")
            if not api_loc or not api_dept:
                scraped_loc, scraped_dept = scrape_job_page(raw_url)

            raw_loc  = _correct_location(api_loc or overrides.get(job.get("id", "")) or scraped_loc)
            raw_dept = api_dept or scraped_dept

            jobs.append({
                "id":           f"hr-{job.get('id', '')}",
                "title":        job.get("title") or job.get("name", ""),
                "department":   raw_dept,
                "location":     raw_loc,
                "url":          raw_url,
                "source":       "Homerun",
                "published_at": job.get("published_at") or job.get("created_at", ""),
            })

        if not has_more:
            break
        page += 1

    return jobs, {"list_item": raw_first, "detail_item": raw_first_detail}


def load_overrides() -> dict:
    path = os.path.join(os.path.dirname(__file__), "../../joblisting/location_overrides.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def main() -> None:
    tt_key    = os.environ.get("TEAMTAILOR_API_KEY", "").strip()
    hr_key    = os.environ.get("HOMERUN_API_KEY", "").strip()
    overrides = load_overrides()

    all_jobs: list[dict] = []
    errors: list[str] = []

    if tt_key:
        try:
            tt_jobs, _ = fetch_teamtailor(tt_key)
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
            hr_jobs, _ = fetch_homerun(hr_key, overrides)
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
