# -*- coding: utf-8 -*-
"""jobhunt setup 선택 화면(setup_ui.py): 경로 후보 · 고르기 · setup.sh 인자로 바꾸기 · 고른 폴더 기억."""
import os
import shutil
import subprocess
import sys
import unittest
from unittest import mock

from support import HERE, TMP

import setup_ui

UP, DOWN, ENTER, SPACE, TAB, BACK, CLEAR = b"\x1b[A", b"\x1b[B", b"\r", b" ", b"\t", b"\x7f", b"\x15"


class Fake(setup_ui.Term):
    """정해 둔 키를 차례로 누르는 터미널."""

    def __init__(self, keys):
        super().__init__(-1)
        self.keys, self.out = list(keys), []

    def write(self, s):
        self.out.append(s)

    def read_key(self):
        return self.keys.pop(0)


def typed(text):
    return [ch.encode() for ch in text]


class Paths(unittest.TestCase):
    def setUp(self):
        self.base = os.path.join(TMP, "ui-paths")
        for d in ("develop", "devops", ".dev", os.path.join("busy", "jobhunt"), os.path.join("old", "jobhunt", "data")):
            os.makedirs(os.path.join(self.base, d), exist_ok=True)
        for f in ("dev.txt", os.path.join("busy", "jobhunt", "notes.md")):
            open(os.path.join(self.base, f), "w").close()

    def tearDown(self):
        shutil.rmtree(self.base)

    def test_complete(self):
        """마지막 조각으로 시작하는 폴더만, 숨김 폴더는 '.' 으로 시작할 때만, 상대 경로는 입력한 모양 그대로."""
        self.assertEqual(setup_ui.complete("dev", self.base), ["develop/", "devops/"])
        self.assertEqual(setup_ui.complete("DEV", self.base), ["develop/", "devops/"])
        self.assertEqual(setup_ui.complete(".d", self.base), [".dev/"])
        sub = os.path.join(self.base, "develop")
        self.assertEqual(setup_ui.complete("../dev", sub), ["../develop/", "../devops/"])
        self.assertEqual(setup_ui.complete("없는곳/x", self.base), [])

    def test_target_and_problem(self):
        """고른 위치 아래 jobhunt 폴더 (이름이 jobhunt 면 그대로). 다른 파일이 있는 폴더는 쓰지 않는다."""
        self.assertEqual(setup_ui.target("develop", self.base), os.path.join(self.base, "develop", "jobhunt"))
        self.assertEqual(setup_ui.target("old/jobhunt/", self.base), os.path.join(self.base, "old", "jobhunt"))
        self.assertEqual(setup_ui.target("", self.base), os.path.expanduser("~/jobhunt"))
        self.assertEqual(setup_ui.problem(os.path.join(self.base, "develop", "jobhunt")), "")   # 없는 폴더
        self.assertEqual(setup_ui.problem(os.path.join(self.base, "old", "jobhunt")), "")       # 이미 쓰던 폴더
        self.assertIn("다른 파일", setup_ui.problem(os.path.join(self.base, "busy", "jobhunt")))
        self.assertIn("파일", setup_ui.problem(os.path.join(self.base, "dev.txt")))

    def test_folder_tab_and_retry(self):
        """Tab 은 고른 후보로 채우고, 쓸 수 없는 폴더는 그 자리에서 다시 묻는다. 한글도 입력된다."""
        t = Fake(typed("한") + [BACK] + typed("de") + [DOWN, TAB, ENTER])
        self.assertEqual(t.folder("어디", self.base), os.path.join(self.base, "devops", "jobhunt"))
        t = Fake(typed("busy") + [ENTER, CLEAR] + typed("develop") + [ENTER])
        self.assertEqual(t.folder("어디", self.base), os.path.join(self.base, "develop", "jobhunt"))
        self.assertTrue(any("다른 파일" in s for s in t.out))


