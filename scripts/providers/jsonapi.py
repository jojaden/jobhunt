# -*- coding: utf-8 -*-
"""설정으로 움직이는 JSON 목록 수집기 (2026-10-08 실측).

채용 사이트가 브라우저에서 부르는 목록 API 를 탐색 때 한 번 찾아 sources.yaml 에 적어 두면, 매주 브라우저 없이 그대로 부른다.
회사 항목에 둘 중 하나를 적는다.

  ats: workday | recruiter | roundhr | workable | ashby | skcareers
      채용 시스템 이름. careers_url 에서 설정을 만든다 (아래 PRESETS, 주소 꼴은 references/sources.md).
  jsonapi:                                   그 밖의 자체 API
    list: <목록 주소>                         GET. 응답이 HTML 이면 그 안의 __NEXT_DATA__ JSON 을 쓴다
    post: {...} 또는 'a=1&b=2'                있으면 POST (dict → JSON, 문자열 → 폼)
    headers: {...}                           목록·상세 요청에 함께 붙일 헤더
    items: data.list                         공고 목록 위치. 점으로 잇고, '*' 는 목록의 각 항목으로 펼친다 (jobs.*.data)
    id: jobId / title: name                  항목 안의 점 경로
    url: 'https://…/jobs/{jobId}'            공고 주소 틀. {점 경로} 를 항목 값으로 채운다
    where: {status: OPEN}                    이 값과 같은 항목만 (선택)
    text: content                            항목 안의 본문 (선택)
    detail: 'https://…/api/jobs/{jobId}'     본문 주소 (선택). JSON 이면 긴 글 필드를 모두, HTML 이면 페이지 글.
                                             없으면 공고 주소를 다루는 다른 공급원(greetinghr 등)이나 공고 페이지 글
    detail_post: {jobNoticeId: '{jobNoticeId}'}   상세가 POST 일 때 (선택)
    closes / location: 항목 안의 점 경로 또는 '{…}' 틀 (선택)
    total: page.total                        전체 수 위치 (선택). 받은 수가 모자라면 post 의 offset 키를 늘려 이어 받고,
    offset: offset                           그래도 모자라면 ShapeError ("일부만 받음"을 조용히 넘기지 않는다)

마감: 지금 목록에 있으면 활성. 목록에 없을 때는 상세(또는 공고 주소)가 404·410 일 때만 마감, 나머지는 판정 불가(None).
"""
import json
import re
import sys
from functools import lru_cache
from typing import List, Optional
from urllib.parse import parse_qs, urlencode, urlparse

from jobkit import P, Job, ShapeError, html_text, http_get, http_post, load_yaml, norm_company

_ND = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
_FIELD = re.compile(r"\{([\w.]+)\}")


# ── 채용 시스템 프리셋: careers_url → 설정 ────────────────────────
def _workday(c):
    """https://{tenant}.wd{n}.myworkdayjobs.com/{ko-KR/}{site} — 목록은 한 번에 20건까지라 offset 으로 이어 받는다."""
    m = re.match(r"https://([\w-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([\w-]+)", c["careers_url"])
    if not m:
        raise ShapeError(f"Workday 주소 꼴이 아님: {c['careers_url']}")
    host, api = f"https://{m.group(1)}.{m.group(2)}.myworkdayjobs.com", f"/wday/cxs/{m.group(1)}/{m.group(3)}"
    return dict(list=f"{host}{api}/jobs", post={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""},
                items="jobPostings", id="bulletFields.0", title="title", url=f"{host}/{m.group(3)}{{externalPath}}",
                detail=f"{host}{api}{{externalPath}}", location="locationsText", total="total", offset="offset")


