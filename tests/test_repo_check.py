# -*- coding: utf-8 -*-
"""CI 규칙 점검(.github/scripts/repo_check.py): PR 규칙과 릴리스 본문."""
import importlib.util
import json
import os
import re
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("repo_check", os.path.join(os.path.dirname(HERE), ".github", "scripts", "repo_check.py"))
assert _spec and _spec.loader
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)

CHANGELOG = """# 변경 기록

## 다음 버전

- 새 기능 (#1)
- **data/ 이전:** 없음

## v1.2.0 — 2026-10-13

- 지난 기능 (#0)
- **data/ 이전:** 없음

## v1.1.0 — 2026-10-08

- 더 지난 기능
"""


class Pr(unittest.TestCase):
    def test_changelog_needed(self):
        """사용자가 알아챌 파일만 바꾸면 실패, 라벨이 있거나 tests/ 만 바꾸면 통과."""
        errors, _ = rc.pr_problems(["scripts/scan.py", "tests/test_scan.py"], CHANGELOG, False)
        self.assertEqual(len(errors), 1)
        self.assertIn("scripts/scan.py", errors[0])
        self.assertEqual(rc.pr_problems(["scripts/scan.py"], CHANGELOG, True), ([], []))
        self.assertEqual(rc.pr_problems(["tests/test_scan.py", ".github/workflows/test.yml"], CHANGELOG, False), ([], []))
        self.assertEqual(rc.pr_problems(["modes/scan.md", "CHANGELOG.md"], CHANGELOG, False), ([], []))

    def test_data_migration_line(self):
        """CHANGELOG 를 바꿨으면 '다음 버전'에 data/ 이전 줄이 있어야 한다 (다른 버전 절의 줄로는 안 됨)."""
        no_line = CHANGELOG.replace("- 새 기능 (#1)\n- **data/ 이전:** 없음", "- 새 기능 (#1)")
        errors, _ = rc.pr_problems(["CHANGELOG.md"], no_line, False)
        self.assertEqual(len(errors), 1)
        self.assertIn("data/ 이전", errors[0])
        errors, _ = rc.pr_problems(["CHANGELOG.md"], CHANGELOG.replace("## 다음 버전", "## 다음"), False)
        self.assertIn("'## 다음 버전'", errors[0])

    def test_readme_pair(self):
        """README 하나만 바꾸면 경고 (실패 아님)."""
        errors, warnings = rc.pr_problems(["README.md"], CHANGELOG, False)
        self.assertEqual(errors, [])
        self.assertIn("README.en.md", warnings[0])
        self.assertEqual(rc.pr_problems(["README.md", "README.en.md"], CHANGELOG, False), ([], []))


class Release(unittest.TestCase):
    def repo(self, changelog=CHANGELOG, pyproject="1.2.0", plugin="1.2.0"):
        root = tempfile.mkdtemp(prefix="jobhunt-release-")
        self.addCleanup(shutil.rmtree, root, True)
        os.makedirs(os.path.join(root, "plugin", ".claude-plugin"))
        with open(os.path.join(root, "CHANGELOG.md"), "w", encoding="utf-8") as f:
            f.write(changelog)
        with open(os.path.join(root, "pyproject.toml"), "w", encoding="utf-8") as f:
            f.write(f'[project]\nname = "jobhunt"\nversion = "{pyproject}"\n')
        with open(os.path.join(root, "plugin", ".claude-plugin", "plugin.json"), "w", encoding="utf-8") as f:
            json.dump({"name": "jobhunt", "version": plugin}, f)
        return root

    def test_notes(self):
        """태그의 절 본문만 (다음 절은 빼고)."""
        self.assertEqual(rc.release_notes("v1.2.0", self.repo()), "- 지난 기능 (#0)\n- **data/ 이전:** 없음")

    def test_mismatch(self):
        with self.assertRaisesRegex(ValueError, "plugin.json 1.1.0"):
            rc.release_notes("v1.2.0", self.repo(plugin="1.1.0"))
        with self.assertRaisesRegex(ValueError, "절이 없습니다"):
            rc.release_notes("v1.3.0", self.repo(pyproject="1.3.0", plugin="1.3.0"))
        with self.assertRaisesRegex(ValueError, "vX.Y.Z"):
            rc.release_notes("1.2.0", self.repo())
        with self.assertRaisesRegex(ValueError, "비어 있습니다"):
            rc.release_notes("v1.2.0", self.repo(changelog=CHANGELOG.replace("- 지난 기능 (#0)\n- **data/ 이전:** 없음\n", "")))

    def test_this_repo(self):
        """저장소의 지금 버전으로도 본문이 나온다 (릴리스 직전의 실제 형식과 맞는지)."""
        with open(os.path.join(rc.ROOT, "pyproject.toml"), encoding="utf-8") as f:
            version = re.search(r'^version = "([^"]+)"', f.read(), re.M).group(1)
        self.assertTrue(rc.release_notes(f"v{version}").startswith("- "))


if __name__ == "__main__":
    unittest.main()
