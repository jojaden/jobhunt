# -*- coding: utf-8 -*-
"""판정 정답 세트 비교 (LLM 호출 없음). 분류 규칙을 바꾼 뒤 에이전트의 판정이 정답에서 얼마나 벗어났는지 잰다.

  python3 scripts/eval_golden.py <판정 폴더> [--min-lines 0.85] [--min-verdicts 0.8] [--golden examples/golden]

정답 세트: examples/golden/ — 가상 지원자(candidate.md), 개인 선호(scoring.yaml), 공고 본문(postings/), 정답(answers/).
판정 폴더: 에이전트가 candidate.md 만 근거로 postings/ 의 공고를 분류해 같은 파일 이름(.yaml)으로 저장한 곳.
절차: references/scoring.md "Golden set".

비교 (줄은 문장을 정규화해 짝짓는다)
  조건   gates 중 fail 인 것
  줄     work.fit · required.met · gap · alt · preferred.met · key, 빠진 줄 · 더한 줄 (태도 줄을 뺐는지 등)
  방향   direction.primary · domain_new 유무
  결론   score.py 로 계산한 지원 권장 / 고려 / 보류 / 제외
줄 일치율이나 결론 일치율이 기준보다 낮으면 종료 코드 1.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from typing import List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import jobkit as K  # noqa: E402
import score as S  # noqa: E402

FIELDS = {"work": ("fit",), "required": ("met", "gap", "alt"), "preferred": ("met", "key")}


def _norm(line: str | None) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", str(line).lower())


def _value(x: S.Line, f: str):
    if f == "met":
        return S._met(x)
    if f in ("alt", "key"):
        return bool(x.get(f))
    if f == "gap":
        return x.get("gap") if S._met(x) == "no" else None
    return x.get(f)


def _lines(j: S.Judgment, sec: str) -> List[S.Line]:
    return dict(work=j.get("work"), required=j.get("required"), preferred=j.get("preferred")).get(sec) or []


def compare(want: S.Judgment, got: S.Judgment, cfg: dict) -> dict:
    """정답 판정 ↔ 에이전트 판정 → {lines, agree, diffs, verdict}."""
    diffs, lines, agree = [], 0, 0
    fails = lambda j: sorted(k for k, v in (j.get("gates") or {}).items() if v == "fail")   # noqa: E731
    if fails(want) != fails(got):
        diffs.append(f"조건 fail: 정답 {fails(want) or '없음'} · 판정 {fails(got) or '없음'}")
    for sec, fields in FIELDS.items():
        mine = {_norm(x.get("line")): x for x in _lines(got, sec)}
        seen = set()
        for x in _lines(want, sec):
            key = _norm(x.get("line"))
            lines += 1
            y = mine.get(key)
            if y is None:
                diffs.append(f"{sec}: 빠진 줄 — {x.get('line')}")
                continue
            seen.add(key)
            bad = [f"{f} {_value(x, f)!r}→{_value(y, f)!r}" for f in fields if _value(x, f) != _value(y, f)]
            if bad:
                diffs.append(f"{sec}: {x.get('line')} — {', '.join(bad)}")
            else:
                agree += 1
        for key, y in mine.items():
            if key not in seen:
                lines += 1
                diffs.append(f"{sec}: 더한 줄 — {y.get('line')}")
    wd, gd = want.get("direction") or {}, got.get("direction") or {}
    if wd.get("primary") != gd.get("primary"):
        diffs.append(f"direction.primary: {wd.get('primary')!r}→{gd.get('primary')!r}")
    if bool(want.get("domain_new")) != bool(got.get("domain_new")):
        diffs.append(f"domain_new: {want.get('domain_new') or '없음'!r}→{got.get('domain_new') or '없음'!r}")
    rw, rg = S.score(want, cfg), S.score(got, cfg)
    return dict(lines=lines, agree=agree, diffs=diffs, want=rw, got=rg, same=rw["verdict"] == rg["verdict"])


def run(folder: str, golden: str):
    cfg = K.load_yaml(os.path.join(golden, "scoring.yaml"))
    out = []
    for path in sorted(glob.glob(os.path.join(golden, "answers", "*.yaml"))):
        name = os.path.basename(path)
        want = S.load_judgment(path)
        mine = os.path.join(folder, name)
        if not os.path.exists(mine):
            out.append(dict(name=name, missing=True, rule=want.get("rule", "")))
            continue
        out.append(dict(name=name, missing=False, rule=want.get("rule", ""), **compare(want, S.load_judgment(mine), cfg)))
    return out


def _total(r):
    return "—" if r["total"] is None else r["total"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="판정 정답 세트 비교")
    ap.add_argument("folder", help="에이전트가 분류한 판정 폴더 (정답과 같은 파일 이름)")
    ap.add_argument("--golden", default=os.path.join(K.RES, "examples", "golden"))
    ap.add_argument("--min-lines", type=float, default=0.85, help="줄 일치율 기준 (기본 0.85)")
    ap.add_argument("--min-verdicts", type=float, default=0.8, help="결론 일치율 기준 (기본 0.8)")
    a = ap.parse_args(argv)

    res = run(a.folder, a.golden)
    if not res:
        print(f"정답 파일이 없습니다: {a.golden}/answers", file=sys.stderr)
        return 2
    lines = agree = same = 0
    for r in res:
        if r["missing"]:
            print(f"✗ {r['name']}: 판정 파일 없음")
            continue
        lines, agree, same = lines + r["lines"], agree + r["agree"], same + r["same"]
        mark = "✓" if r["same"] and not r["diffs"] else ("△" if r["same"] else "✗")
        print(f"{mark} {r['name']}: 결론 {r['want']['verdict']}({_total(r['want'])})"
              + ("" if r["same"] else f" → {r['got']['verdict']}({_total(r['got'])})")
              + f" · 줄 {r['agree']}/{r['lines']}")
        if r["diffs"]:
            print(f"    규칙: {r['rule']}")
            for d in r["diffs"]:
                print(f"    - {d}")
    line_rate = agree / lines if lines else 0.0
    verdict_rate = same / len(res)
    print(f"\n줄 일치 {agree}/{lines} ({line_rate:.0%}, 기준 {a.min_lines:.0%}) · "
          f"결론 일치 {same}/{len(res)} ({verdict_rate:.0%}, 기준 {a.min_verdicts:.0%})")
    return 0 if line_rate >= a.min_lines and verdict_rate >= a.min_verdicts else 1


if __name__ == "__main__":
    sys.exit(main())