def _recruiter(c):
    """마이다스인 잡플렉스 (*.recruiter.co.kr). 새 형식(/career/…)은 공용 API 에 prefix 헤더, 이전 형식(/app…)은 사이트의 list.json.
    주소에 경로가 없으면 첫 화면에 /appsite/ 가 보이는지로 가린다."""
    u = urlparse(c["careers_url"])
    old = u.path.startswith("/app")
    if not old and not u.path.startswith("/career"):
        old = "/appsite/" in http_get(f"https://{u.netloc}/", accept="text/html")[1]
    if old:
        return dict(list=f"https://{u.netloc}/app/jobnotice/list.json", post="jobnoticeStateCode=10&pageSize=100&currentPage=1",
                    items="list", id="jobnoticeSn", title="jobnoticeName", where={"receiptState": "접수중"}, total="pageUtil.recordCount",
                    url=f"https://{u.netloc}/app/jobnotice/view?systemKindCode={{systemKindCode}}&jobnoticeSn={{jobnoticeSn}}")
    api = "https://api-recruiter.recruiter.co.kr/position"
    return dict(list=f"{api}/v1/jobflex", headers={"prefix": u.netloc},
                post={"pageableRq": {"page": 1, "size": 100, "sort": ["CREATED_DATE_TIME"]},
                      "filter": {"keyword": "", "tagSnList": [], "jobGroupSnList": [], "careerTypeList": [], "regionSnList": [],
                                 "submissionStatusList": ["IN_SUBMISSION"], "openStatusList": [], "resumeLanguageTypeList": []}},
                items="list", id="positionSn", title="title", url=f"https://{u.netloc}/career/jobs/{{positionSn}}",
                detail=f"{api}/v2/jobflex/{{positionSn}}", closes="endDateTime", total="pagination.totalCount")


def _roundhr(c):
    """라운드HR (*.recruit.roundhr.com 또는 회사 도메인). code 는 하위 도메인, 회사 도메인이면 sources.yaml code: (없으면 도메인 이름)."""
    u = urlparse(c["careers_url"])
    code = c.get("code") or (u.netloc.split(".")[0] if u.netloc.endswith(".recruit.roundhr.com") else u.netloc.split(".")[-2])
    return dict(list=f"https://api-prod.roundhr.com/api/site/jobs?code={code}&per=100&page=1", items="results", id="code", title="title",
                url=f"https://{u.netloc}/c/{{application_form.code}}", text="application_form.intro_content", total="page.total")


def _workable(c):
    """apply.workable.com/{account} — 공개 위젯 API 는 한 번에 전부 준다."""
    m = re.search(r"apply\.workable\.com/([\w-]+)", c["careers_url"])
    if not m:
        raise ShapeError(f"Workable 주소 꼴이 아님: {c['careers_url']}")
    return dict(list=f"https://apply.workable.com/api/v1/widget/accounts/{m.group(1)}", items="jobs", id="shortcode", title="title",
                url=f"https://apply.workable.com/{m.group(1)}/j/{{shortcode}}/", location="{city}, {country}",
                detail=f"https://apply.workable.com/api/v2/accounts/{m.group(1)}/jobs/{{shortcode}}")


def _ashby(c):
    """jobs.ashbyhq.com/{org} — 공식 공개 API, 목록에 본문이 있다."""
    m = re.search(r"jobs\.ashbyhq\.com/([\w.-]+)", c["careers_url"])
    if not m:
        raise ShapeError(f"Ashby 주소 꼴이 아님: {c['careers_url']}")
    return dict(list=f"https://api.ashbyhq.com/posting-api/job-board/{m.group(1)}", items="jobs", where={"isListed": True},
                id="id", title="title", url=f"https://jobs.ashbyhq.com/{m.group(1)}/{{id}}", text="descriptionPlain", location="location")


def _skcareers(c):
    """SK 그룹 채용 (skcareers.com/Recruit?corpCode=…  또는 ?searchText=…). 상세는 서버가 그린 페이지."""
    q = parse_qs(urlparse(c["careers_url"]).query)
    if not (q.get("corpCode") or q.get("searchText")):
        raise ShapeError(f"SK Careers 주소에 corpCode·searchText 가 없음 (그룹 전체가 됨): {c['careers_url']}")
    form = urlencode(dict(sort=2, searchText=q.get("searchText", [""])[0], corpCode=q.get("corpCode", [""])[0], jobRole=0,
                          recruitType="", workingType="", workingRegion=""))
    return dict(list="https://www.skcareers.com/Recruit/GetRecruitList", post=form, items="list", id="noticeID", title="title",
                url="https://www.skcareers.com/Recruit/Detail/{noticeID}", closes="end", location="workingArea", total="totalCount")


