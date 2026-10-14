# -*- coding: utf-8 -*-
"""jobhunt 명령. 명령마다 scripts/ 의 스크립트를 그대로 돌린다 (jobhunt scan … = python3 scripts/scan.py …).

  jobhunt <명령> [인자…]     명령별 도움말: jobhunt <명령> --help
  jobhunt where              개인 자료 폴더와 설치 위치
  jobhunt changes [버전]     그 버전 뒤로 바뀐 점 (CHANGELOG)
  jobhunt --version
"""
from __future__ import annotations

import os
import re
import runpy
import shutil
import subprocess
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
    "git-log": ("git_log.sh", "로컬 git 저장소에서 내 커밋 로그"),
    "setup": ("setup.sh", "개인 자료 폴더 · 스킬 연결 · Chromium · 폰트 · poppler (터미널이면 고르는 화면, --yes 는 묻지 않고 전부)"),
}
# 설치본의 개인 자료 폴더에 두는 안내. 스킬을 읽지 않는 에이전트도 이 폴더에서 실행하면 설치된 지침을 찾아간다
HOME_AGENTS = """# jobhunt data folder

This folder holds the user's personal job-search data (`data/`). The jobhunt tool and its instructions are installed separately (`uv tool install`), so nothing here but `data/` belongs to jobhunt.

- Instructions: run `jobhunt where`, open `SKILL.md` in the folder it prints as "함께 배포된 파일", and follow it. Paths like `modes/…` and `references/…` are relative to that folder; paths like `data/…` are relative to this folder.
- Commands: `jobhunt <command>` (`jobhunt --help`).
- Keep personal data only under `data/` here.
"""


def version() -> str:
    """'1.1.0 (464475d)'. git 에서 설치했으면 커밋을 붙인다 (기본 브랜치에서 받으면 버전 번호만으로는 갱신 여부를 모른다)."""
    import json
    from importlib import metadata
    try:
        dist = metadata.distribution("jobhunt")
    except metadata.PackageNotFoundError:        # 저장소에서 설치 없이 돌 때
        with open(os.path.join(os.path.dirname(HERE), "pyproject.toml"), encoding="utf-8") as f:
            return re.search(r'^version = "([^"]+)"', f.read(), re.M).group(1)
    commit = (json.loads(dist.read_text("direct_url.json") or "{}").get("vcs_info") or {}).get("commit_id", "")
    return dist.version + (f" ({commit[:7]})" if commit else "")


def changes(res: str, since: str) -> str:
    """CHANGELOG 에서 since 버전보다 위(새) 절들. since 가 없거나 못 찾으면 맨 위 절 하나."""
    with open(os.path.join(res, "CHANGELOG.md"), encoding="utf-8") as f:
        secs = re.split(r"\n(?=## )", f.read())[1:]
    since = since.lstrip("v")
    out = []
    for s in secs:
        if since and re.match(rf"## v{re.escape(since)}\b", s):
            return "\n".join(out)
        out.append(s.strip() + "\n")
    return out[0] if out else ""


def prepare_home(res: str, root: str) -> None:
    """설치본: 개인 자료 폴더(root)에 data/ 뼈대(없는 파일만)와 에이전트 안내(AGENTS.md · CLAUDE.md, 없을 때만)를 둔다."""
    src, data = os.path.join(res, "skeleton", "data"), os.path.join(root, "data")
    for d, _, files in os.walk(src):
        for fn in files:
            dst = os.path.join(data, os.path.relpath(os.path.join(d, fn), src))
            if not os.path.exists(dst):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(os.path.join(d, fn), dst)
    for fn, text in (("AGENTS.md", HOME_AGENTS), ("CLAUDE.md", "@AGENTS.md\n")):
        path = os.path.join(root, fn)
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
    print(f"▶ 개인 자료 폴더: {data}", flush=True)       # 뒤에 도는 setup.sh 출력보다 먼저 보이게


def usage() -> str:
    rows = "\n".join(f"  {name:<12} {desc}" for name, (_, desc) in COMMANDS.items())
    return (f"사용: jobhunt <명령> [인자…]\n\n{rows}\n  {'where':<12} 개인 자료 폴더와 설치 위치\n"
            f"  {'changes':<12} 바뀐 점 (jobhunt changes 1.1.0 = 1.1.0 뒤로)\n  {'--version':<12} 설치된 버전\n")


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(usage(), end="")
        return 0
    if argv[0] in ("-V", "--version"):
        print(f"jobhunt {version()}")
        return 0
    cmd, rest = argv[0], argv[1:]
    sys.path.insert(0, HERE)                     # 스크립트끼리 import jobkit · import providers 로 부른다
    import jobkit as K
    if cmd == "where":
        print(f"개인 자료: {K.DATA}  (바꾸려면 JOBHUNT_HOME)\n함께 배포된 파일: {K.RES}\n코드: {HERE}")
        return 0
    if cmd == "changes":
        print(changes(K.RES, rest[0] if rest else ""), end="")
        return 0
    if cmd not in COMMANDS:
        print(f"모르는 명령: {cmd}\n\n{usage()}", end="", file=sys.stderr)
        return 2
    path = os.path.join(HERE, COMMANDS[cmd][0])
    if path.endswith(".sh"):
        env = dict(os.environ)
        if cmd == "setup":
            import setup_ui
            installed = K.RES == HERE
            # 터미널이면 고르는 화면. 개인 자료 폴더는 설치본에서, 아직 자료가 없고 JOBHUNT_HOME 으로 정하지 않았을 때만 묻는다
            root, rest = setup_ui.run(K.ROOT, rest, env, installed and not os.environ.get("JOBHUNT_HOME") and not os.path.isdir(K.DATA))
            if installed:                        # 설치본: 패키지 폴더를 스킬로 연결하고, 파이썬 패키지는 uv 가 이미 깔았다
                setup_ui.save_home(K.HOME_FILE, root)
                prepare_home(K.RES, root)
                env.update(JOBHUNT_HOME=root, JOBHUNT_PY=sys.executable, JOBHUNT_SKILL_SRC=HERE)
        return subprocess.call(["bash", path, *rest], env=env)
    sys.argv = [f"jobhunt {cmd}", *rest]
    runpy.run_path(path, run_name="__main__")    # 스크립트가 sys.exit 로 끝내면 그 종료 코드를 그대로 쓴다
    return 0


if __name__ == "__main__":
    sys.exit(main())