class Ask(unittest.TestCase):
    def setUp(self):
        self.home = os.path.join(TMP, "ui-home")
        for d in (".claude", ".codex"):
            os.makedirs(os.path.join(self.home, d), exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.home)

    def ask(self, keys, which=None, env=None):
        env = {} if env is None else env
        with mock.patch.object(setup_ui.shutil, "which", return_value=which):
            root, args, plugins = setup_ui.ask(Fake(keys), self.home, env, "/x/jobhunt", False, self.home)
        return args, env.get("SKILLS_DIR"), [p[0] for p in plugins]

    def skills(self, *agents):
        return ":".join(os.path.join(self.home, a, "skills") for a in agents)

    def test_first_install(self):
        """처음이면 감지된 에이전트를 모두 골라 둔다. PDF 환경을 미루면 --skill-only."""
        self.assertEqual(self.ask([ENTER, DOWN, ENTER]), (["--skill-only"], self.skills(".claude", ".codex"), []))
        self.assertEqual(self.ask([SPACE, DOWN, SPACE, ENTER, ENTER]), (["--no-skill"], None, []))

    def test_update_keeps_current_and_installs_plugin(self):
        """갱신이면 지금 연결된 에이전트만 골라 두고, 플러그인을 고르면 설치할 목록에 넣는다 (SKILLS_DIR 에도 넣어 예전 링크를 걷게)."""
        link = os.path.join(self.home, ".claude", "skills", "jobhunt")
        os.makedirs(os.path.dirname(link))
        os.symlink(TMP, link)
        self.assertEqual(self.ask([ENTER, DOWN, ENTER, ENTER], which="/bin/claude"),
                         ([], self.skills(".claude"), ["Claude Code"]))

    def test_skills_dir_env(self):
        """SKILLS_DIR 를 주면 에이전트는 묻지 않는다."""
        self.assertEqual(self.ask([ENTER], env={"SKILLS_DIR": "/s"}), ([], "/s", []))

    def test_run_without_prompt(self):
        """--yes 나 다른 인자를 주거나 터미널이 없으면 묻지 않는다."""
        self.assertEqual(setup_ui.run("/r", ["--yes", "--no-skill"], {}, True), ("/r", ["--no-skill"]))
        with mock.patch.object(setup_ui.Term, "open", side_effect=AssertionError("묻지 않아야 함")):
            self.assertEqual(setup_ui.run("/r", ["--skill-only"], {}, True), ("/r", ["--skill-only"]))
        with mock.patch.object(setup_ui.Term, "open", return_value=None):
            self.assertEqual(setup_ui.run("/r", [], {}, True), ("/r", []))


class Home(unittest.TestCase):
    def test_saved_home(self):
        """기본이 아닌 폴더만 기억하고, 설치본 jobkit 은 JOBHUNT_HOME 이 없으면 그 폴더를 쓴다."""
        conf = os.path.join(TMP, "xdg")
        path = os.path.join(conf, "jobhunt", "home")
        setup_ui.save_home(path, "/data/jh")
        with open(path, encoding="utf-8") as f:
            self.assertEqual(f.read(), "/data/jh\n")
        pkg = os.path.join(TMP, "installed", "jobhunt")          # jobkit.py 옆에 references/ 가 있으면 설치본
        os.makedirs(os.path.join(pkg, "references"), exist_ok=True)
        shutil.copy(os.path.join(os.path.dirname(HERE), "scripts", "jobkit.py"), pkg)
        env = {k: v for k, v in os.environ.items() if k != "JOBHUNT_HOME"}
        root = lambda e: subprocess.run([sys.executable, "-c", "import jobkit; print(jobkit.ROOT)"], cwd=pkg,
                                        env=dict(e, XDG_CONFIG_HOME=conf), capture_output=True, text=True).stdout.strip()
        self.assertEqual(root(env), "/data/jh")
        self.assertEqual(root(dict(env, JOBHUNT_HOME="/env/jh")), "/env/jh")
        setup_ui.save_home(path, os.path.expanduser("~/jobhunt"))
        self.assertFalse(os.path.exists(path))
        self.assertEqual(root(env), os.path.expanduser("~/jobhunt"))


if __name__ == "__main__":
    unittest.main()
