# -*- coding: utf-8 -*-
"""jobhunt 명령(cli.py)과 자료 위치, 주간 실행(weekly.py)."""
import contextlib
import io
import os
import re
import subprocess
import sys
import unittest
from types import SimpleNamespace

from support import HERE, TMP, K

import cli
import weekly

SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")


class Cli(unittest.TestCase):
    def test_commands_exist(self):
        for name, (fn, _) in cli.COMMANDS.items():
            self.assertTrue(os.path.exists(os.path.join(SCRIPTS, fn)), name)

    def test_help_and_unknown(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(cli.main(["--help"]), 0)
        self.assertIn("scan", out.getvalue())
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["nope"]), 2)

    def test_home(self):
        """개인 자료 폴더: JOBHUNT_HOME 이 먼저, 없으면 저장소에서 돌 때 저장소 루트."""
        code = "import jobkit; print(jobkit.ROOT); print(jobkit.RES)"
        env = {k: v for k, v in os.environ.items() if k != "JOBHUNT_HOME"}
        run = lambda e: subprocess.run([sys.executable, "-c", code], cwd=SCRIPTS, env=e, capture_output=True, text=True).stdout.split()
        repo = os.path.dirname(SCRIPTS)
        self.assertEqual(run(env), [repo, repo])
        self.assertEqual(run(dict(env, JOBHUNT_HOME="/tmp/jobhunt-x"))[0], "/tmp/jobhunt-x")

    def test_deps_match(self):
        """pyproject.toml 의 dependencies 와 requirements.txt 가 같다 (setup.sh 는 requirements.txt 로 설치한다)."""
        repo = os.path.dirname(SCRIPTS)
        with open(os.path.join(repo, "pyproject.toml"), encoding="utf-8") as f:
            block = re.search(r"^dependencies = \[(.*?)\]", f.read(), re.S | re.M).group(1)
        with open(os.path.join(repo, "requirements.txt"), encoding="utf-8") as f:
            self.assertEqual(sorted(re.findall(r'"([^"]+)"', block)), sorted(f.read().split()))

    def test_changes(self):
        """그 버전보다 새 절만. 버전을 모르면 맨 위 절 하나."""
        d = os.path.join(TMP, "res")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "CHANGELOG.md"), "w", encoding="utf-8") as f:
            f.write("# 변경 기록\n\n## 다음 버전\n\n- 새것\n\n## v1.1.0 — 2026-10-08\n\n- 중간\n\n## v1.0.0 — 2026-09-01\n\n- 처음\n")
        self.assertEqual(cli.changes(d, "1.1.0"), "## 다음 버전\n\n- 새것\n")
        self.assertIn("- 중간", cli.changes(d, "v1.0.0"))
        self.assertNotIn("- 처음", cli.changes(d, "v1.0.0"))
        self.assertEqual(cli.changes(d, ""), "## 다음 버전\n\n- 새것\n")

    def test_version_in_repo(self):
        self.assertRegex(cli.version(), r"^\d+\.\d+\.\d+")

    def test_prepare_home(self):
        """설치본 setup: 뼈대는 없는 파일만 복사하고, 에이전트 안내는 없을 때만 쓴다."""
        res, home = os.path.join(TMP, "pkg"), os.path.join(TMP, "home")
        os.makedirs(os.path.join(res, "skeleton", "data", "profile"), exist_ok=True)
        for fn, text in (("README.md", "뼈대"), ("profile.example.yaml", "예시")):
            with open(os.path.join(res, "skeleton", "data", "profile", fn), "w", encoding="utf-8") as f:
                f.write(text)
        os.makedirs(os.path.join(home, "data", "profile"), exist_ok=True)
        with open(os.path.join(home, "data", "profile", "README.md"), "w", encoding="utf-8") as f:
            f.write("사용자가 고친 것")
        k = SimpleNamespace(RES=res, ROOT=home, DATA=os.path.join(home, "data"))
        with contextlib.redirect_stdout(io.StringIO()):
            cli.prepare_home(k)
        read = lambda *p: K.read_text(os.path.join(home, *p))
        self.assertEqual(read("data", "profile", "README.md"), "사용자가 고친 것")
        self.assertEqual(read("data", "profile", "profile.example.yaml"), "예시")
        self.assertIn("jobhunt where", read("AGENTS.md"))
        self.assertEqual(read("CLAUDE.md"), "@AGENTS.md\n")

    def test_setup_relinks_old_jobhunt(self):
        """setup.sh: 예전 git 설치(옮겨 둬 SKILL.md 가 없음)를 가리키던 링크는 바꾸고, 다른 스킬·살아 있는 다른 jobhunt 사본은 그대로 둔다."""
        repo = os.path.dirname(SCRIPTS)
        skills, old, other = (os.path.join(TMP, n) for n in ("skills", "old-clone", "other-skill"))
        for d in (skills, old, other):
            os.makedirs(d, exist_ok=True)
        with open(os.path.join(other, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("---\nname: other\n---\n")
        link = os.path.join(skills, "jobhunt")
        run = lambda: subprocess.run(["bash", os.path.join(SCRIPTS, "setup.sh"), "--skill-only"], capture_output=True, text=True,
                                     env=dict(os.environ, SKILLS_DIR=skills), cwd=TMP)
        os.symlink(old, link)
        run()
        self.assertEqual(os.path.realpath(link), os.path.realpath(repo))
        os.remove(link)
        os.symlink(other, link)
        self.assertIn("다른 스킬", run().stdout)
        self.assertEqual(os.path.realpath(link), os.path.realpath(other))
        # 살아 있는 다른 jobhunt 사본(개발용 clone)은 사용자가 고른 것이라 그대로 둔다
        clone = os.path.join(TMP, "dev-clone")
        os.makedirs(clone, exist_ok=True)
        with open(os.path.join(clone, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write("---\nname: jobhunt\n---\n")
        os.remove(link)
        os.symlink(clone, link)
        self.assertIn("다른 jobhunt 사본", run().stdout)
        self.assertEqual(os.path.realpath(link), os.path.realpath(clone))


class Weekly(unittest.TestCase):
    def test_report(self):
        """수집이 멈춰도(sys.exit) 마감 확인·보고표는 돌고, 보고서에 셋 다 남는다."""
        calls = []

        def stop(argv):
            calls.append(("scan", argv))
            sys.exit("data/search/sources.yaml 이 없습니다.")

        saved = weekly.scan.main, weekly.alive.main, weekly.tracker.main
        weekly.scan.main = stop
        weekly.alive.main = lambda argv: (calls.append(("alive", argv)), print("── 마감 확인"))
        weekly.tracker.main = lambda argv: (calls.append(("tracker", argv)), print("## 공고 현황"))
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(weekly.main(["--since", "2026-10-01"]), 0)
        finally:
            weekly.scan.main, weekly.alive.main, weekly.tracker.main = saved
        self.assertEqual(calls, [("scan", []), ("alive", ["--write"]), ("tracker", ["report", "--since", "2026-10-01"])])
        text = K.read_text(os.path.join(K.P["reports"], f"{K.TODAY}.md"))
        for s in ("sources.yaml 이 없습니다", "── 마감 확인", "## 공고 현황"):
            self.assertIn(s, text)


if __name__ == "__main__":
    unittest.main()
