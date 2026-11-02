# -*- coding: utf-8 -*-
"""원티드. 목록 chaos/navigation, 상세 v4/jobs/{id} (2026-09-29 실측).

목록은 한 쪽에 30개까지: limit 이 30 을 넘으면 오류 없이 빈 목록이 온다 (2026-11-02 실측).
"""
import re
from typing import List, Optional

from jobkit import Job, ShapeError, get_json

BASE = "https://www.wanted.co.kr"
PAGE = 30


def collect(cfg: dict) -> List[Job]:
    q = "&".join(f"job_ids={i}" for i in cfg.get("job_ids", [872, 674, 10110]))
    url = (f"{BASE}/api/chaos/navigation/v1/results?job_group_id={cfg.get('job_group_id', 518)}&{q}"
           f"&country=kr&job_sort=job.latest_order&years={cfg.get('years', -1)}&locations=all&limit={PAGE}&offset=0")
    jobs = []
    for _ in range(cfg.get("max_pages", 50)):
        d = get_json(url)
        if "data" not in d:
            raise ShapeError("원티드 목록에 data 없음")
        for it in d["data"]:
            a = it.get("address") or {}
            jobs.append(Job("wanted", str(it["id"]), f"{BASE}/wd/{it['id']}", it["company"]["name"], it["position"],
                            location=" ".join(x for x in (a.get("location"), a.get("district")) if x),
                            extra=dict(career=(it.get("annual_from"), it.get("annual_to")))))
        nxt = (d.get("links") or {}).get("next")
        if not nxt:
            break
        url = BASE + nxt
    return jobs


def _job(id_: str) -> dict:
    d = get_json(f"{BASE}/api/v4/jobs/{id_}")
    if "job" not in d:
        raise ShapeError("원티드 상세에 job 없음")
    return d["job"]


def detail(job: Job) -> str:
    j = _job(job.id)
    det = j.get("detail") or {}
    job.closes_at = j.get("due_time") or "상시"
    parts = [("주요업무", det.get("main_tasks")), ("자격요건", det.get("requirements")),
             ("우대사항", det.get("preferred_points")), ("소개", det.get("intro"))]
    if j.get("annual_from") is not None:
        parts.append(("경력", f"{j.get('annual_from')}~{j.get('annual_to')}년"))
    full = (j.get("address") or {}).get("full_location")
    if full:
        job.location = full
    return "\n\n".join(f"## {k}\n{v}" for k, v in parts if v)


def handles(url: str) -> bool:
    return "wanted.co.kr/wd/" in url


def alive(url: str) -> Optional[bool]:
    m = re.search(r"/wd/(\d+)", url)
    return None if not m else _job(m.group(1)).get("status") == "active"
