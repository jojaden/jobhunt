# -*- coding: utf-8 -*-
"""나인하이어 (*.ninehire.site 또는 회사 도메인에 붙인 나인하이어 채용 사이트, 2026-09-30 실측).

목록: sources.yaml 의 company_id, 없으면 채용 사이트 첫 화면 __NEXT_DATA__ 의 homepageProps.homepage.companyId →
      https://api.ninehire.com/identity-access/homepage/recruitments?companyId=…
      (company_id 는 첫 화면 og:image·favicon 주소 image.ninehire.com/{brand|homepage}/{companyId}/… 에서 읽는다)
본문: {채용 사이트}/job_posting/{addressKey} 의 __NEXT_DATA__ pageProps.jobPosting.content (HTML)
"""
import json
import re
from typing import List, Optional

from jobkit import P, Job, ShapeError, html_text, http_get, load_yaml, url_part

API = "https://api.ninehire.com/identity-access/homepage/recruitments"
_ND = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)


def _next_data(url: str) -> dict:
    status, body = http_get(url, accept="text/html")
    if status == 404:
        return {}
    m = _ND.search(body)
    if status != 200 or not m:
        raise ShapeError(f"나인하이어 __NEXT_DATA__ 없음: {url}")
    return json.loads(m.group(1))


def _base(url: str) -> str:
    return url_part(r"^https?://[^/]+", url)


def _company_from_posting(careers_url: str):
    """첫 화면이 없는 나인하이어(자체 소개 페이지가 공고 링크만 거는 경우): 공고 하나에서 companyId 를 읽는다."""
    status, body = http_get(careers_url, accept="text/html")
    m = re.search(r"https://([a-z0-9-]+\.ninehire\.site)/job_posting/([A-Za-z0-9]{4,})", body) if status == 200 else None
    if not m:
        return None, None
    status, page = http_get(m.group(0), accept="text/html")
    cid = re.search(r'"companyId":"([^"]+)"', page) if status == 200 else None
    return (cid.group(1) if cid else None), f"https://{m.group(1)}"


def collect(cfg: dict) -> List[Job]:
    base = _base(cfg["careers_url"])
    cid = cfg.get("company_id")   # 채용 사이트 첫 화면이 봇 차단(HTTP 429)일 때도 목록 API 는 열려 있다 (2026-10-06)
    if not cid:
        try:
            hp = (((_next_data(base).get("props") or {}).get("pageProps") or {}).get("homepageProps") or {}).get("homepage") or {}
        except ShapeError:
            hp = {}
        cid = hp.get("companyId")
    if not cid:
        cid, site = _company_from_posting(cfg["careers_url"])
        base = site or base
    if not cid:
        raise ShapeError(f"나인하이어 companyId 없음 (첫 화면 차단이면 sources.yaml 에 company_id 지정): {base}")
    jobs, page = [], 1
    while True:
        status, body = http_get(f"{API}?companyId={cid}&page={page}&countPerPage=50&order=created_at_desc")
        if status != 200:
            raise ShapeError(f"나인하이어 목록 HTTP {status}")
        d = json.loads(body)
        if not isinstance(d.get("results"), list):
            raise ShapeError("나인하이어 목록에 results 없음")
        for r in d["results"]:
            if r.get("status") != "in_progress" or r.get("isPrivate"):
                continue
            loc = " ".join(x.get("addressName") or "" for x in r.get("jobLocations") or [])
            car = (r.get("career") or {}).get("range") or {}
            jobs.append(Job(f"ninehire:{base.split('//')[1].split('.')[0]}", r["recruitmentId"], f"{base}/job_posting/{r['addressKey']}",
                            cfg.get("name") or base, r.get("externalTitle") or r["title"], location=loc,
                            closes_at=(r.get("deadlineValue") or "")[:10] or "상시",
                            extra=dict(career=(car.get("over"), car.get("below")), group=(r.get("jobGroup") or {}).get("title"))))
        if page * 50 >= (d.get("count") or 0):
            break
        page += 1
    return jobs


def detail(job: Job) -> str:
    jp = ((_next_data(job.url).get("props") or {}).get("pageProps") or {}).get("jobPosting") or {}
    return html_text(jp.get("content") or "")


def handles(url: str) -> bool:
    return "/job_posting/" in url and ("ninehire" in url or url.count("/") == 4)


def _open_keys(cid: str) -> set:
    """목록 API 에서 진행 중·공개 공고의 addressKey 모음."""
    keys, page = set(), 1
    while True:
        status, body = http_get(f"{API}?companyId={cid}&page={page}&countPerPage=50&order=created_at_desc")
        if status != 200:
            raise ShapeError(f"나인하이어 목록 HTTP {status}")
        d = json.loads(body)
        if not isinstance(d.get("results"), list):         # 형식이 바뀐 것을 '모두 마감'으로 읽지 않게
            raise ShapeError("나인하이어 목록에 results 없음")
        keys |= {r["addressKey"] for r in d["results"] if r.get("status") == "in_progress" and not r.get("isPrivate")}
        if page * 50 >= (d.get("count") or 0):
            return keys
        page += 1


def _company_id_for(url: str) -> Optional[str]:
    """공고 주소의 호스트와 같은 채용 사이트를 sources.yaml 에서 찾아 company_id 를 돌려준다."""
    host = _base(url)
    for c in (load_yaml(P["sources"]) or {}).get("companies") or []:
        if c.get("company_id") and _base(c.get("careers_url") or "x://") == host:
            return c["company_id"]
    return None


def alive(url: str) -> Optional[bool]:
    try:
        pp = (_next_data(url).get("props") or {}).get("pageProps") or {}
    except ShapeError:   # 공고 페이지가 봇 차단이면 목록 API 로 판정 (2026-10-06)
        cid = _company_id_for(url)
        try:
            return url.rstrip("/").rsplit("/", 1)[-1] in _open_keys(cid) if cid else None
        except ShapeError:
            return None
    if not pp:
        return False
    return (pp.get("recruitment") or {}).get("status", "in_progress") == "in_progress" and bool(pp.get("jobPosting"))
