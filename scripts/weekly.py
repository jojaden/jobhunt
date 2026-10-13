# -*- coding: utf-8 -*-
"""주간 스캔의 LLM 없는 부분: 수집 → 마감 확인 → 통합 보고표.
1차 선별(brief.md 기준)과 평가는 AI 에이전트가 이어서 한다 (modes/scan.md 4단계부터).

  jobhunt weekly [--since YYYY-MM-DD]      (기본: 7일 전. 저장소에서는 bash scripts/weekly.sh 와 같다)

cron/launchd 로 돌려도 된다. 결과: data/search/reports/YYYY-MM-DD.md
"""
from __future__ import annotations

import argparse
import contextlib
import io
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import alive  # noqa: E402
import jobkit as K  # noqa: E402
import scan  # noqa: E402
import tracker  # noqa: E402


def _run(fn, argv):
    """한 단계가 멈춰도(sys.exit) 다음 단계는 돈다. 멈춘 이유는 보고서에 남긴다."""
    try:
        fn(argv)
    except SystemExit as e:
        if isinstance(e.code, str):
            print(e.code, file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser(description="주간 스캔: 수집 → 마감 확인 → 보고표")
    ap.add_argument("--since", default=(date.today() - timedelta(days=7)).isoformat())
    a = ap.parse_args(argv)

    out = os.path.join(K.P["reports"], f"{K.TODAY}.md")
    os.makedirs(K.P["reports"], exist_ok=True)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        print(f"# 주간 스캔 {K.TODAY}\n\n```")
        _run(scan.main, [])
        print()
        _run(alive.main, ["--write"])
        print("```\n")
        _run(tracker.main, ["report", "--since", a.since])
        print()
        print("다음: AI 에이전트에게 \"새로 수집한 공고 선별해줘\" → modes/scan.md 4단계 (pipeline.md '새로 수집 (선별 전)')")
    K.write_text(out, buf.getvalue())
    print(f"보고서: {out}")
    print("\n".join([l for l in buf.getvalue().split("\n") if l.startswith(("  ", "──"))][:30]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
