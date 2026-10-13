# -*- coding: utf-8 -*-
"""jobhunt 명령. 명령마다 scripts/ 의 스크립트를 그대로 돌린다 (jobhunt scan … = python3 scripts/scan.py …).

  jobhunt <명령> [인자…]     명령별 도움말: jobhunt <명령> --help
  jobhunt where              개인 자료 폴더와 설치 위치
"""
from __future__ import annotations

import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
COMMANDS = {
    "scan": ("scan.py", "공고 수집"),
    "alive": ("alive.py", "마감 확인"),
    "weekly": ("weekly.py", "주간 스캔: 수집 → 마감 확인 → 보고표"),
    "score": ("score.py", "판정 파일 점수 계산 · pipeline.md 반영"),
    "tracker": ("tracker.py", "지원 현황표"),
    "report": ("report_html.py", "공고 현황표 HTML"),
    "discover": ("discover.py", "회사 찾기"),
    "render": ("render.py", "이력서 빌드 (yaml → PDF · PNG)"),
    "check": ("check.py", "이력서 검사"),
    "check-links": ("check_links.py", "링크 확인"),
    "cover-check": ("cover_check.py", "자기소개서 답변 검사"),
    "eval-golden": ("eval_golden.py", "판정 정답 세트와 비교"),
}


def usage() -> str:
    rows = "\n".join(f"  {name:<12} {desc}" for name, (_, desc) in COMMANDS.items())
    return f"사용: jobhunt <명령> [인자…]\n\n{rows}\n  {'where':<12} 개인 자료 폴더와 설치 위치\n"


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(usage(), end="")
        return 0
    cmd, rest = argv[0], argv[1:]
    sys.path.insert(0, HERE)                     # 스크립트끼리 import jobkit · import providers 로 부른다
    if cmd == "where":
        import jobkit as K
        print(f"개인 자료: {K.DATA}  (바꾸려면 JOBHUNT_HOME)\n함께 배포된 파일: {K.RES}\n코드: {HERE}")
        return 0
    if cmd not in COMMANDS:
        print(f"모르는 명령: {cmd}\n\n{usage()}", end="", file=sys.stderr)
        return 2
    path = os.path.join(HERE, COMMANDS[cmd][0])
    sys.argv = [f"jobhunt {cmd}", *rest]
    runpy.run_path(path, run_name="__main__")    # 스크립트가 sys.exit 로 끝내면 그 종료 코드를 그대로 쓴다
    return 0


if __name__ == "__main__":
    sys.exit(main())
