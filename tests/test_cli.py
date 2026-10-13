# -*- coding: utf-8 -*-
"""jobhunt 명령(cli.py)과 자료 위치, 주간 실행(weekly.py)."""
import contextlib
import io
import os
import re
import subprocess
import sys
import unittest

from support import HERE, K

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
