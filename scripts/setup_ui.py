# -*- coding: utf-8 -*-
"""jobhunt setup 의 선택 화면: 개인 자료 폴더 · 연결할 에이전트 · 연결 방식(스킬 링크 / 플러그인) · 이력서 PDF 빌드 환경.

화살표로 움직이고 스페이스로 고르고 엔터로 넘어간다. 'curl | bash' 로 돌아 표준 입력이 파이프여도 /dev/tty 로 묻는다.
터미널이 없거나(CI · cron) 인자를 주면 묻지 않고 setup.sh 가 인자대로(없으면 전부) 설치한다.
고른 결과는 setup.sh 인자(--no-skill · --skill-only)와 SKILLS_DIR 로 넘기고, 플러그인은 여기서 설치한다.
"""
from __future__ import annotations

import json
import os
import re
import select
import shutil
import subprocess
import sys
import unicodedata

MARKET = "jojaden/jobhunt"
# (이름, 홈 아래 폴더, 명령, 플러그인 설치 명령들) — 폴더가 있으면 그 에이전트가 깔린 것으로 본다 (setup.sh 와 같은 기준)
AGENTS = (
    ("Claude Code", ".claude", "claude", [["claude", "plugin", "install", "jobhunt", "--marketplace", MARKET]]),
    ("Codex", ".codex", "codex", [["codex", "plugin", "marketplace", "add", MARKET], ["codex", "plugin", "add", "jobhunt@jobhunt"]]),
)
ARROWS = {b"\x1b[A": "up", b"\x1bOA": "up", b"\x1b[B": "down", b"\x1bOB": "down",
          b"\r": "enter", b"\n": "enter", b"\x03": "ctrl-c"}
KEYS = {**ARROWS, b"k": "up", b"j": "down", b" ": "space"}                             # 고르기
EDIT = {**ARROWS, b"\t": "tab", b"\x7f": "back", b"\x08": "back", b"\x15": "clear"}   # 경로 입력
HIDE, SHOW = "\x1b[?25l", "\x1b[?25h"
SHOWN = 6                                        # 경로 후보를 몇 개까지 보여 줄지


def paint(code: str, s: str) -> str:
    return s if os.environ.get("NO_COLOR") else f"\x1b[{code}m{s}\x1b[0m"


BAR = paint("2", "│")


def tilde(path: str) -> str:
    home = os.path.expanduser("~")
    return "~" + path[len(home):] if path == home or path.startswith(home + os.sep) else path


def plugin_installed(home: str, folder: str) -> bool:
    """이 에이전트에 jobhunt 플러그인이 사용자 범위로 깔려 있나 (setup.sh plugin_installed 와 같은 판단)."""
    try:
        if folder == ".claude":
            with open(os.path.join(home, ".claude", "plugins", "installed_plugins.json"), encoding="utf-8") as f:
                d = json.load(f).get("plugins", {})
            return any(e.get("scope") == "user" for k, v in d.items() if k.startswith("jobhunt@") for e in v)
        with open(os.path.join(home, ".codex", "config.toml"), encoding="utf-8") as f:
            return re.search(r'^\[plugins\."jobhunt@', f.read(), re.M) is not None
    except (OSError, ValueError, AttributeError):
        return False


def complete(text: str, cwd: str) -> list[str]:
    """입력한 경로의 마지막 조각으로 시작하는 폴더들 ('../dev' → ['../develop/', …]). 숨김 폴더는 '.' 으로 시작할 때만."""
    head, prefix = os.path.split(text)
    try:
        names = os.listdir(os.path.join(cwd, os.path.expanduser(head or ".")))
    except OSError:
        return []
    base = os.path.join(cwd, os.path.expanduser(head or "."))
    return [os.path.join(head, n) + "/" for n in sorted(names, key=str.lower)
            if n.lower().startswith(prefix.lower()) and (prefix.startswith(".") or not n.startswith("."))
            and os.path.isdir(os.path.join(base, n))]


def target(text: str, cwd: str) -> str:
    """입력한 위치 아래의 jobhunt 폴더. 이름이 이미 jobhunt 면 그 폴더 (빈 입력은 ~ → ~/jobhunt)."""
    loc = os.path.normpath(os.path.join(cwd, os.path.expanduser(text or "~")))
    return loc if os.path.basename(loc) == "jobhunt" else os.path.join(loc, "jobhunt")


