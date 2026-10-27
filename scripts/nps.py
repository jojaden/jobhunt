# -*- coding: utf-8 -*-
"""국민연금 가입 사업장 내역 (공공데이터포털 오픈 API, 사용자 본인 키): 가입자 수, 평균연봉 추정, 최근 1년 입사·퇴사.

명세: 국민연금공단_오픈API활용가이드_국민연금 가입 사업장 내역_v2.0 (https://www.data.go.kr/data/3046071/openapi.do, 2026-10-27 확인).
3인 이상 법인 사업장만 공개된다. 오류 메시지에 키가 든 주소를 넣지 않는다.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jobkit as K  # noqa: E402

BASE = "https://apis.data.go.kr/B552015/NpsBplcInfoInqireServiceV2"
PAGE = "https://www.data.go.kr/data/3046071/openapi.do"
# 기준소득월액 상한 (적용 시작 년월, 원): 명세 설명 + 국민연금공단 2026년 상·하한액 조정 안내
CAPS = [("202107", 5_240_000), ("202207", 5_530_000), ("202307", 5_900_000), ("202407", 6_170_000),
        ("202507", 6_370_000), ("202607", 6_590_000)]
KEY_HELP = "공공데이터포털 키가 거절됨: '국민연금 가입 사업장 내역' 활용신청을 했는지, 발급 직후면 1~2시간 뒤 다시 (jobhunt keys)"


class Ambiguous(Exception):
    """이름이 같은 사업장이 여럿."""


def norm(name: str) -> str:
    """회사 이름 비교용: 법인 표기와 공백을 뺀다."""
    return re.sub(r"\(주\)|㈜|주식회사|\(유\)|유한회사|\s", "", name or "").lower()


def core_name(name: str) -> str:
    """'(주)가나다' · '주식회사 가나다' → '가나다'."""
    return re.sub(r"\(주\)|㈜|주식회사|\(유\)|유한회사", "", name or "").strip()


def rate(ym: str) -> float:
    """그 달의 연금보험료율: 2025년까지 9%, 2026년부터 해마다 0.5%p 올라 2033년 13% (2025년 국민연금법 개정)."""
    y = int(ym[:4])
    return 0.09 if y <= 2025 else round(min(0.13, 0.09 + 0.005 * (y - 2025)), 3)


def cap(ym: str) -> int:
    return [c for start, c in CAPS if start <= ym][-1] if ym >= CAPS[0][0] else CAPS[0][1]


def _fail(code: str, what: str) -> None:
    """결과 코드 → 알맞은 오류. 03(자료 없음)은 오류가 아니다."""
    if code in ("20", "30", "31"):
        raise RuntimeError(KEY_HELP)
    if code in ("22", "23"):
        raise RuntimeError("공공데이터포털 요청 제한 (하루 1만 건 또는 초당 호출 수): 잠시 뒤 다시")
    raise RuntimeError(f"공공데이터포털 {what} 오류 코드 {code}")


def _call(op: str, what: str, key: str, **params: Any) -> List[Dict[str, Any]]:
    """한 오퍼레이션의 items.item 목록 (한 건이면 dict 로 오기도 해 목록으로 맞춘다)."""
    q = urllib.parse.urlencode(dict({k: v for k, v in params.items() if v not in (None, "")},
                                    serviceKey=key, dataType="json", pageNo=1))
    status, body = K.http_get(f"{BASE}/{op}?{q}")
    if status in (401, 403):
        raise RuntimeError(KEY_HELP)
    if status == 429:
        _fail("22", what)
    if status != 200:
        raise RuntimeError(f"공공데이터포털 {what} HTTP {status}")
    try:
        d = json.loads(body)
    except ValueError:
        # 게이트웨이 오류는 JSON 을 달라고 해도 XML 로 온다
        m = re.search(r"<(?:returnReasonCode|resultCode)>(\d+)<", body)
        if m and m.group(1) not in ("00", "03"):
            _fail(m.group(1), what)
        if m:
            return []
        raise K.ShapeError(f"공공데이터포털 {what} 응답이 JSON 이 아님") from None
    r = d.get("response", d) if isinstance(d, dict) else None
    if not isinstance(r, dict) or not isinstance(r.get("header"), dict):
        raise K.ShapeError(f"공공데이터포털 {what} 응답에 header 없음")
    code = str(r["header"].get("resultCode", ""))
    if code == "03":
        return []
    if code != "00":
        _fail(code, what)
    items = (r.get("body") or {}).get("items")
    if items in (None, ""):                     # 결과가 없으면 빈 문자열로 온다
        return []
    if not isinstance(items, dict):
        raise K.ShapeError(f"공공데이터포털 {what} 응답에 items 없음")
    item = items.get("item") or []
    return [item] if isinstance(item, dict) else [x for x in item if isinstance(x, dict)]


def ping(key: str) -> None:
    """키가 쓰이는지 한 번 불러 본다 (실패하면 RuntimeError)."""
    _call("getBassInfoSearchV2", "사업장 조회", key, wkplNm="국민연금공단", numOfRows=1)


def _int(v: Any) -> Optional[int]:
    try:
        return int(str(v).replace(",", ""))
    except ValueError:
        return None


def workplace(key: str, name: str, bizno: str = "", addr: str = "") -> Tuple[str, str, List[Dict[str, Any]]]:
    """(사업장명, 최근 주소, 달마다 한 줄 [오래된 것 → 최근]). 이름이 정확히 같은 사업장을 고르고, bizno(사업자등록번호)·addr(주소 일부)로 좁힌다.
    사업장은 이름과 사업자등록번호 앞자리로 묶는다 (이사하면 같은 사업장도 달마다 주소가 다르다)."""
    rows: List[Dict[str, Any]] = []
    # 이름은 부분 일치로 찾는다('가나다' → '(주)가나다'). 법인 표기를 뗀 이름 먼저, 없으면 표기를 붙여 본다
    core = core_name(name)
    for q in dict.fromkeys([core, name, f"주식회사 {core}", f"(주){core}"]):
        rows = _call("getBassInfoSearchV2", "사업장 조회", key, wkplNm=q, bzowrRgstNo=re.sub(r"\D", "", bizno)[:6], numOfRows=100)
        if rows:
            break
    groups: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for r in rows:
        if "wkplNm" not in r or "dataCrtYm" not in r:
            raise K.ShapeError("국민연금 사업장 조회 응답에 wkplNm·dataCrtYm 없음")
        groups.setdefault((r["wkplNm"], str(r.get("bzowrRgstNo", ""))), []).append(r)
    latest = {g: max(rs, key=lambda r: r["dataCrtYm"]) for g, rs in groups.items()}
    pool = [g for g in groups if norm(g[0]) == norm(name)] or list(groups)
    if addr:
        pool = [g for g in pool if addr.replace(" ", "") in latest[g].get("wkplRoadNmDtlAddr", "").replace(" ", "")]
    # 탈퇴한 사업장은 뺀다 (가장 최근 달 기준)
    pool = [g for g in pool if str(latest[g].get("wkplJnngStcd", "1")) == "1"]
    if not pool:
        raise LookupError(f"국민연금 가입 사업장에서 '{name}' 을 찾지 못함 (3인 이상 법인만 공개)")
    if len(pool) > 1:
        raise Ambiguous("\n".join(f"  {n} · {latest[(n, b)].get('wkplRoadNmDtlAddr', '')} · 사업자 {b}" for n, b in pool))
    g = pool[0]
    return g[0], latest[g].get("wkplRoadNmDtlAddr", ""), sorted(groups[g], key=lambda r: r["dataCrtYm"])


def detail(key: str, seq: Any) -> Tuple[int, int]:
    """(가입자 수, 당월 고지 금액)."""
    rows = _call("getDetailInfoSearchV2", "상세 조회", key, seq=seq)
    cnt, amt = (_int(rows[0].get("jnngpCnt")), _int(rows[0].get("crrmmNtcAmt"))) if rows else (None, None)
    if cnt is None or amt is None:
        raise K.ShapeError("국민연금 상세 조회 응답에 jnngpCnt·crrmmNtcAmt 없음")
    return cnt, amt


def flow(key: str, seq: Any, ym: str) -> Optional[Tuple[int, int]]:
    """그 달 (취득자 수, 상실자 수). 자료가 없으면 None."""
    rows = _call("getPdAcctoSttusInfoSearchV2", "기간별 현황", key, seq=seq, dataCrtYm=ym)
    if not rows:
        return None
    new, lost = _int(rows[0].get("nwAcqzrCnt")), _int(rows[0].get("lssJnngpCnt"))
    if new is None or lost is None:
        raise K.ShapeError("국민연금 기간별 현황 응답에 nwAcqzrCnt·lssJnngpCnt 없음")
    return new, lost


def _ym(ym: str) -> str:
    return f"{ym[:4]}-{ym[4:6]}"


def last_months(ym: str, n: int = 12) -> List[str]:
    """ym 까지 n 달 (오래된 것 → 최근), 'YYYYMM'."""
    y, m = int(ym[:4]), int(ym[4:6])
    out = []
    for _ in range(n):
        out.append(f"{y:04d}{m:02d}")
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    return out[::-1]


def numbers(key: str, name: str, source: int, today: str, bizno: str = "",
            addr: str = "") -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """(sources 한 줄, company.numbers 줄들): 가입자 수 (1년 전과 비교), 평균연봉 추정, 최근 1년 입사·퇴사."""
    wname, waddr, months = workplace(key, name, bizno, addr)
    last = months[-1]
    ym = last["dataCrtYm"]
    cnt, amt = detail(key, last["seq"])
    out: List[Dict[str, Any]] = []
    head = f"{cnt:,}명"
    first = months[0]
    if first["seq"] != last["seq"]:              # 달마다 따로 있는 줄이면 1년 안쪽 첫 달과 비교한다
        head += f" ({_ym(first['dataCrtYm'])} {detail(key, first['seq'])[0]:,}명)"
    out.append(dict(label="국민연금 가입자", value=head, as_of=_ym(ym), source=source))
    if cnt:
        r = rate(ym)
        yearly = amt / cnt / r * 12
        out.append(dict(label="평균연봉 (국민연금 고지액 기반 추정)", value=f"약 {round(yearly / 10000):,}만원", as_of=_ym(ym), source=source,
                        note=f"고지액 ÷ 가입자 ÷ 보험료율 {r * 100:g}% × 12. 기준소득월액 상한(월 {cap(ym):,}원)을 넘는 소득은 상한으로 잡혀 "
                             "고연봉자가 많을수록 낮게 나오고, 대표·임원도 들어 있다"))
    # 달마다 줄(seq)이 따로 오면 그 줄로, 한 줄만 오면 같은 seq 에 달을 바꿔 묻는다
    seq_of = {m["dataCrtYm"]: m["seq"] for m in months}
    got = [f for f in (flow(key, seq_of.get(m, last["seq"]), m) for m in last_months(ym)) if f]
    if got:
        out.append(dict(label="최근 1년 입사 · 퇴사", value=f"입사 {sum(f[0] for f in got):,}명 · 퇴사 {sum(f[1] for f in got):,}명",
                        as_of=_ym(ym), source=source,
                        note=f"{len(got)}개월 합. 납부 재개·납부 예외도 들어가 실제 입사·퇴사와 다를 수 있다"))
    src = dict(id=source, title=f"국민연금 가입 사업장 내역 ({wname}, {waddr})" if waddr else f"국민연금 가입 사업장 내역 ({wname})",
               url=PAGE, read=today)
    return src, out
