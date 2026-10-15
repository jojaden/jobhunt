# -*- coding: utf-8 -*-
"""회사 찾기 (LLM 호출 없음). 자체 채용 사이트에만 공고를 올리는 회사까지 수집 범위를 넓힌다.

  python3 scripts/discover.py collect          정보원에서 회사 후보를 모으고 인지도·규모 점수를 매긴다
  python3 scripts/discover.py probe [--top N] [--no-browser]
                                               점수 높은 후보의 채용 사이트와 채용 시스템(ATS)을 찾는다 (못 찾으면 흔한 채용 주소 →
                                               헤드리스 브라우저로 목록 API 를 본다. 순서: references/sources.md "회사 찾기")
  python3 scripts/discover.py report           후보 표 (점수·채용 사이트·ATS·수집 가능 여부)
  python3 scripts/discover.py missing          채용 사이트를 못 찾은 후보 (Firecrawl·검색으로 채울 목록)
  python3 scripts/discover.py set <파일.tsv>   밖에서 찾은 채용 사이트(회사<TAB>URL<TAB>출처)를 넣고 채용 시스템을 판별·검증
  python3 scripts/discover.py promote [--min S] [--dry-run]
                                               점수 S 이상이고 채용 사이트를 찾은 회사를 sources.yaml companies 에 넣는다

결과: data/search/companies.yaml (후보 전체, 다시 돌려도 사용자가 적은 status·memo 는 남는다)
정보원·점수 기준: references/sources.md "회사 찾기". 잡플래닛은 robots.txt 가 크롤러를 막아 쓰지 않는다.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import jobkit as K  # noqa: E402

REG = os.path.join(K.DATA, "search", "companies.yaml")
TECHBLOG = "https://raw.githubusercontent.com/maczniak/awesome-korean-techblog/master/README.md"
GITHUB_ORGS = "https://raw.githubusercontent.com/channy/korea-devculture/main/github.json"
SEED = os.path.join(K.RES, "references", "company_seed.yaml")        # 알려진 회사 (공개, 사용자가 더함)
SEED_LOCAL = os.path.join(K.DATA, "search", "company_seed.yaml")      # 개인 추가분 (선택)
WANTED = "https://www.wanted.co.kr"
WANTED_JOBS = [872, 674, 10110, 660, 899, 1634]   # 서버 · DevOps · 소프트웨어 엔지니어 · 웹 · 파이썬 · 머신러닝(회사 발견용, 공고 수집과 별개)

# 채용 시스템(ATS) 판별: 채용 사이트 URL·HTML 에서 찾는다. provider 가 있으면 scan.py 가 자동 수집한다
ATS = [
    ("greetinghr", r"[\w-]+\.career\.greetinghr\.com|greetinghr\.com", "greetinghr"),
    ("greenhouse", r"boards(?:-api)?\.greenhouse\.io/(?:v1/boards/)?[\w-]+|job-boards\.greenhouse\.io/[\w-]+|gh_jid=", "greenhouse"),
    ("lever", r"jobs\.lever\.co/[\w-]+", "lever"),
    ("ninehire", r"[\w-]+\.ninehire\.site|ninehire\.com", "ninehire"),
    ("hiworks", r"recruit\.[\w.-]+/recruit/(?:jobs|view/)|gabiaoffice\.hiworks\.com", "hiworks"),   # 가비아 하이웍스 채용 (JS 로 그림)
    ("workday", r"[\w-]+\.wd\d+\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?[\w-]+", "workday"),
    ("recruiter", r"[\w-]+\.recruiter\.co\.kr", "recruiter"),
    ("roundhr", r"[\w-]+\.recruit\.roundhr\.com|api-prod\.roundhr\.com|roundhr\.com/service", "roundhr"),   # 회사 도메인이면 아이콘 주소로만 보인다
    ("workable", r"apply\.workable\.com/(?!api/|j/)[\w-]+", "workable"),
    ("ashby", r"jobs\.ashbyhq\.com/[\w.-]+", "ashby"),
    ("skcareers", r"skcareers\.com/Recruit[^\"'\s<]*", "skcareers"),
    ("smartrecruiters", r"(?:jobs|careers)\.smartrecruiters\.com/[\w-]+", None),   # 아래는 지문만 (수집기 없음)
    ("teamtailor", r"[\w-]+\.teamtailor\.com", None),
    ("recruitee", r"[\w-]+\.recruitee\.com", None),
    ("bamboohr", r"[\w-]+\.bamboohr\.com/careers", None),
    ("notion", r"[\w-]+\.notion\.site|notion\.so/|[\w-]+\.oopy\.io", None),
    ("wanted", r"wanted\.co\.kr/(?:company|wd)/\d+", None),
]
CAREER_LINK = re.compile(r'href="([^"#]+)"[^>]*>(?:(?!</a>).){0,200}?(?:채용|인재\s*영입|커리어|Careers?|Recruit|Jobs|Join\s*us|We\'?re\s*hiring)',
                         re.I | re.S)
CAREER_HREF = re.compile(r'href="([^"#]*(?:career|recruit|jobs|hiring|join)[^"]*)"', re.I)


def _norm(name: str) -> str:
    """비교용 이름. sources.yaml company_aliases 를 먼저 보고, 영문은 corp·inc 같은 꼬리를 뗀다."""
    n = K.norm_company(name or "")
    return re.sub(r"(corporation|corp|inc|co\.?,?ltd|korea|코리아)$", "", re.sub(r"[^\w가-힣]", "", n)) or n


def _load() -> dict:
    return {c["key"]: c for c in (K.load_yaml(REG) or {}).get("companies", [])}


def _save(reg: dict):
    import yaml
    rows = sorted(reg.values(), key=lambda c: (-c.get("tier", 0), c["name"]))
    K.write_text(REG, "# discover.py 가 만든다. status(후보/추가/제외)·memo 는 손으로 고쳐도 다음 실행에 남는다.\n"
                 + yaml.safe_dump({"updated": K.TODAY, "companies": rows}, allow_unicode=True, sort_keys=False, width=200))


def _find(reg: dict, names) -> str:
    """이름·영문명 중 하나라도 이미 있는 회사면 그 키. 없으면 첫 이름의 키."""
    keys = [k for k in (_norm(n) for n in names) if k]
    for k in keys:
        if k in reg:
            return k
    for c in reg.values():
        if set(keys) & {_norm(x) for x in [c["name"]] + (c["signals"].get("aka") or [])}:
            return c["key"]
    return keys[0] if keys else ""


def _merge(reg: dict, name: str, **signals):
    key = _find(reg, [name] + list(signals.get("aka") or []))
    if not key:
        return
    c = reg.setdefault(key, dict(key=key, name=name, status="후보", signals={}))
    for k, v in signals.items():
        if k == "aka":
            c["signals"]["aka"] = sorted((set(c["signals"].get("aka") or []) | set(v or []) | {name}) - {c["name"]})
        elif v not in (None, "", [], {}):
            c["signals"][k] = v


# ── 정보원 ──────────────────────────────────────────────
def from_techblog(reg):
    status, md = K.http_get(TECHBLOG, accept="*/*")
    if status != 200:
        raise K.ShapeError(f"기술 블로그 목록 HTTP {status}")
    corp = md.split("## 기업 블로그")[1].split("\n## ")[0]
    n = 0
    for name, url, alt in re.findall(r"^\* \[([^\]]+)\]\(([^)]+)\)(?: \(([^)]*)\))?", corp, re.M):
        _merge(reg, name, techblog=url, aka=[a.strip() for a in re.sub(r"\[.*?\]\(.*?\)", "", alt or "").split(",") if a.strip()])
        n += 1
    return n


def from_github(reg):
    status, body = K.http_get(GITHUB_ORGS, accept="*/*")
    if status != 200:
        raise K.ShapeError(f"GitHub 조직 목록 HTTP {status}")
    rows = json.loads(body)
    for r in rows:
        orgs = r.get("organizations") or []
        _merge(reg, r["name"], github=[o["organization_id"] for o in orgs], github_followers=sum(o.get("followers", 0) for o in orgs))
    return len(rows)


def from_wanted(reg, max_pages: int = 30):
    """원티드에서 개발 직군 공고를 낸 회사 → 회사 상세의 연봉 수준·인원·설립·홈페이지."""
    ids = {}
    for jid in WANTED_JOBS:
        url = f"{WANTED}/api/chaos/navigation/v1/results?job_group_id=518&job_ids={jid}&country=kr&job_sort=job.latest_order&years=-1&locations=all&limit=100&offset=0"
        for _ in range(max_pages):
            d = K.get_json(url)
            for x in d.get("data") or []:
                ids[x["company"]["id"]] = x["company"]["name"]
            nxt = (d.get("links") or {}).get("next")
            if not nxt:
                break
            url = WANTED + nxt
    known = {c["signals"].get("wanted_id") for c in reg.values()}
    for i, (cid, name) in enumerate(ids.items(), 1):
        if cid in known:
            continue
        if i % 100 == 0:
            print(f"  … 원티드 회사 {i}/{len(ids)}", file=sys.stderr)
        try:
            c = K.get_json(f"{WANTED}/api/v4/companies/{cid}").get("company") or {}
        except K.ShapeError:
            continue
        tags = [t["title"] for t in c.get("company_tags") or []]
        _merge(reg, name, wanted_id=cid, homepage=(c.get("detail") or {}).get("link"), founded=c.get("founded_year"),
               industry=c.get("industry_name"), salary=next((t for t in tags if t.startswith("연봉상위")), None),
               headcount=next((t for t in tags if re.match(r"[\d,~]+명|\d+명이상", t)), None))
    return len(ids)


def from_seed(reg):
    rows = []
    for path in (SEED, SEED_LOCAL):
        rows += (K.load_yaml(path) or {}).get("companies") or []
    for r in rows:
        _merge(reg, r["name"], known=r.get("group") or True, homepage=r.get("home"), aka=r.get("aka") or [])
    return len(rows)


def from_sources(reg):
    """이미 sources.yaml 에 있는 회사는 '추가' 상태로 표시한다."""
    src = K.load_yaml(K.P["sources"]) or {}
    for c in src.get("companies") or []:
        _merge(reg, c["name"], careers=c.get("careers_url"), aka=re.findall(r"\((.*?)\)", c["name"]))
        reg[_find(reg, [c["name"]])]["status"] = "추가"
    return len(src.get("companies") or [])


# ── 점수 ──────────────────────────────────────────────
SALARY = {"연봉상위1%": 3.5, "연봉상위2~5%": 3.0, "연봉상위6~10%": 2.0, "연봉상위11~20%": 1.0}   # 원티드 회사 태그 (2026-09-30 실측)
HEAD = [(r"10,?001|1,?001~10,?000|1001", 2.0), (r"301~1,?000", 1.5), (r"51~300", 0.5)]


def tier(c: dict) -> float:
    s, sig = 0.0, c["signals"]
    s += SALARY.get(sig.get("salary", ""), 0)
    s += next((v for p, v in HEAD if re.search(p, sig.get("headcount") or "")), 0)
    s += 2.0 if sig.get("known") else 0          # company_seed.yaml 에 적힌 회사
    s += 1.5 if sig.get("techblog") else 0
    s += 1.0 if sig.get("github") else 0
    s += 0.5 if (sig.get("github_followers") or 0) >= 100 else 0
    return round(s, 1)


# ── 채용 사이트 찾기 ──────────────────────────────────────
def ats_of(url: str, html: str = ""):
    for name, pat, _ in ATS:
        m = re.search(pat, url or "", re.I) or re.search(pat, html or "", re.I)
        if m:
            return name, m.group(0)
    return None, None


def _home(c):
    sig = c["signals"]
    for u in (sig.get("careers"), sig.get("homepage"), sig.get("techblog")):
        if u and not re.search(r"medium\.com|tistory|youtube|github\.io|blog\.naver|velog|brunch", u):
            p = urllib.parse.urlparse(u if "//" in u else "https://" + u)
            return f"{p.scheme or 'https'}://{p.netloc}"
    return None


ASSET = re.compile(r"\.(png|jpe?g|gif|svg|webp|ico|css|js|pdf|woff2?)(\?|&|$)|/image\?src=", re.I)
MARKETING = re.compile(r"^https?://(www\.)?(greetinghr|ninehire)\.com|/cdn-cgi/|profiles\.greetinghr\.com", re.I)   # "powered by"·로고 링크 — 그 링크가 있던 페이지가 채용 사이트


def _links(base: str, html: str):
    raw = [m.group(1) for m in CAREER_LINK.finditer(html)] + [m.group(1) for m in CAREER_HREF.finditer(html)]
    out = []
    for x in raw:
        u = urllib.parse.urljoin(base + "/", x.replace("&amp;", "&"))
        if not x.startswith(("mailto:", "javascript:", "tel:")) and not ASSET.search(u) and u not in out:
            out.append(u)
    return out


def verify(ats: str, careers: str, name: str, **extra):
    """판별한 채용 시스템으로 목록을 실제로 받아 본다 → 공고 수 (실패하면 None). extra: company_id(나인하이어)·code(라운드HR)."""
    import providers
    mod = providers.BY_ATS.get(ats)
    if not mod or ats == "greenhouse":
        return None
    try:
        return len(mod.collect({"careers_url": careers, "name": name, "ats": ats, **extra}))
    except Exception:
        return None


def _identify(url: str, page: str, name: str, **extra):
    """페이지(주소·HTML·iframe·script)에 보이는 채용 시스템마다 목록을 받아 보고, 공고가 나온 것을 고른다.
    여러 시스템이 함께 보이면(예: 공고 없는 greetinghr 사이트 + Workday) 공고 수가 있는 쪽 → 0건이라도 받은 쪽 → 처음 본 쪽."""
    hrefs = [urllib.parse.urljoin(url, h.replace("&amp;", "&")) for h in re.findall(r'(?:href|src)="([^"#]+)"', page or "")] + [url]
    found = []
    for ats, pat, _ in ATS:
        m = re.search(pat, url, re.I) or re.search(pat, page or "", re.I)
        if not m:
            continue
        own = [x for x in hrefs if re.search(pat, x, re.I) and not MARKETING.search(x) and not ASSET.search(x)]
        if not own and ats in ("workday", "workable", "ashby", "lever", "greenhouse") and "/" in m.group(0):
            own = ["https://" + m.group(0)]      # 링크가 아니라 페이지 데이터 안에만 있는 주소 (예: jobs.ashbyhq.com/{회사}). 경로가 회사를 가리키는 시스템만
        careers = own[0] if own else url
        n = verify(ats, careers, name, **extra)
        found.append(dict(careers=careers, ats=ats, **({"verified": n} if n is not None else {})))
    return sorted(found, key=lambda r: (-(r.get("verified") or 0), "verified" not in r))[0] if found else None


SUBS = ("careers", "career", "recruit", "jobs", "talent", "join")
PATHS = ("/careers", "/career", "/career/jobs", "/careers/jobs", "/recruit", "/recruit/list", "/jobs", "/hiring", "/ko/careers")
POSTING = re.compile(r'href="[^"]*?/(?:jobs?|recruits?|careers?|positions?|openings?|o|detail|job_posting)/[\w-]*\d[\w-]*/?"', re.I)


def _guess(home: str):
    """채용 링크를 못 찾았을 때 흔한 채용 주소(하위 도메인·경로)를 붙여 본다.
    200 이어도 공고 링크 2개 이상이나 채용 시스템 지문이 없으면 버린다 (홈으로 돌려보내는 사이트가 많다)."""
    dom = re.sub(r"^www\.", "", urllib.parse.urlparse(home).netloc)   # 하위 도메인 회사(x.그룹.com)가 그룹 채용 사이트로 가지 않게 그대로 쓴다
    out, blocked = [], []
    for u in [f"https://{s}.{dom}/" for s in SUBS] + [home + x for x in PATHS]:
        try:
            st, page = K.http_get(u, accept="text/html", timeout=10)
        except OSError:          # 없는 하위 도메인 (DNS)
            continue
        if st == 200 and (len(set(POSTING.findall(page))) >= 2 or ats_of(u, page)[0]):
            out.append((u, page))
        elif st in (403, 429):   # 봇 차단 (나인하이어 등) — 브라우저로 볼 후보
            blocked.append(u)
    return out, blocked


def _links_hint(url: str, page: str) -> str:
    """평문 HTML 에 공고 링크가 2개 이상이면 htmllinks 용 links 정규식 제안 (숫자를 \\d+ 로)."""
    pats: dict[str, int] = {}
    for h in set(re.findall(r'href="([^"]*?/(?:jobs?|recruits?|careers?|positions?|openings?|o|detail|job_posting)/[\w-]*\d[\w-]*/?)"', page or "", re.I)):
        pat = re.sub(r"\d+", r"\\d+", re.escape(urllib.parse.urlparse(h).path))
        pats[pat] = pats.get(pat, 0) + 1
    if not pats:
        return ""
    pat, n = max(pats.items(), key=lambda x: x[1])
    return f"links: '{pat}' {n}건 (평문 HTML)" if n >= 2 else ""


JOBWORD = r"job|recruit|rec\b|posting|notice|position|announce|anno|opening|career|apply|due|employ"   # 사이트 장식용 목록(메뉴·앵커)과 가르기


def _job_lists(o, path="", out=None):
    """JSON 안에서 공고 목록처럼 보이는 곳 (제목·아이디 같은 키를 가진 dict 목록) → [(경로, 개수)]."""
    out = [] if out is None else out
    if isinstance(o, list) and o and all(isinstance(x, dict) for x in o[:3]):
        keys = " ".join(o[0])
        if re.search(r"title|subject|name|Nm\b", keys, re.I) and re.search(r"id\b|Id\b|Sn\b|seq|No\b|code", keys) \
                and re.search(JOBWORD, path + " " + keys, re.I):
            out.append((path.lstrip("."), len(o)))
    if isinstance(o, dict):
        for k, v in o.items():
            _job_lists(v, f"{path}.{k}", out)
    return out


def _browser(url: str) -> dict:
    """탐색 때만: 헤드리스 브라우저로 채용 페이지를 열어 네트워크를 본다 (playwright 가 없으면 건너뜀).
    공고 목록 JSON 이 안 보이면 '채용 공고·전체·더보기·View all' 버튼을 한 번 누른다.
    → ats_seen(요청 주소의 채용 시스템), company_id(나인하이어 API 의 companyId), hint(목록 API 와 브라우저 없이 재현되는지)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {}
    seen, hits = [], []

    def on_resp(r):
        seen.append(r.url)
        if r.request.resource_type in ("xhr", "fetch") and "json" in r.headers.get("content-type", ""):
            try:
                lists = _job_lists(r.json())
                post = r.request.post_data
            except Exception:            # JSON 아님·압축된 요청 본문
                return
            if lists:
                hits.append((r.request.method, r.url, post, max(lists, key=lambda x: x[1])))
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context(locale="ko-KR").new_page()
        page.on("response", on_resp)
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            if not hits:
                page.get_by_text(re.compile(r"^\s*(채용\s*공고|전체|더\s*보기|View all|Open positions)\s*$", re.I)).first.click(timeout=3000)
                page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        b.close()
    r = {}
    for ats, pat, prov in ATS:
        if prov and any(re.search(pat, u, re.I) for u in seen):
            r["ats_seen"] = ats
            break
    cid = next((m.group(1) for u in seen if "ninehire" in u or "_backend" in u for m in [re.search(r"companyId=([0-9a-f-]{36})", u)] if m), None)
    if cid:
        r["company_id"] = cid
    if hits:
        method, u, post, (path, n) = hits[0]
        try:
            body = json.loads(post) if post else None
        except ValueError:
            body = post
        st, text = K.http_post(u, body) if body is not None else K.http_get(u)
        ok = st == 200 and any(c == n for _, c in _job_lists(json.loads(text) if text.lstrip()[:1] in "[{" else {}))
        r["hint"] = f"{method} {u}{' ' + post[:200] if post else ''} → {path or '$'} {n}건 · 브라우저 없이 {'재현됨' if ok else '안 됨'}"
    return r