def problem(path: str) -> str:
    """개인 자료 폴더로 쓸 수 없는 이유 (쓸 수 있으면 빈 문자열)."""
    if os.path.exists(path) and not os.path.isdir(path):
        return "같은 이름의 파일이 있습니다"
    try:
        if os.path.isdir(path) and os.listdir(path) and not os.path.isdir(os.path.join(path, "data")):
            return "다른 파일이 있는 폴더입니다. 다른 위치를 고르세요"
    except OSError:
        return "읽을 수 없는 폴더입니다. 다른 위치를 고르세요"
    if path.startswith("/mnt/") and os.path.exists("/proc/version"):
        with open("/proc/version", encoding="utf-8", errors="ignore") as f:
            if "microsoft" in f.read().lower():
                return "Windows 드라이브(/mnt/...)는 느리고 스킬 링크가 깨질 수 있습니다. WSL 홈(~) 아래를 고르세요"
    return ""


def fit(line: str, cols: int) -> str:
    """색 코드는 두고 보이는 글자만 cols-1 칸까지 (한글은 두 칸). 줄이 접히면 다시 그릴 때 지울 줄 수가 어긋난다."""
    out, width = [], 0
    for tok in re.findall(r"\x1b\[[0-9;?]*[A-Za-z]|.", line):
        if not tok.startswith("\x1b"):
            width += 2 if unicodedata.east_asian_width(tok) in "WF" else 1
            if width >= cols:
                out.append("…\x1b[0m")
                break
        out.append(tok)
    return "".join(out)


def save_home(path: str, root: str) -> None:
    """설치본이 쓸 개인 자료 폴더를 path(jobkit.HOME_FILE)에 기억한다. 기본 위치(~/jobhunt)면 파일을 만들지 않고, 있으면 지운다."""
    if root == os.path.expanduser("~/jobhunt"):
        if os.path.exists(path):
            os.remove(path)
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(root + "\n")


