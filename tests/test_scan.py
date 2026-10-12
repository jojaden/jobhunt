# -*- coding: utf-8 -*-
"""scan.py --add: 손으로 찾은 공고도 자동 수집분과 같은 필터·중복 확인을 거쳐 기록된다."""
import os
import unittest

import yaml

from support import TMP, K

import scan


class Add(unittest.TestCase):
    def setUp(self):
        with open(K.P["sources"], encoding="utf-8") as f:
            self.sources = f.read()
        with open(K.P["sources"], "a", encoding="utf-8") as f:
            f.write("title_filter: {positive: [백엔드, SRE], negative: [인턴]}\nlocation_filter: {allow: [서울]}\n")
        for key, text in (("tracker", ""), ("pipeline", "## 대기\n\n- [ ] https://a.example/dup | 바사아 | 백엔드 | 3.8\n")):
            with open(K.P[key], "w", encoding="utf-8") as f:
                f.write(text)
        if os.path.exists(K.P["history"]):
            os.remove(K.P["history"])

    def tearDown(self):
        with open(K.P["sources"], "w", encoding="utf-8") as f:
            f.write(self.sources)

    def test_add(self):
        path = os.path.join(TMP, "found.yaml")
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump([
                dict(url="https://a.example/dup", company="바사아", title="백엔드", source="jobkorea"),
                dict(url="https://a.example/intern", company="자차카", title="백엔드 인턴", source="jobkorea"),
                dict(url="https://a.example/ok", company="타파하", title="SRE 엔지니어", source="firecrawl:타파하",
                     location="서울 강남구", career=[3, 7], closes_at="2026-12-31", text="자격요건\n- Go 3년 이상"),
            ], f, allow_unicode=True)
        self.assertEqual(scan.main(["--add", path]), 0)
        hist = {r["url"]: r["status"] for r in K.read_history()}
        self.assertEqual(hist, {"https://a.example/intern": "skipped_title", "https://a.example/ok": "added"})   # 이미 대기에 있는 공고는 다시 기록하지 않는다
        md = K.read_text(K.P["pipeline"])
        line = next(l for l in md.split("\n") if "a.example/ok" in l)
        self.assertIn("| 타파하 | SRE 엔지니어 | 서울 강남구 | 선별 전 | firecrawl:타파하 · ", line)
        body = os.path.join(K.P["inbox"], os.path.basename(line.split("본문: ")[1]))
        self.assertIn("- Go 3년 이상", K.read_text(body))
        self.assertNotIn("intern", md)


if __name__ == "__main__":
    unittest.main()
