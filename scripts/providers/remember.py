# -*- coding: utf-8 -*-
"""리멤버. 검색 API 가 목록과 본문을 함께 준다. 로그인·헤더 없이 일반 요청으로 받는다 (2026-10-15 실측).

목록: POST career-api.rememberapp.co.kr/job_postings/search {"search":{"job_category_ids":[..],"keywords":[..]},"page":n,"per":50}
      → data[] (공고마다 주요업무·자격요건·우대사항·경력·근무지·마감), meta.total_pages. 정렬은 starts_at·id 내림차순.
      per 는 50 까지 (100 은 400). 직군 번호 여럿은 합집합, 키워드와 함께 주면 둘 다 맞는 공고.
      모르는 직군 번호는 조용히 무시되고, 모두 모르는 번호면 전체 공고(약 1만 4천 건)가 나온다.
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


def _searches(cfg: dict) -> List[dict]:
    """검색 조건들. 직군(job_category_ids)으로 찾고, 키워드가 있으면 키워드마다 직군과 함께. 둘 다 없으면 키워드 '백엔드'."""
    cats = cfg.get("job_category_ids") or []
    base = {"job_category_ids": cats} if cats else {}
    kws = cfg.get("keywords") or ([] if cats else ["백엔드"])
    return [dict(base, keywords=[kw]) for kw in kws] or [base]


def collect(cfg: dict) -> List[Job]:
    jobs, seen = [], set()
    cats = set(cfg.get("job_category_ids") or [])
    for search in _searches(cfg):
        for page in range(1, cfg.get("max_pages", 20) + 1):
            q = {"search": search, "page": page, "per": 50}
            d = get_json(f"{API}/search", data=json.dumps(q, ensure_ascii=False).encode(), headers={"Content-Type": "application/json"})
            ps, meta = d.get("data"), d.get("meta")
            if not isinstance(ps, list) or not isinstance(meta, dict):
                raise ShapeError("리멤버 목록에 data·meta 없음")
            if cats and ps and not cats & set(ps[0].get("job_category_ids") or []):
                raise ValueError(f"리멤버 직군 번호가 맞지 않음 (모르는 번호면 전체 공고가 나옴): {sorted(cats)}")
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
