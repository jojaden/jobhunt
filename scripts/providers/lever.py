# -*- coding: utf-8 -*-
"""Lever 공개 API (채널코퍼레이션 등). api.lever.co/v0/postings/{회사}?mode=json (2026-10-06 실측).

목록에 본문(descriptionPlain · lists · additionalPlain)이 함께 온다. 마감은 /v0/postings/{회사}/{id} 가 404.
sources.yaml 에는 api: https://api.lever.co/v0/postings/{회사} 로 적는다 (jobs.lever.co/{회사} 의 {회사}와 같다).
"""
import json
import re
from typing import List, Optional

from jobkit import Job, ShapeError, html_text, http_get, url_part

API = "https://api.lever.co/v0/postings"


def site_of(url: str) -> str:
    return url_part(r"(?:api\.lever\.co/v0/postings|jobs\.lever\.co)/([^/?#]+)", url, 1)


def collect(cfg: dict) -> List[Job]:
    site = site_of(cfg["api"])
    status, body = http_get(f"{API}/{site}?mode=json")
    if status != 200:
        raise ShapeError(f"Lever HTTP {status}: {site}")
    d = json.loads(body)
    if not isinstance(d, list):
        raise ShapeError("Lever 응답이 목록이 아님")
    jobs = []
    for p in d:
        lists = "\n".join(f"## {l.get('text')}\n{html_text(l.get('content'))}" for l in p.get("lists") or [])
        jobs.append(Job(f"lever:{site}", p["id"], p["hostedUrl"], cfg.get("name") or site, p.get("text") or "",
                        location=(p.get("categories") or {}).get("location") or "", closes_at="상시",
                        text="\n\n".join(x for x in (p.get("descriptionPlain"), lists, p.get("additionalPlain")) if x)))
    return jobs


def detail(job: Job) -> str:
    return job.text


def handles(url: str) -> bool:
    return "jobs.lever.co/" in url


def alive(url: str) -> Optional[bool]:
    m = re.search(r"jobs\.lever\.co/([^/]+)/([0-9a-f-]{36})", url)
    if not m:
        return None
    status, _ = http_get(f"{API}/{m.group(1)}/{m.group(2)}")
    return status == 200 if status in (200, 404) else None
