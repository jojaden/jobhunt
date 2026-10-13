# -*- coding: utf-8 -*-
"""LinkedIn 비로그인(guest) API (2026-09-29 실측).

목록 /jobs-guest/jobs/api/seeMoreJobPostings/search (HTML 카드 10개씩), 상세 /jobs-guest/jobs/api/jobPosting/{id}.
- 검색 결과의 전체 URL(슬러그 포함)을 그대로 쓴다. 숫자 ID로 jobs/view/{id} 를 다시 만들면 마감처럼 보인다 (2026-09-01).
- 한국어로 쓴 공고만 받는다(korean_only). 영어 전용 JD는 본문을 읽은 뒤 skipped_language 로 뺀다.
- 요청 간격 1.6초 이상. 429 가 나면 10초 쉬고 한 번 더, 그래도 429 면 그 키워드는 멈추고 받은 것까지만 쓴다
  (Partial 로 돌려줘 수집 보고에 "일부만"으로 남는다. 못 받은 공고는 기록되지 않아 다음 실행에 다시 받는다).
"""
import re
import time
import urllib.parse
from typing import List, Optional

from jobkit import Job, Partial, ShapeError, html_text, http_get

BASE = "https://www.linkedin.com/jobs-guest/jobs/api"
DELAY = 1.6
_CARD = re.compile(r'data-entity-urn="urn:li:jobPosting:(\d+)"(.*?)(?=data-entity-urn="urn:li:jobPosting:|\Z)', re.S)


def _pick(pat: str, s: str) -> str:
    m = re.search(pat, s, re.S)
    return html_text(m.group(1)).strip() if m else ""


def collect(cfg: dict) -> List[Job]:
    loc = urllib.parse.quote(cfg.get("location", "Seoul, South Korea"))
    period = int(cfg.get("period_days", 30)) * 86400
    jobs, seen, stopped = [], set(), []
    for kw in cfg.get("keywords", ["백엔드 개발자"]):
        for page in range(cfg.get("max_pages", 5)):
            url = (f"{BASE}/seeMoreJobPostings/search?keywords={urllib.parse.quote(kw)}&location={loc}"
                   f"&f_TPR=r{period}&start={page * 10}")
            status, body = http_get(url, accept="text/html", delay=DELAY)
            if status == 429:                       # 잠깐 쉬고 한 번만 다시
                time.sleep(10)
                status, body = http_get(url, accept="text/html", delay=DELAY)
            if status == 429:
                stopped.append(f"'{kw}' {page + 1}쪽부터")
                break
            if status != 200:
                raise ShapeError(f"LinkedIn 목록 HTTP {status}")
            cards = _CARD.findall(body)
            if not cards and page == 0 and "base-card" in body:
                raise ShapeError("LinkedIn 카드 형식이 바뀜")
            for jid, c in cards:
                if jid in seen:
                    continue
                seen.add(jid)
                href = re.search(r'class="base-card__full-link[^"]*"\s+href="([^"?]+)', c)
                jobs.append(Job("linkedin", jid, href.group(1) if href else f"https://www.linkedin.com/jobs/view/{jid}",
                                _pick(r'base-search-card__subtitle">.*?<a[^>]*>(.*?)</a>', c),
                                _pick(r'base-search-card__title">(.*?)</h3>', c),
                                location=_pick(r'job-search-card__location">(.*?)</span>', c),
                                posted_at=_pick(r'<time[^>]*datetime="([^"]+)"', c),
                                extra=dict(korean_only=cfg.get("korean_only", True))))
            if len(cards) < 10:
                break
    return Partial(jobs, "요청 제한(429)으로 못 받음: " + ", ".join(stopped)) if stopped else jobs


def _detail_html(jid: str):
    status, body = http_get(f"{BASE}/jobPosting/{jid}", accept="text/html", delay=DELAY)
    if status == 429:                               # 수집 직후엔 요청 제한이 잦다 — 쉬고 한 번만 다시
        time.sleep(10)
        status, body = http_get(f"{BASE}/jobPosting/{jid}", accept="text/html", delay=DELAY)
    return status, body


def _hangul_ratio(s: str) -> float:
    letters = re.findall(r"[A-Za-z가-힣]", s)
    return sum(1 for ch in letters if "가" <= ch <= "힣") / len(letters) if letters else 0.0


def detail(job: Job) -> str:
    status, body = _detail_html(job.id)
    if status != 200:
        raise ShapeError(f"LinkedIn 상세 HTTP {status}")
    text = html_text(_pick(r'show-more-less-html__markup[^"]*">(.*)</div>\s*<button', body) or
                     _pick(r'show-more-less-html__markup[^"]*">(.*?)</div>', body))
    crit = [html_text(x) for x in re.findall(r'description__job-criteria-text[^>]*>(.*?)</span>', body, re.S)]
    if crit:
        text += "\n\n## 조건 (LinkedIn)\n" + " · ".join(x for x in crit if x)
    if job.extra.get("korean_only") and _hangul_ratio(text) < 0.2:
        job.extra["skip"] = "skipped_language"      # 영어 전용 JD (사용자 조건: 한국어 공고만)
    return text


def handles(url: str) -> bool:
    return "linkedin.com/jobs/view/" in url


def alive(url: str) -> Optional[bool]:
    m = re.search(r"(\d{8,})(?:[/?]|$)", url)
    if not m:
        return None
    status, body = _detail_html(m.group(1))
    if status == 404:
        return False
    if status != 200:
        return None
    if re.search(r"No longer accepting applications|더 이상 지원을 받지 않", body):
        return False
    return "show-more-less-html__markup" in body