def probe_one(c: dict, browser: bool = True) -> dict:
    """홈페이지에서 채용 링크를 찾고(없으면 흔한 채용 주소를 붙여 보고), 페이지의 채용 시스템을 판별해 목록을 받아 검증한다.
    그래도 자체 사이트면 헤드리스 브라우저로 목록 API 를 찾는다 (references/judgment.md §2)."""
    home = _home(c)
    if not home:
        return dict(probe="홈페이지 모름")
    status, html = K.http_get(home, accept="text/html", timeout=15)
    if status != 200:
        return dict(probe=f"홈페이지 HTTP {status}", home=home)
    pages = [(home, html)]
    links = _links(home, html)
    for cand in [x for x in links if not MARKETING.search(x)][:3]:     # 채용 링크를 열어 안에 박힌 채용 시스템을 찾는다
        st, page = K.http_get(cand, accept="text/html", timeout=15)
        if st == 200:
            pages.append((cand, page))
    blocked = []
    if len(pages) == 1:
        guessed, blocked = _guess(home)
        pages += guessed
    for url, page in pages[1:] + pages[:1]:
        r = _identify(url, page, c["name"])
        if r:
            return dict(probe="찾음", home=home, **r)
    if len(pages) > 1:
        r = dict(probe="찾음", home=home, careers=pages[1][0], ats="자체")
        hint = _links_hint(*pages[1])
        if hint:
            r["hint"] = hint
    elif blocked:
        r = dict(probe="찾음 · 봇 차단", home=home, careers=blocked[0], ats="자체")
    else:
        r = dict(probe="채용 링크 없음", home=home)
    return _with_browser(r, r.get("careers") or home, c["name"]) if browser and "hint" not in r else r


