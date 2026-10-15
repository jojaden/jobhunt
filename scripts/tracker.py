# -*- coding: utf-8 -*-
"""지원 현황표 관리 (modes/track.md). 표를 손으로 고치지 않고 이 스크립트로 바꾼다.

  python3 scripts/tracker.py add --company 회사 --role 포지션 --score 4.2/5 --eval data/job_postings/x.eval.md --memo "서울 강남 · 원티드"
  python3 scripts/tracker.py set <번호|회사> <상태> [--note "메모"]
  python3 scripts/tracker.py report [--alive] [--since YYYY-MM-DD]
        평가한 공고 + 선별 통과 공고를 표 하나로 (지원 여부 컬럼 포함, standing.md 보고 형식)

상태값: 평가함 지원함 서류합격 면접 최종합격 입사 불합격 포기 제외
지원함으로 바꾸면 pipeline.md 의 같은 공고를 "지원 완료 — 재지원 쿨다운"으로 옮긴다.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import jobkit as K  # noqa: E402

APPLIED = ("지원함", "서류합격", "면접", "최종합격", "입사", "불합격")
COOL_HEADER = "## 지원 완료 — 재지원 쿨다운"


def _write_rows(rows):
    text = K.read_text(K.P["tracker"])
    if not text.strip():
        text = f"# 지원 현황\n\n{K.TRACKER_HEAD}\n|---|------|------|--------|------|------|-----|------|------|\n"
    lines = [l for l in text.rstrip("\n").split("\n") if not re.match(r"\|\s*\d+\s*\|", l)]
    K.write_text(K.P["tracker"], "\n".join(lines + [K.tracker_line(r) for r in sorted(rows, key=lambda r: r["num"])]) + "\n")


def find(rows, key):
    if key.isdigit():
        hit = [r for r in rows if r["num"] == int(key)]
    else:
        n = K.norm_company(key)
        hit = [r for r in rows if n and n in K.norm_company(r["company"])]
    if len(hit) != 1:
        sys.exit(f"'{key}'에 맞는 행이 {len(hit)}개입니다. 번호로 지정하세요: "
                 + ", ".join(f"#{r['num']} {r['company']} {r['role']}" for r in hit))
    return hit[0]


def cmd_add(a):
    rows = K.read_tracker()
    ev = os.path.relpath(a.eval, os.path.dirname(K.P["tracker"])) if a.eval else ""
    r = dict(num=max([x["num"] for x in rows] or [0]) + 1, date=K.TODAY, company=a.company, role=a.role,
             score=a.score or "—", state=a.state, pdf="❌", eval=f"[평가]({ev})" if ev else "—", memo=a.memo or "")
    if r["state"] not in K.STATES:
        sys.exit(f"상태값이 아닙니다: {r['state']} (가능: {' '.join(K.STATES)})")
    _write_rows(rows + [r])
    print(f"#{r['num']} 추가: {r['company']} — {r['role']} ({r['state']})")


def cmd_set(a):
    if a.state not in K.STATES:
        sys.exit(f"상태값이 아닙니다: {a.state} (가능: {' '.join(K.STATES)})")
    rows = K.read_tracker()
    r = find(rows, a.key)
    old, r["state"] = r["state"], a.state
    r["memo"] += f"; {a.note or a.state} ({K.TODAY})"
    if a.pdf:
        r["pdf"] = "✅"
    _write_rows(rows)
    print(f"#{r['num']} {r['company']}: {old} → {a.state}")
    if a.state == "지원함":
        md = K.read_text(K.P["pipeline"])
        moved = md
        for u in _urls_for(r):
            moved = K.move_line(moved, u, COOL_HEADER, f"지원 {K.TODAY} — 재지원 쿨다운", before="## 마감 확인")
        if moved != md:
            K.write_text(K.P["pipeline"], moved)
            print("  pipeline.md: 재지원 쿨다운 섹션으로 옮김")


def _urls_for(r):
    from alive import eval_url
    urls = set(K.URL_RE.findall(r["memo"]))
    u = eval_url(r["eval"])
    if u:
        urls.add(u)
    return urls


# ── 보고 ──────────────────────────────────────────────
def verdict(score: str) -> str:
    m = re.match(r"([\d.]+)", score or "")
    if not m:
        return "—"
    s = float(m.group(1))
    return "지원 권장" if s >= 4.0 else "지원 고려" if s >= 3.5 else "보류" if s >= 3.0 else "제외"


def _label(tri, line: str) -> str:
    """점수가 있으면 verdict() 이름으로 (references/scoring.md), 본문을 못 받은 줄은 확인 필요."""
    if not tri:
        return "선별 전"
    if "본문 확인 필요" in line:
        return "확인 필요"
    return verdict(tri.group(2)) if tri.group(2) else f"1차 {tri.group(1)}"


def _loc(text: str) -> str:
    m = re.search(r"((?:서울|경기|인천|부산|대구|광주|대전|울산|세종|강원|충청|충북|충남|전라|전북|전남|경상|경북|경남|제주|판교|성남|분당)[^·;,|]{0,12}|재택|원격)", text or "")
    return m.group(1).strip() if m else "?"


def cmd_report(a):
    first_seen = {h["url"]: h["first_seen"] for h in K.read_history()}
    alive = {}
    if a.alive:
        import alive as AL
        res = AL.run(AL.tracker_targets() + AL.pipeline_targets())
        alive = {r["url"]: r["alive"] for r in res}
    mark = {True: "열림", False: "마감", None: "?"}

    rows, done = [], set()
    for r in K.read_tracker():
        if r["state"] in ("제외", "포기"):
            continue
        urls = _urls_for(r)
        url = next(iter(urls), "")
        done |= urls
        applied = f"지원함 ({r['state']})" if r["state"] in APPLIED else "미지원"
        new = "✓" if a.since and first_seen.get(url, "0") >= a.since else ""
        rows.append((r["company"], r["role"], _loc(r["memo"]), r["score"], verdict(r["score"]) if r["state"] == "평가함" else r["state"],
                     applied, new, mark.get(alive.get(url), "?") if a.alive else "", re.sub(r"\s+", " ", r["memo"])[:70]))

    for p in K.read_pipeline():
        if p.section != "## 대기" or p.mark != " " or not p.url or p.url in done:
            continue
        tri = re.search(r"(PASS|MARGINAL|FAIL)\s*([\d.]+/5)?", p.line)
        new = "✓" if a.since and first_seen.get(p.url, "0") >= a.since else ""
        rows.append((p.company, p.title, p.cells[3] if len(p.cells) > 3 else "?",
                     (tri.group(2) or "—") if tri else "—", _label(tri, p.line), "미지원", new,
                     mark.get(alive.get(p.url), "?") if a.alive else "", p.cell(5)[:70]))

    order = {"지원 권장": 0, "지원 고려": 1, "1차 PASS": 2, "보류": 3, "1차 MARGINAL": 4, "확인 필요": 5}
    score = lambda x: -float(re.match(r"[\d.]+", x[3]).group(0)) if re.match(r"[\d.]+", x[3]) else 0
    rows.sort(key=lambda x: (x[5] != "미지원", order.get(x[4], 5), score(x)))
    pending = sum(1 for l in K.read_text(K.P["pipeline"]).split("## 새로 수집 (선별 전)")[-1].split("\n## ")[0].split("\n")
                  if l.lstrip().startswith("- [ ]")) if "## 새로 수집 (선별 전)" in K.read_text(K.P["pipeline"]) else 0
    print(f"## 공고 현황 ({K.TODAY}) — 평가·선별 {len(rows)}건, 선별 전 {pending}건\n")
    print("| 회사 | 포지션 | 근무지 | 점수 | 판정 | 지원 여부 | 새로 찾음 | 마감 | 한 줄 근거 |")
    print("|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        print("| " + " | ".join(x.replace("|", "/") for x in r) + " |")


def main(argv=None):
    ap = argparse.ArgumentParser(description="지원 현황표")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("add")
    p.add_argument("--company", required=True)
    p.add_argument("--role", required=True)
    p.add_argument("--score")
    p.add_argument("--eval")
    p.add_argument("--memo")
    p.add_argument("--state", default="평가함")
    p = sub.add_parser("set")
    p.add_argument("key")
    p.add_argument("state")
    p.add_argument("--note")
    p.add_argument("--pdf", action="store_true", help="PDF 준비됨 표시")
    p = sub.add_parser("report")
    p.add_argument("--alive", action="store_true", help="마감 여부도 확인 (느림)")
    p.add_argument("--since", help="이 날짜 이후 처음 본 공고에 '새로 찾음' 표시")
    a = ap.parse_args(argv)
    {"add": cmd_add, "set": cmd_set, "report": cmd_report}[a.cmd](a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
