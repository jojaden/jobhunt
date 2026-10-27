# -*- coding: utf-8 -*-
"""OpenDART (금융감독원 전자공시, 사용자 본인 키): 회사 고유번호, 기업개황(대표자·사업자등록번호), 매출·영업이익, 감사보고서 목록.

명세: https://opendart.fss.or.kr/guide/main.do (2026-10-27 확인). 하루 2만 건.
매출·영업이익은 사업보고서를 내는 회사(상장사·주요 비상장사)면 단일회사 주요계정에서, 나머지는 최근 감사보고서 원문의
손익계산서 표(표준계정코드 ACODE)에서 읽는다. 읽지 못한 보고서는 링크와 함께 옮겨 적으라고 알린다.
오류 메시지에 키가 든 주소를 넣지 않는다.
"""
from __future__ import annotations

import html
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import date
from typing import Any, Dict, List, NoReturn, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jobkit as K  # noqa: E402
from nps import core_name, norm  # noqa: E402

BASE = "https://opendart.fss.or.kr/api"
VIEW = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo="
SEARCH = "https://dart.fss.or.kr/dsab007/main.do?option=corp&textCrpNm="
CACHE = os.path.join(os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"), "jobhunt", "dart-corpcode.xml")
CACHE_DAYS = 7
KEY_HELP = "DART 키가 거절됨: 인증키를 다시 확인하세요 (jobhunt keys)"
REVENUE = ("매출액", "수익(매출액)", "영업수익", "매출")
PROFIT = ("영업이익", "영업이익(손실)")
# 감사보고서 원문 손익계산서의 표준계정코드 (ACODE, 2026-10-27 감사보고서 3건에서 확인): 매출액·영업수익, 영업이익(손실)
ACODES = {"12100000010000": "revenue", "12500000010000": "operating_profit"}
UNITS = {"원": 1, "천원": 1_000, "백만원": 1_000_000}


class Ambiguous(Exception):
    """이름이 같은 회사가 여럿."""


def _fail(status: str, message: str, what: str) -> NoReturn:
    if status in ("010", "011", "012", "901"):
        raise RuntimeError(KEY_HELP)
    if status == "020":
        raise RuntimeError("DART 요청 제한 (하루 2만 건): 내일 다시")
    if status == "800":
        raise RuntimeError("DART 시스템 점검 중: 잠시 뒤 다시")
    raise RuntimeError(f"DART {what} 오류 {status}: {message}")


def _call(path: str, what: str, key: str, **params: Any) -> Optional[Dict[str, Any]]:
    """JSON 응답. 조회된 자료가 없으면(013) None."""
    status, body = K.http_get(f"{BASE}/{path}?" + urllib.parse.urlencode(dict(params, crtfc_key=key)))
    if status == 429:
        _fail("020", "", what)
    if status != 200:
        raise RuntimeError(f"DART {what} HTTP {status}")
    try:
        d = json.loads(body)
    except ValueError:
        raise K.ShapeError(f"DART {what} 응답이 JSON 이 아님") from None
    if not isinstance(d, dict) or "status" not in d:
        raise K.ShapeError(f"DART {what} 응답에 status 없음")
    if d["status"] == "013":
        return None
    if d["status"] != "000":
        _fail(d["status"], d.get("message", ""), what)
    return d


def ping(key: str) -> None:
    """키가 쓰이는지 한 번 불러 본다 (삼성전자 기업개황, 명세의 예시 고유번호)."""
    _call("company.json", "기업개황", key, corp_code="00126380")


def _status_fail(raw: bytes, what: str) -> NoReturn:
    """zip 을 달라고 했는데 아닌 응답: 키 오류 등은 상태 코드가 든 XML·JSON 으로 온다."""
    m = re.search(r'<status>(\d+)</status>|"status"\s*:\s*"(\d+)"', raw.decode("utf-8", "replace"))
    if m:
        _fail(m.group(1) or m.group(2), "", what)
    raise K.ShapeError(f"DART {what} 가 zip 이 아님")


def _download(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": K.UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def corp_codes(key: str) -> List[Tuple[str, str, str]]:
    """[(고유번호, 정식 이름, 종목코드)]. 공시 대상 회사 전체 목록(zip)을 받아 일주일 동안 캐시에 둔다."""
    if not os.path.exists(CACHE) or time.time() - os.path.getmtime(CACHE) > CACHE_DAYS * 86400:
        raw = _download(f"{BASE}/corpCode.xml?" + urllib.parse.urlencode(dict(crtfc_key=key)))
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                xml = z.read(z.namelist()[0])
        except zipfile.BadZipFile:
            _status_fail(raw, "고유번호 목록")
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        with open(CACHE + ".tmp", "wb") as f:
            f.write(xml)
        os.replace(CACHE + ".tmp", CACHE)
    out = []
    for el in ET.parse(CACHE).getroot().iter("list"):
        code, name = el.findtext("corp_code"), el.findtext("corp_name")
        if code and name:
            out.append((code.strip(), name.strip(), (el.findtext("stock_code") or "").strip()))
    if not out:
        raise K.ShapeError("DART 고유번호 목록에 list 없음")
    return out


def company(key: str, code: str) -> Dict[str, Any]:
    """기업개황: corp_name, ceo_nm, bizr_no, corp_cls, est_dt …"""
    d = _call("company.json", "기업개황", key, corp_code=code)
    if not d or "corp_name" not in d:
        raise K.ShapeError("DART 기업개황 응답에 corp_name 없음")
    return dict(d, corp_code=code)              # 명세의 응답 항목에는 고유번호가 없다


def find(key: str, name: str, ceo: str = "") -> Dict[str, Any]:
    """이름이 정확히 같은 회사의 기업개황. 여럿이면 대표자 이름(ceo, 원티드 표의 대표자명)이 같은 회사로 좁힌다."""
    hits = [c for c in corp_codes(key) if norm(c[1]) == norm(name)]
    if not hits:
        raise LookupError(f"DART 에서 '{name}' 을 찾지 못함 (공시한 적 없는 회사일 수 있음)")
    if len(hits) == 1:
        return company(key, hits[0][0])
    infos = [company(key, c[0]) for c in hits[:5]]
    same = [i for i in infos if ceo and norm(ceo) in norm(i.get("ceo_nm", ""))]
    if len(same) == 1:
        return same[0]
    raise Ambiguous("\n".join(f"  고유번호 {i.get('corp_code', '')}  {i['corp_name']} · 대표 {i.get('ceo_nm', '')} · {i.get('adres', '')}"
                              for i in infos))


def _amount(v: Any) -> Optional[int]:
    s = str(v or "").replace(",", "").strip()
    return int(s) if re.fullmatch(r"-?\d+", s) else None


def eok(won: int) -> float:
    """원 → 억 원 (소수 첫째 자리)."""
    x = round(won / 1e8, 1)
    return int(x) if x == int(x) else x


def finance(key: str, code: str, this_year: int) -> Tuple[str, List[Dict[str, Any]]]:
    """(사업보고서 접수번호, [{year, revenue, operating_profit} 억 원]). 사업보고서가 없는 회사면 ("", [])."""
    for year in (this_year - 1, this_year - 2):        # 사업보고서는 이듬해 3월쯤 나온다
        d = _call("fnlttSinglAcnt.json", "주요계정", key, corp_code=code, bsns_year=year, reprt_code="11011")
        if d is None:
            continue
        rows = d.get("list")
        if not isinstance(rows, list):
            raise K.ShapeError("DART 주요계정 응답에 list 없음")
        rows = [r for r in rows if isinstance(r, dict)]
        cfs = [r for r in rows if r.get("fs_div") == "CFS"]
        rows = cfs or rows                                 # 연결재무제표가 있으면 그것으로
        by_year: Dict[int, Dict[str, Any]] = {}
        for r in rows:
            nm = r.get("account_nm", "")
            field = "revenue" if nm in REVENUE else "operating_profit" if nm in PROFIT else ""
            if not field:
                continue
            for col, y in (("thstrm_amount", year), ("frmtrm_amount", year - 1), ("bfefrmtrm_amount", year - 2)):
                v = _amount(r.get(col))
                if v is not None:
                    by_year.setdefault(y, {"year": y}).setdefault(field, eok(v))
        rcept = next((r.get("rcept_no", "") for r in rows if r.get("rcept_no")), "")
        return rcept, [by_year[y] for y in sorted(by_year)]
    return "", []


def audits(key: str, code: str, today: date, n: int = 2) -> List[Dict[str, str]]:
    """최근 감사보고서 n 개 [{rcept_no, report_nm, rcept_dt}] (새 것부터, 5년 안). 별도 감사보고서가 있으면 연결은 뺀다 (해마다 같은 기준으로)."""
    d = _call("list.json", "공시 목록", key, corp_code=code, bgn_de=f"{today.year - 5}{today:%m%d}", end_de=f"{today:%Y%m%d}",
              pblntf_ty="F", last_reprt_at="Y", page_count=100)
    if d is None:
        return []
    rows = d.get("list")
    if not isinstance(rows, list):
        raise K.ShapeError("DART 공시 목록 응답에 list 없음")
    rows = [r for r in rows if isinstance(r, dict) and "감사보고서" in r.get("report_nm", "") and "rcept_no" in r]
    rows = [r for r in rows if "연결" not in r["report_nm"]] or rows
    return sorted(rows, key=lambda r: r.get("rcept_dt", ""), reverse=True)[:n]


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def _won(cell: str) -> Optional[int]:
    """'1,234' · '(1,234)' · '△1,234' · '-1,234' → 정수. 빈칸·'-' 는 None."""
    t = cell.replace(",", "").replace(" ", "")
    neg = t[:1] in ("(", "△", "-") and len(t) > 1
    t = t.strip("()△-")
    return (-int(t) if neg else int(t)) if t.isdigit() else None


def statement(xml: str) -> Dict[int, Dict[str, Any]]:
    """감사보고서 원문 → {연도: {year, revenue, operating_profit} 억 원} (당기·전기). 손익계산서 표에서 표준계정코드로,
    코드가 없으면 계정 이름으로 찾는다. 못 찾으면 ShapeError."""
    for g in re.finditer(r"<TABLE-GROUP\b[^>]*>(.*?)</TABLE-GROUP>", xml, re.S):
        body = g.group(1)
        found: Dict[str, List[int]] = {}
        for tr in re.findall(r"<TR\b[^>]*>(.*?)</TR>", body, re.S):
            cells = [_text(c) for c in re.findall(r"<T[DHE]\b[^>]*>(.*?)</T[DHE]>", tr, re.S)]
            if not cells:
                continue
            m = re.search(r'ACODE="(\d+)"', tr)
            name = re.sub(r"^[\sⅠ-ⅩIVX]+\.?\s*|\(주석[^)]*\)|\s", "", cells[0])
            field = ACODES.get(m.group(1) if m else "") or ("revenue" if name in REVENUE else "operating_profit"
                                                            if name in PROFIT or name == "영업손실" else "")
            nums = [v for v in map(_won, cells[1:]) if v is not None]
            if field and field not in found and nums:
                found[field] = [-v for v in nums] if name == "영업손실" else nums
        if len(found) < 2:
            continue
        text = _text(body)
        years = [int(y) for y in re.findall(r"(\d{4})년\s*\d{1,2}월\s*\d{1,2}일\s*까지", text)][:2]
        unit = re.search(r"단위\s*[:：]?\s*(백만원|천원|원)", text)
        if not years or not unit:
            raise K.ShapeError("감사보고서 손익계산서에 회계연도나 단위 표기 없음")
        out: Dict[int, Dict[str, Any]] = {}
        for i, y in enumerate(years):
            row: Dict[str, Any] = {"year": y}
            for field, nums in found.items():
                if i < len(nums):
                    row[field] = eok(nums[i] * UNITS[unit.group(1)])
            out[y] = row
        return out
    raise K.ShapeError("감사보고서에서 손익계산서(영업수익·영업이익)를 찾지 못함")


def audit_finance(key: str, rcept_no: str) -> Dict[int, Dict[str, Any]]:
    """감사보고서 원문(zip 안 XML)을 받아 statement 로 읽는다."""
    raw = _download(f"{BASE}/document.xml?" + urllib.parse.urlencode(dict(crtfc_key=key, rcept_no=rcept_no)))
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            docs = [z.read(n).decode("utf-8", "replace") for n in z.namelist()]
    except zipfile.BadZipFile:
        _status_fail(raw, "감사보고서 원문")
    return statement(max(docs, key=lambda d: d.count("TABLE-GROUP")))


def to_prep(key: str, info: Dict[str, Any], source: int, today: date) -> Tuple[List[Dict[str, Any]], Dict[str, Any], List[str]]:
    """(sources 줄들, company 조각 {leaders, finance}, 알릴 말). source 부터 번호를 차례로 쓴다."""
    read = today.isoformat()
    name = info["corp_name"]
    sources = [dict(id=source, title=f"DART 기업개황 ({name})", url=SEARCH + urllib.parse.quote(core_name(name)), read=read)]
    part: Dict[str, Any] = {}
    if info.get("ceo_nm"):
        part["leaders"] = [dict(name=info["ceo_nm"], role="대표자", source=source)]
    notes: List[str] = []
    rcept, fin = finance(key, info["corp_code"], today.year)
    if fin:
        sid = source + 1
        sources.append(dict(id=sid, title=f"DART 사업보고서 주요계정 ({name})", url=VIEW + rcept, read=read))
        part["finance"] = [dict(f, source=sid) for f in fin]
    else:
        # 사업보고서가 없으면 최근 감사보고서 두 개의 손익계산서 (당기·전기라 세 해가 나온다, 겹치는 해는 새 보고서 것)
        years: Dict[int, Dict[str, Any]] = {}
        reports = audits(key, info["corp_code"], today)
        for sid, a in enumerate(reports, source + 1):
            title = a["report_nm"].strip()
            sources.append(dict(id=sid, title=f"DART {title} ({name})", url=VIEW + a["rcept_no"], read=read))
            try:
                for y, row in audit_finance(key, a["rcept_no"]).items():
                    years.setdefault(y, dict(row, source=sid))
            except K.ShapeError as e:
                notes.append(f"{title}: {e}. 매출·영업이익은 출처 {sid} 의 손익계산서에서 옮겨 적으세요 (억 원)")
        if years:
            part["finance"] = [years[y] for y in sorted(years)]
        if not reports:
            notes.append("DART 에 사업보고서·감사보고서가 없음 (매출·영업이익은 다른 출처에서)")
    return sources, part, notes
