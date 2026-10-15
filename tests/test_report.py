# -*- coding: utf-8 -*-
"""report_html: 직접 확인한 곳에는 스크립트가 수집하지 못하는 채널만 나온다."""
import unittest

import yaml

from support import K

import report_html


class Manual(unittest.TestCase):
    def setUp(self):
        K._ALIAS = None

    def tearDown(self):
        K._ALIAS = None

    def test_auto_collected_hidden(self):
        # 가나다랩은 테스트 sources.yaml 에서 greenhouse 로 자동 수집, Ganada Lab 은 그 별칭
        checks = {name: dict(result="못 봄", checked="2026-10-01") for name in ("가나다랩", "Ganada Lab", "다라마")}
        with open(K.P["checks"], "w", encoding="utf-8") as f:
            yaml.safe_dump(checks, f, allow_unicode=True)
        sites, _ = report_html._manual("")
        names = [s["name"] for s in sites]
        self.assertNotIn("가나다랩", names)
        self.assertNotIn("Ganada Lab", names)
        self.assertIn("다라마", names)


if __name__ == "__main__":
    unittest.main()
