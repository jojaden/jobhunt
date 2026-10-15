# -*- coding: utf-8 -*-
"""Greenhouse 공개 API (당근, 쿠팡, 크래프톤 등). boards-api.greenhouse.io/v1/boards/{보드}/jobs."""
import re
from typing import List, Optional
from urllib.parse import urlparse

from jobkit import P, Job, ShapeError, get_json, http_get, html_text, load_yaml, url_part

API = "https://boards-api.greenhouse.io/v1/boards"


def board_of(api_url: str) -> str:
    return url_part(r"/boards/([^/]+)", api_url, 1)


def collect(cfg: dict) -> List[Job]:
    board = board_of(cfg["api"])
    d = get_json(f"{API}/{board}/jobs?content=true")
    if "jobs" not in d:
        raise ShapeError("Greenhouse 응답에 jobs 없음")
    return [Job(f"greenhouse:{board}", str(j["id"]), j["absolute_url"], cfg.get("name") or j.get("company_name") or board,
                j["title"], location=(j.get("location") or {}).get("name", ""),
                posted_at=(j.get("first_published") or "")[:10], closes_at=(j.get("application_deadline") or "")[:10],
                text=html_text(j.get("content")), extra=dict(board=board))
            for j in d["jobs"]]


def detail(job: Job) -> str:
    return job.text


def handles(url: str) -> bool:
    return "gh_jid=" in url or "greenhouse.io" in url


def alive(url: str) -> Optional[bool]:
    m = re.search(r"greenhouse\.io/([^/]+)/jobs/(\d+)", url)
    if m:
        board, jid = m.group(1), m.group(2)
    else:    # 회사 도메인 + gh_jid: sources.yaml 에서 같은 도메인의 보드를 찾는다
        jid = re.search(r"gh_jid=(\d+)", url)
        host = urlparse(url).netloc
        board = next((board_of(c["api"]) for c in load_yaml(P["sources"]).get("companies") or []
                      if "greenhouse.io" in (c.get("api") or "") and urlparse(c.get("careers_url") or "").netloc == host), None)
        if not (jid and board):
            return None
        jid = jid.group(1)
    status, _ = http_get(f"{API}/{board}/jobs/{jid}")
    return status == 200 if status in (200, 404) else None
