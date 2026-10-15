# -*- coding: utf-8 -*-
"""공고 공급원. 모듈마다 같은 네 함수를 둔다 (Provider).

  collect(cfg) -> List[Job]   목록 (가능하면 본문까지)
  detail(job)  -> str         본문(자격요건·우대·주요업무). 목록에 본문이 있으면 job.text 를 그대로
  alive(url)   -> Optional[bool]   True 활성 / False 마감 / None 판정 불가
  handles(url) -> bool        alive 가 이 URL 을 판정할 수 있는지

방법과 실측 날짜는 references/sources.md. 형식이 바뀌면 ShapeError 를 올려 "응답 형식 변경"으로 보고한다.
"""
from typing import Dict, List, Optional, Protocol

from jobkit import Job

from . import greenhouse, greetinghr, hiworks, htmllinks, jsonapi, jumpit, kakao, lever, line, linkedin, naver, nhn, ninehire, remember, saramin, toss, wanted, woowa



class Collector(Protocol):
    """scan.py 가 쓰는 쪽: 목록과 본문 (scan --add 의 손으로 찾은 공고도 이 모양)."""
    __name__: str

    def collect(self, cfg: dict) -> List[Job]: ...

    def detail(self, job: Job) -> str: ...


class Provider(Collector, Protocol):
    """공급원 모듈의 계약 전체. alive.py 는 for_url 로 고른 모듈에 마감을 묻는다."""
    def alive(self, url: str) -> Optional[bool]: ...

    def handles(self, url: str) -> bool: ...


BOARDS: Dict[str, Provider] = {"wanted": wanted, "jumpit": jumpit, "linkedin": linkedin, "saramin": saramin, "remember": remember}
ALL: List[Provider] = [wanted, jumpit, linkedin, saramin, remember, greenhouse, lever, toss, nhn, kakao, greetinghr, ninehire, naver, woowa, line, hiworks, htmllinks, jsonapi]
BY_ATS: Dict[str, Provider] = {"greetinghr": greetinghr, "ninehire": ninehire, "greenhouse": greenhouse, "hiworks": hiworks,   # sources.yaml 의 ats: (discover.py 가 적음)
          **{name: jsonapi for name in jsonapi.PRESETS}}                                               # workday·recruiter·roundhr·workable·ashby·skcareers


def for_company(c: dict) -> Optional[Provider]:
    """sources.yaml companies 항목 → 공급원 모듈 (없으면 None: 브라우저·수동 대상)."""
    api, url = c.get("api") or "", c.get("careers_url") or ""
    if c.get("method") == "browser":
        return None
    if c.get("ats") in BY_ATS and (c["ats"] != "greenhouse" or "greenhouse.io" in api):
        return BY_ATS[c["ats"]]                      # 회사 도메인에 붙인 채용 시스템 (예: careers.회사.com 이 greetinghr)
    if "greenhouse.io" in api:
        return greenhouse
    if "lever.co" in api:
        return lever
    if c.get("jsonapi"):
        return jsonapi                               # 탐색 때 찾아 둔 목록 API (예: 채용 사이트의 /api/…/announces)
    if c.get("links"):
        return htmllinks                             # 첫 화면 HTML 에 공고 링크가 있는 곳 (예: 두나무 /detail/{번호})
    if "toss.im" in url:
        return toss
    if "careers.nhn.com" in url:
        return nhn
    if "careers.kakao.com" in url:
        return kakao
    if any(h in url for h in naver.HOSTS) or "career.navercloudcorp.com" in url:
        return naver
    if "career.woowahan.com" in url:
        return woowa
    if "careers.linecorp.com" in url:
        return line
    if ".career.greetinghr.com" in url:
        return greetinghr
    return None


def for_url(url: str) -> Optional[Provider]:
    for m in ALL:
        if m.handles(url):
            return m
    return None