def _with_browser(r: dict, url: str, name: str) -> dict:
    """자체 사이트로 남은 결과에 브라우저 관찰을 더한다: 요청에 채용 시스템이 보이면 그 시스템으로 검증, 아니면 hint(목록 API)를 남긴다."""
    b = _browser(url)
    if b.get("ats_seen"):
        n = verify(b["ats_seen"], url, name, **({"company_id": b["company_id"]} if b.get("company_id") else {}))
        r.update(probe=r["probe"].replace("채용 링크 없음", "찾음") + " · 브라우저", careers=url, ats=b["ats_seen"],
                 **({"verified": n} if n is not None else {}))
    r.update({k: b[k] for k in ("company_id", "hint") if k in b})
    return r


# ── 명령 ──────────────────────────────────────────────
def cmd_collect(a):
    reg = _load()
    for label, fn in (("기술 블로그", from_techblog), ("GitHub 조직", from_github), ("알려진 회사", from_seed),
                      ("sources.yaml", from_sources), ("원티드", from_wanted)):
        if label == "원티드" and a.skip_wanted:
            continue
        try:
            print(f"  {label:<12} {fn(reg)}건")
        except Exception as e:
            print(f"  {label:<12} ✗ {type(e).__name__}: {e}")
    for c in reg.values():
        c["tier"] = tier(c)
    _save(reg)
    print(f"후보 {len(reg)}곳 → {os.path.relpath(REG, K.ROOT)}")


