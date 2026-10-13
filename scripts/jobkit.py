# -*- coding: utf-8 -*-
"""공고 수집·기록 공통 도구. scan.py / alive.py / tracker.py 가 쓴다.

표준 라이브러리 + PyYAML 만 쓴다. 파일 형식은 modes/scan.md, modes/track.md 기준.
"""
from __future__ import annotations

import gzip
import html
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
P = dict(
    sources=os.path.join(DATA, "search", "sources.yaml"),
    targets=os.path.join(DATA, "profile", "targets.yaml"),
    pipeline=os.path.join(DATA, "search", "pipeline.md"),
    history=os.path.join(DATA, "search", "scan-history.tsv"),
    blacklist=os.path.join(DATA, "search", "blacklist.md"),
    inbox=os.path.join(DATA, "search", "inbox"),
    checks=os.path.join(DATA, "search", "manual-checks.yaml"),   # 스크립트가 못 도는 채널을 손으로 확인한 결과
    tracker=os.path.join(DATA, "applications", "tracker.md"),
)
HISTORY_COLS = ["url", "first_seen", "portal", "title", "company", "status", "location",
                "fingerprint", "posted_at", "trust_score", "trust_flags", "normalized_company"]
TODAY = date.today().isoformat()


# ── HTTP ──────────────────────────────────────────────
class _Redirect308(urllib.request.HTTPRedirectHandler):
    """파이썬 3.9 urllib 은 308 을 따라가지 않는다 (3.11부터 지원). 307 처럼 다룬다."""
    def http_error_308(self, req, fp, code, msg, headers):
        return self.http_error_307(req, fp, code, msg, headers)

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if code == 308:
            code = 307
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_Redirect308)
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
_last: Dict[str, float] = {}
_locks: Dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()
_KR_2LD = {"co", "or", "go", "ac", "ne", "re", "pe"}


def site(host: str) -> str:
    """요청 간격을 두는 단위. 등록 도메인으로 묶는다 (a.greetinghr.com · b.greetinghr.com → greetinghr.com)."""
    parts = host.split(":")[0].lower().split(".")
    n = 3 if len(parts) >= 3 and parts[-1] == "kr" and parts[-2] in _KR_2LD else 2
    return ".".join(parts[-n:])


def http_get(url: str, accept: str = "application/json", delay: float = 1.0, timeout: int = 20, headers: Optional[dict] = None,
             data: Optional[bytes] = None):
    """(status, text). 같은 사이트에는 한 번에 하나씩, 앞 요청이 끝난 뒤 delay 초 간격을 둔다 (references/sources.md 공통 규칙).
    스레드에서 동시에 불러도 지켜진다. data 가 있으면 POST. gzip 으로 받아 풀어서 돌려준다 (안 하는 사이트는 그대로)."""
    key = site(url.split("/")[2])
    with _locks_guard:
        lock = _locks.setdefault(key, threading.Lock())
    with lock:
        wait = _last.get(key, 0) + delay - time.time()
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept, "Accept-Encoding": "gzip", **(headers or {})},
                                     data=data)
        try:
            with _OPENER.open(req, timeout=timeout) as r:
                raw = r.read()
                if (r.headers.get("Content-Encoding") or "").lower() == "gzip":
                    raw = gzip.decompress(raw)
                status, body = r.status, raw.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            status, body = e.code, ""
        finally:
            _last[key] = time.time()
    return status, body


def http_post(url: str, body, **kw):
    """(status, text). body 가 dict 면 JSON, 문자열이면 폼(application/x-www-form-urlencoded)으로 보낸다."""
    is_json = not isinstance(body, str)
    ctype = "application/json" if is_json else "application/x-www-form-urlencoded; charset=UTF-8"
    data = (json.dumps(body, ensure_ascii=False) if is_json else body).encode("utf-8")
    return http_get(url, headers={"Content-Type": ctype, **(kw.pop("headers", None) or {})}, data=data, **kw)


def get_json(url: str, **kw):
    status, body = http_get(url, **kw)
    if status != 200:
        raise ShapeError(f"HTTP {status}: {url}")
    try:
        return json.loads(body)
    except ValueError:
        raise ShapeError(f"JSON 아님: {url}")


