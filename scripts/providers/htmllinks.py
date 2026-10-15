# -*- coding: utf-8 -*-
"""서버가 그린 HTML 에 공고 링크가 그대로 있는 채용 사이트 (두나무 등, 2026-10-06 실측).

sources.yaml 에 links: '<공고 주소 정규식>' 을 적는다 (careers_url 기준 상대 주소도 된다, 예: '/detail/\\d+').
목록이 스크립트로 그려지지만 사이트맵에 공고 주소가 있는 곳은 sitemap: '<사이트맵 주소>' 를 함께 적는다 (2026-10-08).
제목은 공고 페이지 <title> 에서 ' | 회사' 나 첫 화면 제목 끝의 사이트 이름(' - NBT')을 뗀 것, 본문은 <script>·<style> 을 뺀 페이지 글이다.
없는 공고에도 200 과 채용 첫 화면(두나무)이나 사이트 첫 화면 제목을 돌려주는 곳이 있어, 제목이 그 둘과 같으면 마감으로 본다.
"""
import re
from typing import List, Optional
from urllib.parse import urljoin, urlparse

from jobkit import P, Job, ShapeError, html_text, http_get, load_yaml, url_part


def _page(url: str):
    """(status, <title> 글, 본문 글)."""
    status, body = http_get(url, accept="text/html")
    m = re.search(r"<title[^>]*>(.*?)</title>", body or "", re.S)
    return status, html_text(m.group(1)) if m else "", html_text(re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", "", body or ""))


def _clean(title: str, site: str) -> str:
    """'DevOps Engineer | 두나무' → 'DevOps Engineer', 'Backend Engineer - NBT' (첫 화면 '영입 공고 - NBT') → 'Backend Engineer'."""
    title = title.split(" | ")[0].strip()
    return re.sub(rf"\s+[-–]\s+{re.escape(site)}$", "", title) if site else title


def _site(careers_title: str) -> str:
    m = re.search(r"\s[-–|]\s+([^-–|]+)$", careers_title)
    return m.group(1).strip() if m else ""


def _sitemap(url: str) -> List[str]:
    """사이트맵(또는 사이트맵 목록 한 단계)의 주소들."""
    status, body = http_get(url, accept="application/xml,text/xml")
    if status != 200:
        raise ShapeError(f"사이트맵 HTTP {status}: {url}")
    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", body)
    if "<sitemapindex" in body:
        return [u for sub in locs for u in _sitemap(sub)]
    return locs


def collect(cfg: dict) -> List[Job]:
    status, body = http_get(cfg["careers_url"], accept="text/html")
    if status != 200:
        raise ShapeError(f"채용 첫 화면 HTTP {status}: {cfg['careers_url']}")
    if cfg.get("sitemap"):
        urls = sorted({u for u in _sitemap(cfg["sitemap"]) if re.search(cfg["links"] + r"/?$", u)})
    else:
        urls = sorted({urljoin(cfg["careers_url"], u) for u in re.findall(rf'href="({cfg["links"]})"', body)})
    if not urls:
        raise ShapeError(f"공고 링크 없음 (links 정규식 또는 페이지 형식 확인): {cfg['careers_url']}")
    host = urlparse(cfg["careers_url"]).netloc.split(".")[-2]
    m = re.search(r"<title[^>]*>(.*?)</title>", body, re.S)
    site = _site(html_text(m.group(1)) if m else "")
    jobs = []
    for url in urls:
        status, title, text = _page(url)
        title = _clean(title, site)
        if status == 200 and title:
            jobs.append(Job(f"html:{host}", url.rstrip("/").rsplit("/", 1)[-1], url, cfg.get("name") or host, title, text=text))
    return jobs


def detail(job: Job) -> str:
    return job.text


def _company(url: str) -> Optional[dict]:
    for c in (load_yaml(P["sources"]) or {}).get("companies") or []:
        if c.get("links") and urlparse(c.get("careers_url") or "").netloc == urlparse(url).netloc \
                and re.search(c["links"] + r"/?$", url):
            return c
    return None


def handles(url: str) -> bool:
    return _company(url) is not None


def alive(url: str) -> Optional[bool]:
    c = _company(url)
    status, title, _ = _page(url)
    if status == 404:
        return False
    if status != 200 or not c:
        return None
    home = _page(c["careers_url"])[1]
    root = _page(url_part(r"^https?://[^/]+/", c["careers_url"]))[1]   # 사이트 첫 화면으로 돌려보내는 곳
    return bool(title) and _clean(title, _site(home)) not in {_clean(home, _site(home)), _clean(root, _site(home))}