PRESETS = {"workday": _workday, "recruiter": _recruiter, "roundhr": _roundhr, "workable": _workable, "ashby": _ashby,
           "skcareers": _skcareers}


# ── 공통 ──────────────────────────────────────────────
def spec_of(c: dict) -> dict:
    return c.get("jsonapi") or PRESETS[c["ats"]](c)


def _get(o, path: Optional[str]):
    """점 경로 값. '*' 는 목록의 각 항목에 나머지 경로를 적용해 하나의 목록으로 편다."""
    keys = [k for k in (path or "").split(".") if k]
    for i, k in enumerate(keys):
        if k == "*":
            out = []
            for x in o if isinstance(o, list) else []:
                v = _get(x, ".".join(keys[i + 1:]))
                out += v if isinstance(v, list) else [v]
            return out
        if isinstance(o, list) and k.isdigit():
            o = o[int(k)] if int(k) < len(o) else None
        elif isinstance(o, dict):
            o = o.get(k)
        else:
            return None
    return o


def _fill(tpl, item):
    """'{a.b}' 틀을 항목 값으로 채운다. dict·list 틀은 안의 문자열마다."""
    if isinstance(tpl, dict):
        return {k: _fill(v, item) for k, v in tpl.items()}
    if isinstance(tpl, list):
        return [_fill(v, item) for v in tpl]
    if isinstance(tpl, str):
        return _FIELD.sub(lambda m: "" if _get(item, m.group(1)) is None else str(_get(item, m.group(1))), tpl)
    return tpl


def _val(item, spec: Optional[str]):
    if not spec:
        return None
    return _fill(spec, item) if "{" in spec else _get(item, spec)


def _request(url: str, post=None, headers=None):
    if post is not None:
        return http_post(url, post, accept="application/json", headers=headers)
    return http_get(url, accept="application/json, text/html", headers=headers)


def _fetch(url: str, post=None, headers=None):
    status, body = _request(url, post, headers)
    if status != 200:
        raise ShapeError(f"HTTP {status}: {url}")
    if body.lstrip().startswith(("{", "[")):
        return json.loads(body)
    m = _ND.search(body)
    if m:
        return json.loads(m.group(1))
    raise ShapeError(f"JSON 도 __NEXT_DATA__ 도 아님: {url}")


def _items(spec: dict) -> list:
    post, headers = spec.get("post"), spec.get("headers")
    data = _fetch(spec["list"], post, headers)
    items = _get(data, spec["items"])
    if not isinstance(items, list):
        raise ShapeError(f"목록 위치 {spec['items']} 에 목록이 없음: {spec['list']}")
    total = _get(data, spec["total"]) if spec.get("total") else None
    for _ in range(50):
        if not (isinstance(total, int) and len(items) < total and spec.get("offset") and isinstance(post, dict)):
            break
        post = dict(post, **{spec["offset"]: len(items)})
        more = _get(_fetch(spec["list"], post, headers), spec["items"]) or []
        if not more:
            break
        items += more
    if isinstance(total, int) and len(items) < total:
        raise ShapeError(f"전체 {total}건 중 {len(items)}건만 받음 (페이지 설정 확인): {spec['list']}")
    where = spec.get("where") or {}
    return [x for x in items if all(_get(x, k) == v for k, v in where.items())]


_MONTHS = "january february march april may june july august september october november december".split()


def _date(v) -> str:
    """'2026-10-11T23:59' · '20261011' · 'October 11, 2026(Sun)' → 2026-10-11. 2999년 이후는 상시."""
    s = str(v or "")
    m = re.search(r"(\d{4})[-.]?(\d{2})[-.]?(\d{2})", s)
    if m:
        return "상시" if m.group(1) >= "2999" else "-".join(m.groups())
    m = re.search(r"([A-Za-z]+) (\d{1,2}), (\d{4})", s)
    if m and m.group(1).lower() in _MONTHS:
        return f"{m.group(3)}-{_MONTHS.index(m.group(1).lower()) + 1:02d}-{int(m.group(2)):02d}"
    return s[:20]