class ShapeError(Exception):
    """응답 형식이 예상과 다름. 조용히 0건으로 넘기지 않고 보고한다."""


def html_text(s: Optional[str]) -> str:
    if not s:
        return ""
    s = html.unescape(s)
    s = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h\d>|</div>", "\n", s)
    s = re.sub(r"(?i)<li[^>]*>", "• ", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("\r", "")
    return re.sub(r"\n\s*\n+", "\n\n", re.sub(r"[ \t\xa0]+", " ", s)).strip()


# ── 공고 ──────────────────────────────────────────────
@dataclass
class Job:
    source: str          # wanted / jumpit / greenhouse:daangn / toss / nhn / kakao / greetinghr:kurly
    id: str
    url: str
    company: str
    title: str
    location: str = ""
    posted_at: str = ""
    closes_at: str = ""
    text: str = ""       # 자격요건·우대·주요업무 본문 (없으면 detail 로 채운다)
    extra: dict = field(default_factory=dict)


def _norm_raw(s: str) -> str:
    return re.sub(r"\(.*?\)|㈜|주식회사|\s+", "", s or "").lower()


_ALIAS: Optional[Dict[str, str]] = None


def _aliases() -> Dict[str, str]:
    """sources.yaml company_aliases: {대표 이름: [다른 표기, …]} → 정규화 이름 → 대표 이름."""
    global _ALIAS
    if _ALIAS is None:
        alias = {}   # 다 채운 뒤에 넣는다 (수집 스레드가 채우는 중인 빈 dict 를 읽지 않게)
        for canon, names in (load_yaml(P["sources"]).get("company_aliases") or {}).items():
            for n in [canon] + list(names or []):
                alias[_norm_raw(n)] = _norm_raw(canon)
        _ALIAS = alias
    return _ALIAS


def norm_company(s: str) -> str:
    """회사 이름 비교용. 별칭 → 괄호 안 이름 → 공백으로 나눈 조각 순서로 대표 이름을 찾는다.
    예: "Ganada" → 가나다, "Toss Payments(토스페이먼츠)" → 토스페이먼츠, "TVING 티빙" → 티빙"""
    a = _aliases()
    raw = _norm_raw(s)
    if raw in a:
        return a[raw]
    for part in re.findall(r"\((.*?)\)", s or "") + (s or "").split():
        if _norm_raw(part) in a:
            return a[_norm_raw(part)]
    return raw


def load_yaml(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# ── 필터 ──────────────────────────────────────────────
def _kw_hit(kw: str, title: str) -> bool:
    """title-keywords 규칙: 'word:X' 는 단어 단위, 2~3자 영문은 단어 단위, 그 외는 부분 문자열."""
    t = title.lower()
    if kw.startswith("word:") or re.fullmatch(r"[A-Za-z]{2,3}", kw.strip()):
        w = kw[5:] if kw.startswith("word:") else kw.strip()
        return re.search(rf"(?<![a-z]){re.escape(w.lower())}(?![a-z])", t) is not None
    return kw.lower() in t


def title_ok(title: str, tf: dict) -> Optional[str]:
    """통과면 None, 아니면 제외 사유."""
    if any(_kw_hit(k, title) for k in tf.get("negative", [])):
        return "skipped_title"
    if tf.get("positive") and not any(_kw_hit(k, title) for k in tf["positive"]):
        return "skipped_title"
    return None


def location_check(loc: str, lf: dict) -> str:
    """'ok' / 'block' / 'unknown'."""
    l = (loc or "").lower()
    if any(k.lower() in l for k in lf.get("always_allow", [])):
        return "ok"
    if any(k.lower() in l for k in lf.get("block", [])):
        return "block"
    if any(k.lower() in l for k in lf.get("allow", [])):
        return "ok"
    return "unknown"


def career_check(career, cf: dict) -> Optional[str]:
    """(최소, 최대) 연차가 있을 때만 판정. sources.yaml career_filter. 값이 없으면 통과."""
    if not cf or not career or career[0] in (None, ""):
        return None
    try:
        lo = int(career[0] or 0)
        hi = int(career[1]) if career[1] not in (None, "", 0, "0") else 100
    except (TypeError, ValueError):
        return None
    if "exclude_if_max_below" in cf and hi < cf["exclude_if_max_below"]:
        return "skipped_career"
    if "exclude_if_min_at_least" in cf and lo >= cf["exclude_if_min_at_least"]:
        return "skipped_career"
    return None


LANGS = ["Java", "Kotlin", "Python", "Go", "Golang", "C#", "C++", "Node", "TypeScript", "Ruby", "PHP", "Scala", "Rust"]
_REQ = re.compile(r"(필요해요|필요합니다|있어야|필수|능숙하신|능숙한 분|요구|이상인 분|하신 분|required|must)")
_PREF = re.compile(r"(좋아요|좋습니다|우대|더 좋|이면 좋|plus|preferred|nice to have)")


def stack_hint(text: str) -> str:
    """자격요건 문장에서 언어 언급을 필수/우대로 나눈 힌트. 거르지 않는다 — 판정은 evaluate/1차 선별에서."""
    req, pref = set(), set()
    for sent in re.split(r"[\n•·]|(?<=[.!?요다])\s", text or ""):
        langs = [x for x in LANGS if re.search(rf"(?<![A-Za-z]){re.escape(x)}(?![A-Za-z#+])", sent)]
        if not langs:
            continue
        (pref if _PREF.search(sent) else req if _REQ.search(sent) else pref).update(langs)
    req -= {"Golang"}
    parts = []
    if req:
        parts.append("필수 추정 " + "/".join(sorted(req)))
    if pref - req:
        parts.append("우대·언급 " + "/".join(sorted(pref - req)))
    return "; ".join(parts) or "언어 언급 없음"


# ── 파일 ──────────────────────────────────────────────
def read_history() -> List[dict]:
    if not os.path.exists(P["history"]):
        return []
    rows = []
    with open(P["history"], encoding="utf-8") as f:
        head = f.readline().rstrip("\n").split("\t")
        for line in f:
            v = line.rstrip("\n").split("\t")
            rows.append(dict(zip(head, v + [""] * (len(head) - len(v)))))
    return rows


def append_history(rows: List[dict]):
    new = not os.path.exists(P["history"])
    with open(P["history"], "a", encoding="utf-8") as f:
        if new:
            f.write("\t".join(HISTORY_COLS) + "\n")
        for r in rows:
            f.write("\t".join(str(r.get(c, "")).replace("\t", " ").replace("\n", " ") for c in HISTORY_COLS) + "\n")


def read_text(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return f.read()


def write_text(path: str, s: str):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(s)
    os.replace(tmp, path)    # 중간에 끊겨도 원본이 반쯤 쓰이지 않게


URL_RE = re.compile(r"https?://[^\s|)>\];,]+")


def pipeline_urls() -> set:
    return set(URL_RE.findall(read_text(P["pipeline"])))


def dup_keys(company: str, title: str) -> set:
    """같은 공고를 다른 사이트에서 만났는지 보는 (회사, 포지션) 키들.
    회사는 괄호 안·밖 표기를 모두 후보로 ("에이비일팔공(AB180)" ↔ "AB180").
    포지션은 기호·공백과 '채용·모집·영입', 맨 앞 [회사명] 꼬리표만 뗀다 — 괄호 안 팀 이름은 남겨 다른 공고가 합쳐지지 않게."""
    s = company or ""
    parts = re.findall(r"\((.*?)\)", s) + re.split(r"\s+[-–|/]\s+", re.sub(r"\(.*?\)", "", s))   # "AB180 - 에이비일팔공" (LinkedIn)
    cos = {norm_company(s)} | {norm_company(p) for p in parts}
    cos.discard("")
    t = title or ""
    m = re.match(r"\s*\[([^\]]+)\]\s*", t)
    if m and (norm_company(m.group(1)) in cos or _norm_raw(m.group(1)) in _norm_raw(s)):
        t = t[m.end():]
    t = re.sub(r"[^0-9a-z가-힣]", "", re.sub(r"채용|모집|영입", "", t.lower()))
    return {(c, t) for c in cos}


def pipeline_keys() -> set:
    """pipeline.md 체크리스트 줄의 (회사, 포지션). 다른 사이트에 같은 공고가 올라온 경우를 거른다."""
    keys = set()
    for line in read_text(P["pipeline"]).split("\n"):
        if line.lstrip().startswith("- ["):
            c = [x.strip() for x in line.split(" | ")]
            if len(c) > 2:
                keys |= dup_keys(c[1], c[2])
    return keys


def insert_under(md: str, header: str, lines: List[str], before: Optional[str] = None) -> str:
    """header 섹션 맨 위에 lines 를 넣는다. 섹션이 없으면 before 섹션 앞(없으면 끝)에 만든다."""
    block = "\n".join(lines)
    m = re.search(rf"^{re.escape(header)}.*$", md, re.M)      # "## 지원 완료 — 재지원 쿨다운 (6개월)" 처럼 뒤에 붙은 말 허용
    if m:
        return md[:m.end()] + "\n\n" + block + md[m.end():]
    sec = f"{header}\n\n{block}\n\n"
    b = re.search(rf"^{re.escape(before)}", md, re.M) if before else None
    if b:
        return md[:b.start()] + sec + md[b.start():]
    return md.rstrip() + "\n\n" + sec


def move_line(md: str, url: str, header: str, suffix: str, before: Optional[str] = None) -> str:
    """url 이 든 체크리스트 줄을 header 섹션으로 옮기고 상태 표시를 [-] 로 바꾼다."""
    out, moved = [], None
    for line in md.split("\n"):
        if moved is None and url in line and line.lstrip().startswith("- ["):
            moved = re.sub(r"^(\s*)- \[.\]", r"\1- [-]", line) + f" | {suffix}"
            continue
        out.append(line)
    if moved is None:
        return md
    return insert_under("\n".join(out), header, [moved], before)


# ── 지원 현황 ──────────────────────────────────────────
STATES = ["평가함", "지원함", "서류합격", "면접", "최종합격", "입사", "불합격", "포기", "제외"]
TRACKER_HEAD = "| # | 날짜 | 회사 | 포지션 | 점수 | 상태 | PDF | 평가 | 메모 |"


def read_tracker() -> List[dict]:
    rows = []
    for line in read_text(P["tracker"]).split("\n"):
        if not re.match(r"\|\s*\d+\s*\|", line):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        rows.append(dict(num=int(c[0]), date=c[1], company=c[2], role=c[3], score=c[4], state=c[5],
                         pdf=c[6], eval=c[7], memo="|".join(c[8:]).strip(), raw=line))
    return rows


def tracker_line(r: dict) -> str:
    return (f"| {r['num']} | {r['date']} | {r['company']} | {r['role']} | {r['score']} | {r['state']} | "
            f"{r['pdf']} | {r['eval']} | {r['memo']} |")


def cooldown_companies(reapply_days: int) -> Dict[str, str]:
    """지원 이후 reapply_days 가 지나지 않은 회사 → 쿨다운 종료일."""
    out = {}
    for r in read_tracker():
        if r["state"] in ("지원함", "서류합격", "면접", "불합격") and "쿨다운 제외" not in r["memo"]:   # 다른 직무 재지원이 되는지 확인 중인 회사
            try:
                d = datetime.strptime(r["date"], "%Y-%m-%d").date()
            except ValueError:
                continue
            end = date.fromordinal(d.toordinal() + reapply_days)
            if end >= date.today():
                for name in re.split(r"[()]", r["company"]):
                    if name.strip():
                        out[norm_company(name)] = end.isoformat()
    return out


def blacklist_companies() -> set:
    out = set()
    for line in read_text(P["blacklist"]).split("\n"):
        m = re.match(r"\|\s*([^|]+?)\s*\|\s*\d{4}-", line)
        if m:
            out.add(norm_company(m.group(1)))
    return out


def company_in(company: str, names, exact: bool = False) -> Optional[str]:
    """exact=True 면 정규화한 이름이 같을 때만 (쿨다운: '가나다증권' 지원이 '가나다' 공고까지 막지 않게)."""
    n = norm_company(company)
    for x in names:
        if x and (x == n if exact else (x in n or n in x)):
            return x
    return None