class Term:
    """/dev/tty 로 그리고 읽는다. 앞서 그린 줄 수를 기억했다가 지우고 다시 그린다."""

    def __init__(self, fd: int, saved=None):
        self.fd, self.lines, self.saved = fd, 0, saved

    @classmethod
    def open(cls) -> Term | None:
        """묻는 동안 내내 글자 단위 입력(cbreak, 화면에 찍지 않음)으로 둔다. 키를 읽을 때만 바꾸면 그 사이에 친 글자가 버려진다."""
        import termios
        import tty
        try:
            fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY)
        except OSError:                          # 터미널 없음 (CI · cron)
            return None
        saved = termios.tcgetattr(fd)
        tty.setcbreak(fd)
        return cls(fd, saved)

    def close(self) -> None:
        """입력 방식을 되돌리고 커서를 다시 보이게 한다 (중간에 오류가 나도)."""
        import termios
        self.write(SHOW)
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.saved)
        os.close(self.fd)

    def write(self, s: str) -> None:
        os.write(self.fd, s.encode())

    def read_key(self) -> bytes:
        b = os.read(self.fd, 1)
        if b == b"\x1b":                         # ESC [ … 끝 바이트(@~~): 화살표 ESC [ A, Ctrl-↑ ESC [ 1 ; 5 A, Delete ESC [ 3 ~
            while select.select([self.fd], [], [], 0.05)[0]:
                b += os.read(self.fd, 1)
                if len(b) == 3 and b[1:2] == b"O" or len(b) > 2 and b[1:2] == b"[" and 0x40 <= b[-1] <= 0x7E \
                        or b[1:2] not in (b"[", b"O"):
                    break
        elif b and b[0] >= 0xC0:                 # 한글 등 UTF-8 여러 바이트 글자
            b += os.read(self.fd, 1 if b[0] < 0xE0 else 2 if b[0] < 0xF0 else 3)
        return b

    def key(self, table: dict) -> str:
        """표에 있는 키는 이름으로, 아니면 입력한 글자 그대로 (제어 문자는 빈 문자열)."""
        b = self.read_key()
        if not b:                                # 터미널이 닫힘
            raise KeyboardInterrupt
        k = table.get(b) or ("" if b[:1] < b" " or b.startswith(b"\x1b") else b.decode(errors="ignore"))
        if k == "ctrl-c":
            raise KeyboardInterrupt
        return k

    def frame(self, lines: list[str], final: bool = False) -> None:
        try:
            cols = os.get_terminal_size(self.fd).columns
        except OSError:
            cols = 0
        if cols > 0:                             # 폭을 모르는 터미널(0)은 자르지 않는다
            lines = [fit(s, cols) for s in lines]
        clear = f"\x1b[{self.lines}F\x1b[J" if self.lines else ""
        self.write(clear + ("" if final else HIDE) + "".join(f"{s}\n" for s in lines) + (SHOW if final else ""))
        self.lines = 0 if final else len(lines)

    def done(self, title: str, answer: str) -> None:
        self.frame([f"{paint('32', '◇')}  {title}", f"{BAR}  {paint('2', answer)}", BAR], final=True)

    def choose(self, title: str, labels: list[str], picked: list[int], multi: bool = False,
               hints: list[str] | None = None) -> list[int]:
        """하나 고르기면 [커서 자리], 여러 개면 고른 칸들. picked 는 처음 고른 칸(하나 고르기는 처음 커서)."""
        hints = hints or [""] * len(labels)
        cur, chosen = (0 if multi or not picked else picked[0]), set(picked)
        keys = "↑↓ 이동 · 스페이스 선택 · 엔터 확인" if multi else "↑↓ 이동 · 엔터 확인"
        while True:
            rows = [f"{paint('36', '◆')}  {title}"]
            for i, (label, hint) in enumerate(zip(labels, hints)):
                if multi:
                    mark = f"{paint('36', '›') if i == cur else ' '} {paint('32', '◼') if i in chosen else paint('2', '◻')}"
                else:
                    mark = paint("36", "●") if i == cur else paint("2", "○")
                text = label if multi or i == cur else paint("2", label)
                rows.append(f"{BAR}  {mark} {text}" + (f"  {paint('2', hint)}" if hint else ""))
            self.frame(rows + [f"{paint('2', '└')}  {paint('2', keys)}"])
            k = self.key(KEYS)
            if k in ("up", "down"):
                cur = (cur + (1 if k == "down" else -1)) % len(labels)
            elif k == "space" and multi:
                chosen ^= {cur}
            elif k == "enter":
                break
        result = sorted(chosen) if multi else [cur]
        self.done(title, " · ".join(labels[i] for i in result) or "없음")
        return result

    def folder(self, title: str, cwd: str, resolve=target, check=problem, empty: str = "~ (엔터: ~/jobhunt)") -> str:
        """경로 입력. 입력한 경로 아래 폴더를 후보로 보여 주고 Tab 으로 채운다. resolve 로 바꾼 경로를 check 가 통과시키면 돌려준다."""
        text, cur, err = "", 0, ""
        while True:
            cands = complete(text, cwd) if text else []
            cur = min(cur, max(len(cands) - 1, 0))
            dest = resolve(text, cwd)
            shown = text + paint("7", " ") if text else paint("7", " ") + paint("2", empty)
            rows = [f"{paint('36', '◆')}  {title}", f"{BAR}  {shown}"]
            start = max(0, cur - SHOWN + 1)
            for i, c in enumerate(cands[start:start + SHOWN], start):
                rows.append(f"{BAR}  {paint('36', '›') + ' ' + c if i == cur else '  ' + paint('2', c)}")
            if len(cands) > SHOWN:
                rows.append(f"{BAR}  {paint('2', f'  … {len(cands)}개 중 {cur + 1}번째')}")
            rows.append(f"{BAR}  " + (paint("31", err) if err else paint("2", f"→ {tilde(dest)}" if dest else "")))
            self.frame(rows + [f"{paint('2', '└')}  {paint('2', 'Tab 후보 채우기 · ↑↓ 후보 · 엔터 확인')}"])
            k = self.key(EDIT)
            err = ""
            if k in ("up", "down") and cands:
                cur = (cur + (1 if k == "down" else -1)) % len(cands)
            elif k == "tab" and cands:
                text, cur = cands[cur], 0
            elif k == "back":
                text, cur = text[:-1], 0
            elif k == "clear":
                text, cur = "", 0
            elif k == "enter":
                err = check(dest)
                if not err:
                    break
            elif k not in ("up", "down", "tab", ""):
                text, cur = text + k, 0
        self.done(title, tilde(dest))
        return dest


