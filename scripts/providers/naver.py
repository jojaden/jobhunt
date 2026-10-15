# -*- coding: utf-8 -*-
"""네이버 계열 채용 사이트 (recruit.navercorp.com · recruit.navercloudcorp.com · recruit.naverfincorp.com ·
recruit.webtoonscorp.com, 2026-09-30 실측). 모두 같은 /rcrt/ 시스템.

목록: {host}/rcrt/loadJobList.do?…&firstIndex=N (JSON, 10건씩, totalSize)
본문: {host}/rcrt/view.do?annoId={id} HTML 의 detail_wrap. 한 공고에 여러 직무가 섹션으로 들어 있을 수 있다.
"""
import json
import re
from typing import List, Optional

from jobkit import Job, ShapeError, html_text, http_get, url_part

Q = "rcrt/loadJobList.do?annoId=&sw=&subJobCdArr=&sysCompanyCdArr=&empTypeCdArr=&entTypeCdArr=&workAreaCdArr=&firstIndex={}"
HOSTS = ("recruit.navercorp.com", "recruit.navercloudcorp.com", "recruit.naverfincorp.com", "recruit.webtoonscorp.com")


def _host(url: str) -> str:
    h = url_part(r"^https?://([^/]+)", url, 1)
    return "recruit.navercloudcorp.com" if h == "career.navercloudcorp.com" else h   # 소개 사이트 → 채용 시스템


def collect(cfg: dict) -> List[Job]:
    host, jobs, first = _host(cfg["careers_url"]), [], 0
    while True:
        status, body = http_get(f"https://{host}/" + Q.format(first))
        if status != 200:
            raise ShapeError(f"네이버 채용 목록 HTTP {status}: {host}")
        try:
            d = json.loads(body)
        except ValueError:
            raise ShapeError(f"네이버 채용 목록 JSON 아님: {host}")
        if not isinstance(d.get("list"), list):          # 공고가 없어도 "list": [] 가 온다 (2026-10-08 실측)
            raise ShapeError(f"네이버 채용 목록에 list 없음: {host}")
        for x in d["list"]:
            end = x.get("endYmd") or ""
            jobs.append(Job(f"naver:{host.split('.')[1]}", str(x["annoId"]), f"https://{host}/rcrt/view.do?annoId={x['annoId']}",
                            x.get("sysCompanyCdNm") or cfg.get("name") or host, re.sub(r"^\[[^\]]+\]\s*", "", x["annoSubject"]),
                            location="판교" if x.get("workAreaCd") == "0010" else "",
                            closes_at=f"{end[:4]}-{end[4:6]}-{end[6:8]}" if len(end) == 8 else "상시",
                            extra=dict(entry=x.get("entTypeCdNm"), job=x.get("subJobCdNm"))))
        first += 10
        if first >= int(d.get("totalSize") or 0) or not d.get("list"):
            break
    return jobs


def _view(url: str) -> str:
    status, html = http_get(url, accept="text/html")
    if status == 404:
        return ""
    if status != 200:
        raise ShapeError(f"네이버 채용 상세 HTTP {status}")
    return html


def detail(job: Job) -> str:
    html = _view(job.url)
    i = html.find('class="detail_wrap')
    if i < 0:
        raise ShapeError("네이버 채용 상세에 detail_wrap 없음")
    html = re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>", " ", html[html.rfind("<", 0, i):])
    text = re.sub(r"\n\s*\n+", "\n", html_text(html))
    text = text.split("입사지원은 PC를 이용해주세요.")[-1]          # 공유·지원 버튼 문구를 뺀다
    return text.split("Footer")[0].strip()


def handles(url: str) -> bool:
    return any(h in url for h in HOSTS) and "view.do?annoId=" in url


def alive(url: str) -> Optional[bool]:
    try:
        html = _view(url)
    except ShapeError:
        return None
    if not html:
        return False
    if re.search(r"마감된 공고|존재하지 않는 공고|채용이 마감", html):
        return False
    return 'class="detail_wrap' in html