def collect(cfg: dict) -> List[Job]:
    spec = spec_of(cfg)
    src = f"{cfg.get('ats') or 'api'}:{norm_company(cfg.get('name') or urlparse(cfg['careers_url']).netloc)}"
    jobs = []
    for x in _items(spec):
        jid, title = _val(x, spec["id"]), _val(x, spec["title"])
        if jid in (None, "") or not title:
            raise ShapeError(f"id·제목 필드 없음 ({spec['id']}, {spec['title']}): {spec['list']}")
        extra = {}
        if spec.get("detail"):
            extra["detail"] = (_fill(spec["detail"], x), _fill(spec.get("detail_post"), x), spec.get("headers"))
        jobs.append(Job(src, str(jid), _fill(spec["url"], x), cfg.get("name") or src, html_text(str(title)),
                        location=str(_val(x, spec.get("location")) or ""), closes_at=_date(_val(x, spec.get("closes"))),
                        text=html_text(str(_val(x, spec.get("text")) or "")), extra=extra))
    return jobs


def _strings(o, out):
    """JSON 안의 긴 글(주소 제외)을 나온 순서대로."""
    if isinstance(o, dict):
        for v in o.values():
            _strings(v, out)
    elif isinstance(o, list):
        for v in o:
            _strings(v, out)
    elif isinstance(o, str) and len(o) >= 40 and not o.startswith("http") and o not in out:
        out.append(o)
    return out


def _plain(html: str) -> str:
    return html_text(re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", "", html))


def _detail_text(url: str, post=None, headers=None) -> str:
    status, body = _request(url, post, headers)
    if status != 200:
        raise ShapeError(f"상세 HTTP {status}: {url}")
    if body.lstrip().startswith(("{", "[")):
        return "\n\n".join(_plain(s) for s in _strings(json.loads(body), []))
    return _plain(body)


def detail(job: Job) -> str:
    if job.text:
        return job.text
    if job.extra.get("detail"):
        return _detail_text(*job.extra["detail"])
    import providers
    other = providers.for_url(job.url)
    if other and other is not sys.modules[__name__]:
        return other.detail(job)
    return _detail_text(job.url)


# ── 마감 판정 ──────────────────────────────────────────
def _match(tpl: str, url: str) -> Optional[dict]:
    """공고 주소 틀에 url 이 맞으면 {점 경로: 값}. 주소 전체가 필드인 틀('{url}')은 판정하지 않는다."""
    parts = _FIELD.split(tpl)
    if not parts[0]:
        return None
    rx = "".join(re.escape(p) if i % 2 == 0 else f"(?P<f{i // 2}>.+?)" for i, p in enumerate(parts))
    m = re.fullmatch(rx, url)
    if not m:
        return None
    out: dict = {}
    for i, name in enumerate(parts[1::2]):
        node = out
        keys = name.split(".")
        for k in keys[:-1]:
            node = node.setdefault(k, {})
        node[keys[-1]] = m.group(f"f{i}")
    return out


@lru_cache(maxsize=1)
def _specs():
    """sources.yaml 의 jsonapi·프리셋 회사와 설정 (alive.py 가 공고마다 부르므로 한 번만 만든다)."""
    out = []
    for c in (load_yaml(P["sources"]) or {}).get("companies") or []:
        if c.get("jsonapi") or c.get("ats") in PRESETS:
            try:
                out.append((c, spec_of(c)))
            except ShapeError:
                continue
    return out


def _company(url: str):
    for c, spec in _specs():
        fields = _match(spec["url"], url)
        if fields is not None:
            return c, spec, fields
    return None, None, None


def handles(url: str) -> bool:
    return _company(url)[0] is not None


def alive(url: str) -> Optional[bool]:
    c, spec, fields = _company(url)
    if not c:
        return None
    try:
        if any(j.url == url for j in collect(c)):
            return True
    except ShapeError:
        return None
    probe = (url, None, None)
    if spec.get("detail") and set(_FIELD.findall(spec["detail"] + json.dumps(spec.get("detail_post") or ""))) <= set(_FIELD.findall(spec["url"])):
        probe = (_fill(spec["detail"], fields), _fill(spec.get("detail_post"), fields), spec.get("headers"))
    status, _ = _request(*probe)
    return False if status in (404, 410) else None
