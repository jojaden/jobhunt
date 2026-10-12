# -*- coding: utf-8 -*-
"""greetinghr (*.career.greetinghr.com). 목록은 /ko/home 의 __NEXT_DATA__ ["openings"], 본문은 /ko/o/{id} 의
getOpeningById.data.openingsInfo (2026-09-29 실측).
/ko/home 이 없고 회사 홈페이지에 공고 링크(…/ko/o/{id})만 걸어 둔 곳(오늘의집·쏘카)은 careers_url 에 그 홈페이지를 두고
ats: greetinghr 로 적으면 링크를 모아 공고마다 상세에서 제목·마감을 읽는다 (2026-10-06). cfg 의 seen_urls(scan.py 가 넘기는
이미 본 주소)에 있는 공고는 어차피 중복으로 빠지므로 상세를 받지 않고 건너뛴다."""
import json
import re
from typing import List, Optional

from jobkit import Job, ShapeError, html_text, http_get

_ND = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)


def _next_data(url: str) -> dict:
    status, body = http_get(url, accept="text/html")
    if status == 404:
        return {}
    m = _ND.search(body)
    if status != 200 or not m:
        raise ShapeError(f"__NEXT_DATA__ 없음 (브라우저로 읽어야 함): {url}")
    return json.loads(m.group(1))


def _query(nd: dict, first_key: str):
    for q in ((nd.get("props") or {}).get("pageProps") or {}).get("dehydratedState", {}).get("queries", []):
        if q.get("queryKey") and first_key in json.dumps(q["queryKey"]):
            return (q.get("state") or {}).get("data")
    return None


def base_of(url: str) -> str:
    return re.match(r"https?://[^/]+", url).group(0)


def collect(cfg: dict) -> List[Job]:
    base = base_of(cfg["careers_url"])
    ops = None
    # 회사 도메인에 붙인 greetinghr 는 첫 화면에 openings 가 있기도 하다. careers_url 이 /ko/home 이나 첫 화면이면 두 번 받지 않는다
    for url in dict.fromkeys((f"{base}/ko/home", cfg["careers_url"], base)):
        try:
            ops = _query(_next_data(url), '"openings"')
        except ShapeError:
            continue
        if isinstance(ops, list):
            break
    if not isinstance(ops, list):
        jobs = _from_links(cfg)
        if jobs is None:
            raise ShapeError(f"greetinghr openings 없음: {base}")
        return jobs
    jobs = []
    for o in ops:
        pos = (o.get("openingJobPosition") or {}).get("openingJobPositions") or [{}]
        place = pos[0].get("workspacePlace") or {}
        occ = (pos[0].get("workspaceOccupation") or {}).get("occupation", "")
        jobs.append(Job(f"greetinghr:{base.split('//')[1].split('.')[0]}", str(o["openingId"]), f"{base}/ko/o/{o['openingId']}",
                        cfg.get("name") or base, o["title"], location=" ".join(x for x in (place.get("place"), place.get("location")) if x),
                        closes_at=(o.get("dueDate") or "")[:10] or "상시", extra=dict(occupation=occ)))
    return jobs


def _from_links(cfg: dict) -> Optional[List[Job]]:
    """회사 홈페이지에 걸린 greetinghr 공고 링크 → 공고별 상세. 링크가 하나도 없으면 None (형식 변경으로 보고)."""
    status, body = http_get(cfg["careers_url"], accept="text/html")
    urls = sorted(set(re.findall(r"https://[\w.-]+\.career\.greetinghr\.com/ko/o/\d+", body))) if status == 200 else []
    if not urls:
        return None
    seen = cfg.get("seen_urls") or ()
    jobs = []
    for url in urls:
        if url in seen:
            continue
        oi = ((_query(_next_data(url), "getOpeningById") or {}).get("data") or {}).get("openingsInfo") or {}
        if oi.get("status") != "OPEN":
            continue
        oid = url.rsplit("/", 1)[1]
        jobs.append(Job(f"greetinghr:{url.split('//')[1].split('.')[0]}", oid, url, cfg.get("name") or base_of(url), oi.get("title") or "",
                        closes_at=(oi.get("dueDate") or "")[:10] or "상시"))
    return jobs


def _longest(o, best=""):
    if isinstance(o, str):
        return o if len(o) > len(best) else best
    for v in (o.values() if isinstance(o, dict) else o if isinstance(o, list) else []):
        best = _longest(v, best)
    return best


def detail(job: Job) -> str:
    d = _query(_next_data(job.url), "getOpeningById") or {}
    return html_text(_longest(((d.get("data") or {}).get("openingsInfo")) or {}))


def handles(url: str) -> bool:
    # 회사 도메인에 붙인 그리팅(career.bithumbcorp.com 등)도 공고 주소가 /ko/o/{번호} 꼴이다
    return ".career.greetinghr.com/ko/o/" in url or bool(re.search(r"^https?://[^/]+/(?:ko|en)/o/\d+/?$", url))


def alive(url: str) -> Optional[bool]:
    try:
        d = _query(_next_data(url), "getOpeningById")
    except ShapeError:
        return None
    return bool(d and d.get("success") and (d.get("data") or {}).get("openingsInfo"))