def cmd_probe(a):
    reg = _load()
    todo = [c for c in sorted(reg.values(), key=lambda c: -c.get("tier", 0))
            if c["status"] == "후보" and c.get("tier", 0) >= a.min and (a.again or "probe" not in c)][:a.top]
    for i, c in enumerate(todo, 1):
        for k in ("careers", "ats", "verified", "home", "company_id", "hint"):     # 다시 조사할 때 이전 결과가 남지 않게
            if k != "careers" or c["status"] == "후보":
                c.pop(k, None)
        try:
            c.update(probe_one(c, browser=not a.no_browser))
        except Exception as e:
            c["probe"] = f"오류 {type(e).__name__}"
        c["probed"] = K.TODAY
        print(f"  [{i}/{len(todo)}] {c['name']}: {c['probe']} {c.get('ats') or ''} {c.get('careers') or ''}")
        if i % 20 == 0:
            _save(reg)
    _save(reg)


def classify(c: dict, careers: str, via: str, browser: bool = True) -> dict:
    """밖에서 찾은 채용 사이트 URL 로 채용 시스템을 판별하고 목록을 받아 검증한다."""
    st: int | str                             # HTTP 상태, 또는 연결 실패의 예외 이름
    try:
        st, page = K.http_get(careers, accept="text/html", timeout=15)
    except OSError as e:                      # TLS 거부·DNS 실패 — URL 은 남기고 판별만 건너뛴다
        st, page = type(e).__name__, ""
    r = dict(probe=f"찾음 ({via})", careers=careers, ats="자체")
    r.update(_identify(careers, page if st == 200 else "", c["name"]) or {})
    if st != 200:
        r["probe"] += f" · HTTP {st}"
    if r["ats"] == "자체" and _links_hint(careers, page):
        r["hint"] = _links_hint(careers, page)
    return _with_browser(r, careers, c["name"]) if r["ats"] == "자체" and browser and "hint" not in r else r


