# -*- coding: utf-8 -*-
"""사람인 검색 페이지(HTML) → 공고 본문 (2026-10-06 실측).

목록: /zf_user/search/recruit?searchword={키워드}&recruitPageCount=100&exp_cd=2&sort=reg_dt 의 div.item_recruit
      (exp_cd=2 경력, 최신순 100건). 근무지·경력은 job_condition 의 첫째·둘째 span.
본문: /zf_user/jobs/relay/view-detail?rec_idx={id}&rec_seq=0 (relay/view 는 본문이 iframe 이라 비어 있다).
마감: /zf_user/jobs/view?rec_idx={id} 의 "접수기간 및 방법"·지원 버튼 (2026-10-13 실측). relay/view 는 이 부분을 스크립트로 채워 비어 있다.
"""
import re
from datetime import date
from typing import List, Optional
from urllib.parse import quote

from jobkit import Job, ShapeError, html_text, http_get

SEARCH = "https://www.saramin.co.kr/zf_user/search/recruit?searchword={}&recruitPageCount=100&exp_cd=2&sort=reg_dt"
VIEW = "https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx={}"
DETAIL = "https://www.saramin.co.kr/zf_user/jobs/relay/view-detail?rec_idx={}&rec_seq=0"
STATUS = "https://www.saramin.co.kr/zf_user/jobs/view?rec_idx={}"


def _txt(s: str) -> str:
    return re.sub(r"\s+", " ", html_text(s)).strip()


def _years(career: str):
    """'경력 3~8년' → (3, 8), '경력 5년↑' → (5, None), 그 밖(경력무관 등)은 None."""
    m = re.search(r"(\d+)\s*~\s*(\d+)년", career)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"(\d+)년\s*↑", career)
    return (int(m.group(1)), None) if m else None


def _closes(s: str) -> str:
    """'~ 11/01(일)' → 'YYYY-11-01' (지난 달이면 내년), '상시채용'·'채용시' → '상시'."""
    m = re.search(r"(\d{1,2})/(\d{1,2})", s)
    if not m:
        return "상시" if re.search(r"상시|채용시", s) else ""
    today = date.today()
    mon, day = int(m.group(1)), int(m.group(2))
    return date(today.year + (mon < today.month), mon, day).isoformat()


def collect(cfg: dict) -> List[Job]:
    jobs = {}
    for kw in cfg.get("keywords") or []:
        status, body = http_get(SEARCH.format(quote(kw)), accept="text/html")
        if status != 200:
            raise ShapeError(f"사람인 검색 HTTP {status}: {kw}")
        blocks = re.split(r'<div class="item_recruit"', body)[1:]
        if not blocks and "item_recruit" not in body and "검색결과가 없습니다" not in body:
            raise ShapeError("사람인 검색 결과에 item_recruit 없음")
        for blk in blocks:
            rid = re.search(r'value="(\d+)"', blk)
            tit = re.search(r'class="job_tit".*?title="([^"]+)"', blk, re.S)
            corp = re.search(r'class="corp_name".*?<a[^>]*>(.*?)</a>', blk, re.S)
            if not (rid and tit and corp):
                continue
            cond = re.search(r'class="job_condition">(.*?)</div>', blk, re.S)
            spans = [_txt(x) for x in re.findall(r"<span[^>]*>(.*?)</span>", cond.group(1), re.S)] if cond else []
            due = re.search(r'class="date">(.*?)</span>', blk, re.S)
            jobs[rid.group(1)] = Job("saramin", rid.group(1), VIEW.format(rid.group(1)), _txt(corp.group(1)), _txt(tit.group(1)),
                                     location=spans[0] if spans else "", closes_at=_closes(_txt(due.group(1))) if due else "",
                                     extra=dict(career=_years(spans[1]) if len(spans) > 1 else None))
    return list(jobs.values())


def detail(job: Job) -> str:
    status, body = http_get(DETAIL.format(job.id), accept="text/html")
    if status != 200:
        raise ShapeError(f"사람인 본문 HTTP {status}")
    return html_text(re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", "", body))


def handles(url: str) -> bool:
    return "www.saramin.co.kr/zf_user/jobs/" in url


def alive(url: str) -> Optional[bool]:
    """마감 표시(마감되었습니다 · 접수마감 버튼)면 False, 지원 버튼이면 True, 지워진 공고(404)는 False, 그 밖은 None."""
    m = re.search(r"rec_idx=(\d+)", url)
    if not m:
        return None
    status, body = http_get(STATUS.format(m.group(1)), accept="text/html")
    if status == 404:
        return False
    if status != 200:
        return None
    btn = re.search(r'<button\s+class="sri_btn_lg[^"]*"\s+title="([^"]*)"', body)
    if 'class="copy end">마감되었습니다' in body or (btn and btn.group(1) == "접수마감"):
        return False
    return True if btn else None
