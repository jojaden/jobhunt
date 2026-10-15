# -*- coding: utf-8 -*-
"""하이웍스 채용 (가비아 그룹웨어의 채용 사이트 기능, recruit.gabia.com 등, 2026-09-30 실측).

회사 번호: GET {API}/v1/career-site/tokens/site-information  (헤더 x-career-site-domain: 회사 도메인) → data.office_no
목록: GET {API}/v1/career-site/offices/{office_no}/announces → data[] (announce_id, announce_name, announce_type, apply_finish_date)
본문: GET {API}/v1/career-site/offices/{office_no}/announces/{announce_id} → data.description (HTML, 이미지뿐인 공고도 있음)
공고 주소: {채용 사이트}/recruit/view/{announce_id}. 없는 공고는 404.
"""
import json
import re
from typing import List, Optional

from jobkit import Job, ShapeError, html_text, http_get, url_part

API = "https://recruit-api.gabiaoffice.hiworks.com/v1/career-site"
_VIEW = re.compile(r"^(https?://[^/]+)/recruit/view/([a-z0-9]{6})/?$")


def _domain(url: str) -> str:
    host = url_part(r"^https?://([^/]+)", url, 1)
    return host.split(".", 1)[1] if host.count(".") > 1 else host       # recruit.gabia.com → gabia.com


def _get(path: str, domain: str):
    status, body = http_get(API + path, accept="application/json", headers={"x-career-site-domain": domain})
    if status == 404:
        return None
    if status != 200:
        raise ShapeError(f"하이웍스 채용 HTTP {status}: {path}")
    try:
        return json.loads(body).get("data")
    except ValueError:
        raise ShapeError(f"하이웍스 채용 JSON 아님: {path}")


def _office(domain: str) -> str:
    d = _get("/tokens/site-information", domain) or {}
    if not d.get("office_no"):
        raise ShapeError(f"하이웍스 채용 office_no 없음: {domain}")
    return str(d["office_no"])


def collect(cfg: dict) -> List[Job]:
    base = url_part(r"^https?://[^/]+", cfg["careers_url"])
    domain = cfg.get("hiworks_domain") or _domain(cfg["careers_url"])
    office = _office(domain)
    jobs = []
    for a in _get(f"/offices/{office}/announces", domain) or []:
        end = (a.get("apply_finish_date") or "")[:10]
        jobs.append(Job(f"hiworks:{domain.split('.')[0]}", a["announce_id"], f"{base}/recruit/view/{a['announce_id']}",
                        cfg.get("name") or domain, a["announce_name"], closes_at=end or "상시",
                        extra=dict(domain=domain, office=office, experience=a.get("experience"))))
    return jobs


def _detail(url: str):
    domain = _domain(url)
    return _get(f"/offices/{_office(domain)}/announces/{url_part(_VIEW.pattern, url, 2)}", domain)


def detail(job: Job) -> str:
    d = _detail(job.url) or {}
    locs = re.findall(r"'address': '([^']+)'", str(d.get("category_location") or ""))
    text = html_text(d.get("description") or "")
    if len(text) < 50 and "<img" in (d.get("description") or ""):
        text += "\n[본문이 이미지 — 이미지 주소: " + ", ".join(re.findall(r'<img[^>]+src="([^"]+)"', d["description"])[:3]) + "]"
    return (f"근무지: {', '.join(locs)}\n\n" if locs else "") + text


def handles(url: str) -> bool:
    return bool(_VIEW.match(url)) and url.startswith("https://recruit.")


def alive(url: str) -> Optional[bool]:
    try:
        return _detail(url) is not None
    except ShapeError:
        return None