def cmd_missing(a):
    reg = _load()
    rows = [c for c in sorted(reg.values(), key=lambda c: -c.get("tier", 0))
            if c["status"] == "후보" and c.get("tier", 0) >= a.min and c.get("probed") and not c.get("careers")]
    for c in rows:
        print(f"{c['name']}\t{c.get('tier')}\t{c.get('probe')}\t{c.get('home') or c['signals'].get('homepage') or ''}")


def cmd_set(a):
    reg = _load()
    for line in K.read_text(a.file).splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        name, url, *via = [x.strip() for x in line.split("\t")]
        c = reg.get(_find(reg, [name]))
        if not c:
            print(f"  {name}: 후보에 없음 — 건너뜀")
            continue
        if not url or url == "-":
            c["probe"] = f"채용 사이트 없음 ({via[0] if via else '수동'})"
            continue
        for k in ("careers", "ats", "verified", "company_id", "hint"):
            c.pop(k, None)
        c.update(classify(c, url, via[0] if via else "수동", browser=not a.no_browser))
        c["probed"] = K.TODAY
        print(f"  {c['name']}: {c['probe']} {c.get('ats')} {'검증 ' + str(c['verified']) + '건' if 'verified' in c else ''} {url}")
    _save(reg)


def cmd_report(a):
    reg = _load()
    rows = [c for c in sorted(reg.values(), key=lambda c: -c.get("tier", 0)) if c.get("tier", 0) >= a.min]
    print("| 회사 | 점수 | 근거 | 채용 사이트 | ATS | 수집 | 상태 |\n|---|---|---|---|---|---|---|")
    for c in rows:
        s = c["signals"]
        why = " · ".join(x for x in (s.get("salary"), s.get("headcount"), str(s["known"]) if s.get("known") else "",
                                      "기술블로그" if s.get("techblog") else "",
                                      "GitHub" if s.get("github") else "") if x)
        auto = (f"자동 ({c['verified']}건)" if c.get("verified") is not None else
                "자동" if c.get("ats") == "greenhouse" else "브라우저" if c.get("careers") else "—")
        print(f"| {c['name']} | {c.get('tier', 0)} | {why} | {c.get('careers') or c.get('probe', '')} | {c.get('ats') or ''} | {auto} | {c['status']} |")


