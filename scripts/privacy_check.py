# -*- coding: utf-8 -*-
"""개인 자료가 커밋·PR 에 들어가지 않게 막는다. 표준 라이브러리 (--staged 는 profile.yaml 을 PyYAML 로, 없으면 간단히 직접 읽는다).

  python3 scripts/privacy_check.py            추적 중인 파일 중 data/ 허용 목록 밖의 파일 (CI)
  python3 scripts/privacy_check.py --staged   커밋하려는 파일: 위 검사 + 더하는 줄에 data/profile/profile.yaml 의
                                              이름·이메일·전화번호·학교가 있는지 (pre-commit 훅)

허용 목록: data/README.md, data/<폴더>/ 의 README.md · .gitkeep · *.example.* (.gitignore 와 같은 기준).
훅 켜기: git config core.hooksPath .githooks   (scripts/setup.sh 가 안내). 급할 때 건너뛰기: git commit --no-verify
이미 저장소(HEAD)에 들어 있는 값(예: 공개한 GitHub 주소의 이름)은 검사에서 빼고 알려 준다.
바이너리 파일(PDF·PNG)의 내용은 보지 않는다.
"""
import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOWED = re.compile(r"^data/(README\.md|[^/]+/(README\.md|\.gitkeep|[^/]*\.example\.[^/]*))$")
FIELDS = [("name", "이름"), ("email", "이메일"), ("phone", "전화번호"), ("education.school", "학교")]


def git(*args, check=True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True, check=check)


def bad_paths(paths):
    return [p for p in paths if p.startswith("data/") and not ALLOWED.match(p)]


def _simple_yaml(text: str) -> dict:
    """PyYAML 이 없을 때(훅이 다른 가상환경의 python3 로 돌 때): profile.yaml 의 '키: 값' 을 들여쓰기로 중첩해 읽는다."""
    out: dict = {}
    stack: list[tuple[int, str | None]] = [(-1, None)]
    for line in text.split("\n"):
        m = re.match(r"^(\s*)([\w-]+):\s*(.*?)\s*$", re.sub(r"(^|\s)#.*$", "", line))   # 주석을 떼고
        if not m:
            continue
        indent, key, val = len(m.group(1)), m.group(2), m.group(3)
        while stack[-1][0] >= indent:
            stack.pop()
        node = out
        for _, k in stack[1:]:
            node = node.setdefault(k, {})
        if val:
            node[key] = val.strip("'\"")
        else:
            stack.append((indent, key))
    return out


def personal_values():
    """[(항목 이름, 정규식)]. profile.yaml 이 없으면 빈 목록."""
    path = os.path.join(ROOT, "data", "profile", "profile.yaml")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        text = f.read()
    try:
        import yaml
        prof = yaml.safe_load(text) or {}
    except ImportError:
        prof = _simple_yaml(text)
    out = []
    for key, label in FIELDS:
        v = prof
        for k in key.split("."):
            v = v.get(k) if isinstance(v, dict) else None
        v = str(v or "").strip()
        if len(v) < 2:
            continue
        if git("grep", "-F", "-q", "-i", "-e", v, "HEAD", "--", check=False).returncode == 0:
            print(f"  참고: profile.yaml 의 {label}은(는) 이미 저장소에 있어 검사에서 뺍니다", file=sys.stderr)
            continue
        if key == "phone":                       # 010-1234-5678 · 01012345678 · 010 1234 5678 모두
            rx = re.compile(r"[\s.-]?".join(re.escape(d) for d in re.sub(r"\D", "", v)))
        else:
            rx = re.compile(re.escape(v), re.I)
        out.append((label, rx))
    return out


def added_lines():
    """커밋하려는 변경에서 더하는 줄 [(파일, 줄)]."""
    diff = git("diff", "--cached", "-U0", "--no-color", "--no-ext-diff", "--diff-filter=ACMR").stdout
    out, cur = [], None
    for line in diff.split("\n"):
        if line.startswith("+++ "):
            cur = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("+") and cur:
            out.append((cur, line[1:]))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="개인 자료 커밋 방지")
    ap.add_argument("--staged", action="store_true", help="커밋하려는 파일만 (pre-commit 훅)")
    a = ap.parse_args(argv)

    if a.staged:
        paths = git("diff", "--cached", "--name-only", "--diff-filter=ACMR").stdout.split()
    else:
        paths = git("ls-files").stdout.split("\n")
    problems = [f"{p}  ← data/ 의 개인 자료 (허용: README.md · .gitkeep · *.example.*)" for p in bad_paths(paths)]

    if a.staged:
        rules = personal_values()
        for path, line in added_lines():
            for label, rx in rules:
                if rx.search(line):
                    problems.append(f"{path}  ← profile.yaml 의 {label}")

    if problems:
        print("개인 자료가 들어 있어 멈춥니다:", file=sys.stderr)
        for p in sorted(set(problems)):
            print(f"  {p}", file=sys.stderr)
        print("빼려면: git restore --staged <파일> (이미 추적 중이면 git rm --cached <파일>)"
              + ("\n정말 괜찮으면: git commit --no-verify" if a.staged else ""), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
