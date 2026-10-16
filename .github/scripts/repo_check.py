# -*- coding: utf-8 -*-
"""저장소 규칙 점검 (CI 전용, 패키지에 넣지 않음). 표준 라이브러리만 쓴다.

  python3 .github/scripts/repo_check.py pr <기준>        PR 이 바꾼 파일로 AGENTS.md 규칙 점검 (<기준>...HEAD)
  python3 .github/scripts/repo_check.py release <태그>   태그·버전·CHANGELOG 를 맞춰 보고 릴리스 본문을 출력

pr: 사용자가 알아챌 파일을 바꿨는데 CHANGELOG.md 가 그대로면 실패 (SKIP_CHANGELOG=true 면 넘김 — PR 의 '변경기록 없음' 라벨),
    CHANGELOG '다음 버전'에 줄이 있는데 '**data/ 이전:**' 줄이 없으면 실패 (빈 절이면 그 아래 새 버전 절에서), README.md·README.en.md 중 하나만 바꾸면 경고.
release: 태그 vX.Y.Z = pyproject.toml version = plugin.json version, CHANGELOG 에 '## vX.Y.Z — YYYY-MM-DD' 절과 그 줄(data/ 이전 줄 포함)이 있어야 한다.
"""
import json
import os
import re
import subprocess
import sys
from typing import List, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# 바꾸면 사용자가 알아채는 곳 (설치되는 스킬·스크립트·의존성). tests/·docs/·.github/ 는 아니다.
USER_FACING = ("scripts/", "modes/", "references/", "SKILL.md", "install.sh", "pyproject.toml", "requirements.txt")
SKIP_LABEL = "변경기록 없음"
MIGRATION = r"^- \*\*data/ 이전:\*\*"      # 버전마다 있어야 하는 줄 (옮길 것이 없으면 "없음")


def _read(root: str, *parts: str) -> str:
    with open(os.path.join(root, *parts), encoding="utf-8") as f:
        return f.read()


def _section(changelog: str, heading: str) -> str:
    """'## <heading>' 으로 시작하는 절의 본문 (다음 '## ' 앞까지). 없으면 빈 글자."""
    m = re.search(rf"^## {re.escape(heading)}\s*$\n(.*?)(?=^## |\Z)", changelog, re.M | re.S)
    return m.group(1).strip() if m else ""


def pr_problems(changed: List[str], changelog: str, skip_changelog: bool) -> Tuple[List[str], List[str]]:
    """(실패, 경고)."""
    errors, warnings = [], []
    facing = [f for f in changed if f.startswith(USER_FACING)]
    if facing and "CHANGELOG.md" not in changed and not skip_changelog:
        errors.append(f"사용자가 알아챌 파일을 바꿨는데 CHANGELOG.md 가 그대로입니다 ({', '.join(facing[:5])}"
                      f"{' …' if len(facing) > 5 else ''}). '다음 버전'에 한 줄을 더하거나, 사용자가 알아챌 변경이 아니면 "
                      f"PR 에 '{SKIP_LABEL}' 라벨을 붙이세요.")
    if "CHANGELOG.md" in changed:
        if not re.search(r"^## 다음 버전\s*$", changelog, re.M):
            errors.append("CHANGELOG.md 에 '## 다음 버전' 절이 없습니다.")
        elif _section(changelog, "다음 버전"):
            if not re.search(MIGRATION, _section(changelog, "다음 버전"), re.M):
                errors.append("CHANGELOG.md '다음 버전'에 '- **data/ 이전:**' 줄이 없습니다 (옮길 것이 없으면 '없음').")
        else:                                       # 릴리스 PR: 빈 '다음 버전' 아래 새 버전 절을 본다
            head = re.search(r"^## (v\d+\.\d+\.\d+ — \d{4}-\d{2}-\d{2})\s*$", changelog, re.M)
            if head and not re.search(MIGRATION, _section(changelog, head.group(1)), re.M):
                errors.append(f"CHANGELOG.md '{head.group(1)}' 절에 '- **data/ 이전:**' 줄이 없습니다 (옮길 것이 없으면 '없음').")
    readmes = {"README.md", "README.en.md"} & set(changed)
    if len(readmes) == 1:
        other = ({"README.md", "README.en.md"} - readmes).pop()
        warnings.append(f"{readmes.pop()} 만 바뀌었습니다. {other} 도 같은 내용으로 고쳐야 하는지 확인하세요.")
    return errors, warnings


def release_notes(tag: str, root: str = ROOT) -> str:
    """태그에 맞는 CHANGELOG 절의 본문. 맞지 않으면 ValueError."""
    if not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
        raise ValueError(f"태그 형식이 vX.Y.Z 가 아닙니다: {tag}")
    want = tag[1:]
    m = re.search(r'^version = "([^"]+)"', _read(root, "pyproject.toml"), re.M)
    got = {"pyproject.toml": m.group(1) if m else "(없음)",
           "plugin/.claude-plugin/plugin.json": json.loads(_read(root, "plugin", ".claude-plugin", "plugin.json")).get("version")}
    wrong = [f"{k} {v}" for k, v in got.items() if v != want]
    if wrong:
        raise ValueError(f"버전이 태그 {tag} 와 다릅니다: {', '.join(wrong)}")
    changelog = _read(root, "CHANGELOG.md")
    head = re.search(rf"^## ({re.escape(tag)} — \d{{4}}-\d{{2}}-\d{{2}})\s*$", changelog, re.M)
    if not head:
        raise ValueError(f"CHANGELOG.md 에 '## {tag} — YYYY-MM-DD' 절이 없습니다 ('다음 버전'을 이 이름으로 바꾸세요).")
    body = _section(changelog, head.group(1))
    if not body:
        raise ValueError(f"CHANGELOG.md '{head.group(1)}' 절이 비어 있습니다.")
    if not re.search(MIGRATION, body, re.M):
        raise ValueError(f"CHANGELOG.md '{head.group(1)}' 절에 '- **data/ 이전:**' 줄이 없습니다.")
    return body


def _annotate(kind: str, msg: str) -> None:
    print(f"::{kind}::{msg}" if os.environ.get("GITHUB_ACTIONS") else f"[{kind}] {msg}", file=sys.stderr)


def main(argv: List[str]) -> int:
    if len(argv) != 2 or argv[0] not in ("pr", "release"):
        sys.exit(__doc__)
    if argv[0] == "release":
        try:
            print(release_notes(argv[1]))
        except ValueError as e:
            _annotate("error", str(e))
            return 1
        return 0
    changed = subprocess.run(["git", "diff", "--name-only", f"{argv[1]}...HEAD"], cwd=ROOT, check=True,
                             capture_output=True, text=True).stdout.split()
    errors, warnings = pr_problems(changed, _read(ROOT, "CHANGELOG.md"), os.environ.get("SKIP_CHANGELOG") == "true")
    for w in warnings:
        _annotate("warning", w)
    for e in errors:
        _annotate("error", e)
    print(f"바뀐 파일 {len(changed)}개 · 실패 {len(errors)} · 경고 {len(warnings)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
