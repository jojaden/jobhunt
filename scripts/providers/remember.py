# -*- coding: utf-8 -*-
"""리멤버. 검색 API 가 목록과 본문을 함께 준다. 로그인·헤더 없이 일반 요청으로 받는다 (2026-10-15 실측).

목록: POST career-api.rememberapp.co.kr/job_postings/search {"search":{"keywords":[..]},"page":n,"per":30}
      → data[] (공고마다 주요업무·자격요건·우대사항·경력·근무지·마감), meta.total_pages. 정렬은 starts_at·id 내림차순.
마감: GET career-api.rememberapp.co.kr/job_postings/{id} → data.status (published / closed)·ends_at. 지워진 공고는 404.
헤드헌팅 공고는 실제 회사가 비공개라 회사 이름 앞에 "[헤드헌팅] " 을 붙여 다른 회사 공고와 중복으로 묶이지 않게 한다.
"""
import json
import re
from datetime import datetime
from typing import List, Optional

from jobkit import Job, ShapeError, get_json, http_get

API = "https://career-api.rememberapp.co.kr/job_postings"
WEB = "https://career.rememberapp.co.kr/job/posting"


def _text(p: dict) -> str:
    parts = [("주요업무", p.get("job_description")), ("자격요건", p.get("qualifications")),
             ("우대사항", p.get("preferred_qualifications")), ("소개", p.get("introduction"))]
    lo, hi = p.get("min_experience"), p.get("max_experience")
    if lo is not None:
        parts.append(("경력", f"{lo}년 이상" if hi is None else f"{lo}~{hi}년"))
    return "\n\n".join(f"## {k}\n{v.strip()}" for k, v in parts if v and v.strip())


def collect(cfg: dict) -> List[Job]:
    jobs, seen = [], set()
    for kw in cfg.get("keywords", ["백엔드"]):
        for page in range(1, cfg.get("max_pages", 10) + 1):
            q = {"search": {"keywords": [kw]}, "page": page, "per": 30}
            d = get_json(f"{API}/search", data=json.dumps(q, ensure_ascii=False).encode(), headers={"Content-Type": "application/json"})
            ps, meta = d.get("data"), d.get("meta")
            if not isinstance(ps, list) or not isinstance(meta, dict):
                raise ShapeError("리멤버 목록에 data·meta 없음")
            for p in ps:
                if p["id"] in seen:
                    continue
                seen.add(p["id"])
                org = p.get("organization") or {}
                company = ("[헤드헌팅] " if org.get("headhunter") else "") + (org.get("name") or "")
                loc = ", ".join(f"{a.get('address_level1') or ''} {a.get('address_level2') or ''}".strip() for a in p.get("addresses") or [])
                jobs.append(Job("remember", str(p["id"]), f"{WEB}/{p['id']}", company, p["title"], location=loc,
                                posted_at=(p.get("starts_at") or "")[:10], closes_at=(p.get("ends_at") or "")[:10] or "상시",
                                text=_text(p), extra=dict(career=(p.get("min_experience"), p.get("max_experience")))))
            if page >= (meta.get("total_pages") or 0):
                break
    return jobs


def detail(job: Job) -> str:
    return job.text


def handles(url: str) -> bool:
    return "career.rememberapp.co.kr/job/posting/" in url


def alive(url: str) -> Optional[bool]:
    m = re.search(r"/job/posting/(\d+)", url)
    if not m:
        return None
    status, body = http_get(f"{API}/{m.group(1)}")
    if status == 404:
        return False
    if status != 200:
        raise ShapeError(f"HTTP {status}: 리멤버 상세")
    d = json.loads(body).get("data")
    if not isinstance(d, dict):
        raise ShapeError("리멤버 상세에 data 없음")
    if d.get("status") == "closed":
        return False
    if d.get("status") != "published":
        return None
    ends = (d.get("ends_at") or "")[:19]
    return not ends or datetime.strptime(ends, "%Y-%m-%dT%H:%M:%S") > datetime.now()
