# -*- coding: utf-8 -*-
"""회사 숫자: 원티드 회사 정보 표(키 없음)를 읽어 준비 자료(prep.yaml)에 붙일 YAML 로 낸다 (modes/prep.md 2단계).

  jobhunt company <원티드 공고 주소 | 원티드 회사 주소 | 회사 이름> [--source N] [--dart 고유번호] [--nps-addr 주소 일부]

원티드 회사 쪽(wanted.co.kr/company/{id})의 '기업 정보' 표는 로그인 없이 서버가 그려 준다 (2026-10-27 실측).
평균연봉은 국민연금 납부액으로 추정한 값이라 소득 상한 때문에 고연봉자를 낮게 잡는다. 이 주의를 note 로 함께 낸다.
사용자 키가 있으면(jobhunt keys) 국민연금 가입 사업장 내역(nps.py)과 OpenDART(dart.py)로 더 정확한 숫자를 붙인다.
원티드에 없는 회사도 키가 있으면 이름으로 찾는다. 키 쪽 실패는 원티드 결과를 막지 않고 알림으로만 낸다.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dart  # noqa: E402
import jobkit as K  # noqa: E402
import keys  # noqa: E402
import nps  # noqa: E402

BASE = "https://www.wanted.co.kr"
SALARY_NOTE = "국민연금 납부액 기반 추정 (기준소득월액 상한 때문에 고연봉자는 낮게 잡히고 임원도 포함)"
# 원티드 표의 칸 → 준비 자료 numbers 의 label. 회사마다 있는 칸이 다르다
LABELS = [("평균연봉", "평균연봉 (국민연금 기반 추정)"), ("국민연금 가입 사원수", "국민연금 가입자"),
          ("고용보험 가입 사원수", "고용보험 가입자"), ("퇴사/입사 (1년)", "최근 1년 퇴사 · 입사"),
          ("매출액", "매출액 (원티드 표시, 연도 표기 없음)"), ("연혁", "업력")]
# 키로 받은 숫자가 있으면 빼는 원티드 줄: 국민연금 가입 사업장 내역이 대신하는 것, DART 연도별 매출이 대신하는 것
BY_NPS = {"평균연봉 (국민연금 기반 추정)", "국민연금 가입자", "최근 1년 퇴사 · 입사"}
BY_DART = {"매출액 (원티드 표시, 연도 표기 없음)"}


class Ambiguous(Exception):
    """이름으로 찾은 회사가 여럿."""


def _get(url: str, what: str, accept: str = "application/json") -> str:
    """본문. 200 이 아니면 RuntimeError: 요청 제한(403·429)은 응답 형식 변경이 아니라 잠시 뒤 다시 할 일이다."""
    status, body = K.http_get(url, accept=accept)
    if status != 200:
        raise RuntimeError(f"원티드 {what} HTTP {status}" + (" (요청 제한: 잠시 뒤 다시)" if status in (403, 429) else ""))
    return body


def _json(url: str, what: str) -> Any:
    try:
        return json.loads(_get(url, what))
    except json.JSONDecodeError:
        raise K.ShapeError(f"원티드 {what} 응답이 JSON 이 아님") from None


def company_id(query: str) -> int:
    """원티드 회사 번호. 회사 주소면 그 번호, 공고 주소면 공고의 회사, 아니면 이름으로 찾는다 (같은 이름이 하나일 때만)."""
    m = re.search(r"wanted\.co\.kr/company/(\d+)", query)
    if m:
        return int(m.group(1))
    if "wanted.co.kr/wd/" in query:
        jid = K.url_part(r"/wd/(\d+)", query, 1)
        d = _json(f"{BASE}/api/v4/jobs/{jid}", "공고 상세")
        job = d.get("job") if isinstance(d, dict) else None
        if not isinstance(job, dict) or not isinstance((job.get("company") or {}).get("id"), int):
            raise K.ShapeError("원티드 공고 상세에 job.company.id 없음")
        return job["company"]["id"]
    if re.match(r"https?://", query):
        raise ValueError(f"원티드 주소가 아님: {query} (회사 이름으로 찾거나 원티드 회사 주소를 주세요)")
    d = _json(f"{BASE}/api/chaos/search/v1/autocomplete?query={urllib.parse.quote(query)}", "회사 검색")
    if not isinstance(d, dict) or not isinstance(d.get("companies"), list):
        raise K.ShapeError("원티드 회사 검색에 companies 없음")
    found = [(c["id"], c.get("name", "")) for c in d["companies"] if isinstance(c, dict) and "id" in c]
    if not found:
        raise LookupError(f"원티드에서 '{query}' 회사를 찾지 못함")
    # '숨고' → '브레이브모바일(숨고,Soomgo)' 처럼 괄호 안의 서비스 이름으로도 맞춘다
    exact = [f for f in found if query.replace(" ", "") in re.split(r"[(),]", f[1].replace(" ", ""))]
    if len(exact) == 1 or len(found) == 1:
        return (exact or found)[0][0]
    raise Ambiguous("\n".join(f"  {BASE}/company/{i}  {n}" for i, n in found))


def info_table(page: str) -> Dict[str, str]:
    """회사 쪽 HTML → '기업 정보' 표 {칸: 값}. 값이 '-' 인 칸은 뺀다."""
    pairs = re.findall(r"<dt[^>]*>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>", page, re.S)
    table = {K.html_text(k): K.html_text(v) for k, v in pairs}
    if not any(k in table for k, _ in LABELS):
        raise K.ShapeError("원티드 회사 쪽에 '기업 정보' 표 없음")
    return {k: v for k, v in table.items() if v and v != "-"}


def fetch(cid: int) -> Tuple[str, Dict[str, str]]:
    """(회사 이름, 기업 정보 표)."""
    page = _get(f"{BASE}/company/{cid}", "회사 쪽", accept="text/html")
    title = re.search(r"<title>(.*?)(?: 기업정보| \|)", page, re.S)
    return (K.html_text(title.group(1)) if title else ""), info_table(page)


def to_prep(cid: int, name: str, table: Dict[str, str], source: int, today: str) -> Dict[str, Any]:
    """준비 자료에 붙일 조각: sources 한 줄, company.numbers, company.leaders. 표에 없는 칸은 '확인 못 함'."""
    numbers: List[Dict[str, Any]] = []
    for key, label in LABELS:
        row: Dict[str, Any] = dict(label=label, value=table.get(key, "확인 못 함"), as_of=today, source=source)
        if key == "평균연봉" and key in table:
            row["note"] = SALARY_NOTE
        numbers.append(row)
    company: Dict[str, Any] = dict(numbers=numbers)
    if table.get("대표자명"):
        company["leaders"] = [dict(name=table["대표자명"], role="대표자", source=source)]
    src = dict(id=source, title=f"원티드 회사 정보 ({name or cid})", url=f"{BASE}/company/{cid}", read=today)
    return dict(sources=[src], company=company)


def dump(d: Dict[str, Any]) -> str:
    """준비 자료와 같은 모양: 목록의 항목은 한 줄 { … } 로."""
    import yaml

    def one(x: Dict[str, Any]) -> str:
        return yaml.safe_dump(x, allow_unicode=True, default_flow_style=True, sort_keys=False, width=1000).strip()
    out = ["sources:"] + [f"  - {one(s)}" for s in d["sources"]] + ["company:"]
    for key, rows in d["company"].items():
        if rows:
            out += [f"  {key}:"] + [f"    - {one(r)}" for r in rows]
    return "\n".join(out) + "\n"


def base_name(name: str) -> str:
    """'브레이브모바일(숨고,Soomgo)' → '브레이브모바일': 괄호 안 서비스 이름을 뺀 법인 이름."""
    return re.sub(r"\(주\)|㈜", "", name).split("(")[0].strip() or name


def add_keyed(d: Dict[str, Any], first: int, name: str, ceo: str, today: date, dart_code: str = "",
              nps_addr: str = "") -> List[str]:
    """키가 있으면 DART·국민연금 숫자를 d 에 더한다 (출처 번호는 first 부터 비어 있는 다음). 돌려주는 것: 사용자에게 알릴 말."""
    notes: List[str] = []
    co, nxt = d["company"], max([s["id"] for s in d["sources"]], default=first - 1) + 1
    dkey, nkey = keys.get("dart"), keys.get("data_go_kr")
    info: Dict[str, Any] = {}
    if dkey:
        try:
            info = dart.company(dkey, dart_code) if dart_code else dart.find(dkey, base_name(name), ceo)
            srcs, part, more = dart.to_prep(dkey, info, nxt, today)
            d["sources"] += srcs
            nxt += len(srcs)
            notes += more
            if part.get("leaders"):
                co["leaders"] = part["leaders"]
            if part.get("finance"):
                co["finance"] = part["finance"]
                co["numbers"] = [n for n in co["numbers"] if n["label"] not in BY_DART]
        except dart.Ambiguous as e:
            notes.append(f"DART 에 이름이 같은 회사가 여럿입니다. 맞는 회사의 고유번호로 다시 (--dart 고유번호):\n{e}")
        except (LookupError, RuntimeError) as e:
            notes.append(str(e))
        except K.ShapeError as e:
            notes.append(f"응답 형식 변경: {e}")
        except OSError as e:                     # 연결 끊김·시간 초과 (주소에 키가 있어 메시지는 싣지 않는다)
            notes.append(f"DART 연결 실패 ({type(e).__name__}): 잠시 뒤 다시")
    if nkey:
        try:
            src, rows = nps.numbers(nkey, info.get("corp_name") or base_name(name), nxt, today.isoformat(),
                                    bizno=info.get("bizr_no", ""), addr=nps_addr)
            d["sources"].append(src)
            co["numbers"] = rows + [n for n in co["numbers"] if n["label"] not in BY_NPS]
        except nps.Ambiguous as e:
            notes.append(f"국민연금 가입 사업장이 여럿입니다. 주소 일부로 좁혀 다시 (--nps-addr '주소 일부'):\n{e}")
        except (LookupError, RuntimeError) as e:
            notes.append(str(e))
        except K.ShapeError as e:
            notes.append(f"응답 형식 변경: {e}")
        except OSError as e:
            notes.append(f"공공데이터포털 연결 실패 ({type(e).__name__}): 잠시 뒤 다시")
    if not (dkey and nkey):
        notes.append(f"키가 없어 건너뜀: {', '.join(keys.KEYS[n]['title'].split(' (')[0] for n in keys.missing())}"
                     " (발급·등록 방법: jobhunt keys)")
    return notes


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="원티드 회사 정보 → 준비 자료(prep.yaml)에 붙일 YAML")
    ap.add_argument("query", help="원티드 공고 주소, 원티드 회사 주소, 또는 회사 이름")
    ap.add_argument("--source", type=int, default=1, help="준비 자료 sources 에서 쓸 첫 번호 (기본 1, 비어 있는 다음 번호를 주세요)")
    ap.add_argument("--dart", default="", metavar="고유번호", help="DART 에 이름이 같은 회사가 여럿일 때 고를 고유번호 (8자리)")
    ap.add_argument("--nps-addr", default="", metavar="주소 일부", help="국민연금 가입 사업장이 여럿일 때 주소 일부로 좁힘")
    a = ap.parse_args(argv)
    has_key = any(keys.get(n) for n in keys.KEYS)
    cid: Optional[int] = None
    name = a.query
    table: Dict[str, str] = {}
    try:
        cid = company_id(a.query)
        name, table = fetch(cid)
    except Ambiguous as e:
        print(f"'{a.query}' 로 찾은 원티드 회사가 여럿입니다. 맞는 회사 주소로 다시 실행하세요:\n{e}", file=sys.stderr)
        return 2
    except LookupError as e:
        if not has_key:                          # 키가 있으면 원티드에 없는 회사도 이름으로 DART·국민연금에서 찾는다
            print(e, file=sys.stderr)
            return 1
        print(f"{e}. 키로 이름을 찾아봅니다.", file=sys.stderr)
    except (ValueError, RuntimeError) as e:
        print(e, file=sys.stderr)
        return 1
    except K.ShapeError as e:
        print(f"응답 형식 변경: {e}", file=sys.stderr)
        return 1
    today = date.today()
    d = to_prep(cid, name, table, a.source, today.isoformat()) if cid else dict(sources=[], company=dict(numbers=[]))
    notes = add_keyed(d, a.source, name, table.get("대표자명", ""), today, a.dart, a.nps_addr)
    if cid is None and not d["sources"]:
        print("\n".join(notes), file=sys.stderr)
        return 1
    print(f"# {name or cid} — 회사 숫자 ({today} 조회). 준비 자료의 sources·company 에 합치세요.")
    print(dump(d), end="")
    for n in notes:
        print(f"알림: {n}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