def ask(t: Term, home: str, env: dict, root: str, ask_root: bool, cwd: str) -> tuple[str, list[str], list[tuple]]:
    """고른 대로 (개인 자료 폴더, setup.sh 인자, 설치할 플러그인). env 의 SKILLS_DIR 를 채운다."""
    t.write(f"{paint('36', '◆')}  jobhunt 설정\n{BAR}\n")
    if ask_root:
        root = t.folder("개인 자료를 어디에 둘까요? (그 아래 jobhunt 폴더를 만듭니다)", cwd)
    else:                                        # 이미 자료가 있거나 JOBHUNT_HOME 으로 정한 폴더는 묻지 않는다
        t.done("개인 자료 폴더", tilde(root))
    args, plugins = [], []
    if env.get("SKILLS_DIR") or env.get("CLAUDE_SKILLS_DIR"):   # 사용자가 정한 스킬 폴더는 그대로 쓴다
        t.done("스킬 폴더 (SKILLS_DIR)", env.get("SKILLS_DIR") or env["CLAUDE_SKILLS_DIR"])
    else:
        found = [a for a in AGENTS if os.path.isdir(os.path.join(home, a[1]))]
        linked = [os.path.lexists(os.path.join(home, a[1], "skills", "jobhunt")) for a in found]
        plugged = [plugin_installed(home, a[1]) for a in found]
        first = not any(linked + plugged)        # 처음 설치면 감지된 에이전트를 모두, 갱신이면 지금 연결된 것만 골라 둔다
        labels = [a[0] for a in found] + ["다른 위치 (스킬 폴더 경로 입력)"]
        hints = ["플러그인 설치됨" if p else "연결됨" if l else "" for l, p in zip(linked, plugged)] + [""]
        picked = [i for i in range(len(found)) if first or linked[i] or plugged[i]]
        dirs = []
        for i in t.choose("어떤 에이전트에 연결할까요?", labels, picked, multi=True, hints=hints):
            if i == len(found):
                dirs.append(t.folder("스킬 폴더 경로", cwd, resolve=lambda s, c: os.path.normpath(os.path.join(c, os.path.expanduser(s))) if s else "",
                                     check=lambda p: "" if p else "경로를 입력하세요", empty="예: ~/.gemini/skills"))
                continue
            name, folder, cmd, cmds = found[i]
            dirs.append(os.path.join(home, folder, "skills"))   # 플러그인을 깔아도 넣는다: setup.sh 가 예전 링크를 걷어 낸다
            if plugged[i] or not shutil.which(cmd):   # 이미 플러그인이면 그대로, 플러그인을 깔 명령이 없으면 링크
                continue
            how = t.choose(f"{name} 연결 방식", ["스킬 링크", "플러그인"], [0],
                           hints=[f"~/{folder}/skills/jobhunt", f"{cmd} plugin 으로 설치"])
            if how == [1]:
                plugins.append((name, folder, cmds))
        if dirs:
            env["SKILLS_DIR"] = ":".join(dirs)
        else:
            args.append("--no-skill")
    pdf = t.choose("이력서 PDF 빌드 환경을 설치할까요?", ["설치", "나중에"], [0],
                   hints=["Chromium · 한글 폰트 · poppler, 수백 MB", "jobhunt setup --no-skill"])
    if pdf == [1]:
        args.append("--skill-only")
    start = "개인 자료 폴더만 준비합니다 (나중에 jobhunt setup)" if "--no-skill" in args and "--skill-only" in args else "설치를 시작합니다"
    t.write(f"{paint('2', '└')}  {start}\n\n")
    return root, args, plugins


def run(root: str, args: list[str], env: dict, ask_root: bool) -> tuple[str, list[str], bool]:
    """터미널이고 인자가 없으면 물어서 (개인 자료 폴더, setup.sh 인자, 폴더를 화면에서 골랐나)를 돌려준다. --yes 는 묻지 않고 전부."""
    if "--yes" in args or "-y" in args:
        return root, [a for a in args if a not in ("--yes", "-y")], False
    t = None if args else Term.open()
    if t is None:
        return root, args, False
    home = os.path.expanduser("~")
    try:
        root, args, plugins = ask(t, home, env, root, ask_root, os.getcwd())
    except KeyboardInterrupt:
        t.write("\n")
        print("설정을 취소했습니다. 다시 하려면: jobhunt setup", file=sys.stderr)
        raise SystemExit(130)
    finally:
        t.close()
    for name, folder, cmds in plugins:
        print(f"▶ {name} 플러그인", flush=True)
        for c in cmds:                           # codex 마켓플레이스가 이미 있으면 add 가 실패해도 된다: 결과는 아래에서 본다
            subprocess.call(c)
        if not plugin_installed(home, folder):
            print(f"  {name} 플러그인을 설치하지 못해 스킬 링크로 연결합니다", flush=True)
    return root, args, ask_root