def cmd_promote(a):
    import yaml
    reg, src = _load(), K.load_yaml(K.P["sources"]) or {}
    have = {_norm(c["name"]) for c in src.get("companies") or []}
    black = K.blacklist_companies()
    hosts = {urllib.parse.urlparse(c.get("careers_url") or "").netloc for c in src.get("companies") or []} - {""}
    supported = {n: prov for n, _, prov in ATS if prov}
    add = []
    for c in sorted(reg.values(), key=lambda c: -c.get("tier", 0)):
        known = bool(c["signals"].get("known"))   # company_seed.yaml 의 유명 회사는 점수와 상관없이 넣는다
        if c["status"] != "후보" or (c.get("tier", 0) < a.min and not known) or not c.get("careers") or c["key"] in have:
            continue
        if K.company_in(c["name"], black, exact=True):     # 지원하지 않을 회사 (blacklist.md)
            c["status"] = "제외"
            continue
        if urllib.parse.urlparse(c["careers"]).netloc in hosts or c.get("ats") == "wanted":   # 이미 수집하는 곳 (모회사 채용 사이트·원티드)
            c["status"] = "추가"
            continue
        auto = c.get("verified") is not None or (c.get("ats") == "greenhouse" and "greenhouse.io" in c["careers"])
        if not auto and c.get("tier", 0) < a.min_browser and not known:
            continue
        e = dict(name=c["name"], careers_url=c["careers"], priority=True, found_by="discover.py " + K.TODAY)
        if c.get("ats") == "greenhouse":
            m = re.search(r"(?:boards(?:-api)?\.greenhouse\.io/(?:v1/boards/)?|job-boards\.greenhouse\.io/)([\w-]+)", c["careers"])
            if m:
                e["api"] = f"https://boards-api.greenhouse.io/v1/boards/{m.group(1)}/jobs"
        if auto and c.get("ats") in supported:
            e["ats"] = c["ats"]
            if c.get("company_id"):
                e["company_id"] = c["company_id"]
        else:
            e["method"] = "browser"
            if c.get("hint"):                # 탐색이 찾은 읽는 법 (목록 API 또는 links) — 설정으로 옮기면 자동 수집 (references/judgment.md §2)
                e["browse"] = dict(url=c["careers"], how="jsonapi" if "links:" not in c["hint"] else "links", note=c["hint"])
        add.append(e)
        c["status"] = "추가"
    print(f"sources.yaml 에 추가할 회사 {len(add)}곳 (자동 수집 {sum(1 for e in add if 'ats' in e)} · 브라우저 {sum(1 for e in add if 'method' in e)})")
    for e in add:
        print(f"  {e['name']:<24} {e.get('ats') or '브라우저':<10} {e['careers_url']}")
    if a.dry_run or not add:
        return
    text = K.read_text(K.P["sources"]).rstrip() + "\n" + yaml.safe_dump(add, allow_unicode=True, sort_keys=False, width=200)
    K.write_text(K.P["sources"], text)       # companies: 가 파일 끝 목록이라는 전제 (아래 검사)
    if len((K.load_yaml(K.P["sources"]) or {}).get("companies") or []) < len(have) + len(add):
        sys.exit("sources.yaml 구조가 예상과 달라 추가가 companies 목록에 들어가지 않았습니다. 손으로 확인하세요.")
    _save(reg)


def main(argv=None):
    ap = argparse.ArgumentParser(description="회사 찾기")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("collect"); p.add_argument("--skip-wanted", action="store_true")
    p = sub.add_parser("probe"); p.add_argument("--top", type=int, default=60); p.add_argument("--min", type=float, default=2.5)
    p.add_argument("--no-browser", action="store_true", help="헤드리스 브라우저 관찰(F)을 건너뜀")
    p.add_argument("--again", action="store_true")
    p = sub.add_parser("report"); p.add_argument("--min", type=float, default=2.5)
    p = sub.add_parser("missing"); p.add_argument("--min", type=float, default=2.5)
    p = sub.add_parser("set"); p.add_argument("file"); p.add_argument("--no-browser", action="store_true")
    p = sub.add_parser("promote"); p.add_argument("--min", type=float, default=2.5, help="자동 수집(검증된 채용 시스템) 최소 점수")
    p.add_argument("--min-browser", type=float, default=4.0, help="브라우저 수집 최소 점수 (매번 손이 가서 더 높게, 유명 회사 목록은 예외)")
    p.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    return {"collect": cmd_collect, "probe": cmd_probe, "report": cmd_report, "promote": cmd_promote,
            "missing": cmd_missing, "set": cmd_set}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
