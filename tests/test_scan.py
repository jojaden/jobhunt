# -*- coding: utf-8 -*-
"""scan.py --add: 손으로 찾은 공고도 중복 확인과 필터(제목 필터 빼고)를 거쳐 기록된다."""
import contextlib
import io
import os
import unittest
from types import SimpleNamespace

import yaml

from support import TMP, K

import scan


class Add(unittest.TestCase):
    def setUp(self):
        with open(K.P["sources"], encoding="utf-8") as f:
            self.sources = f.read()
        with open(K.P["sources"], "a", encoding="utf-8") as f:
            f.write("title_filter: {positive: [백엔드, SRE], negative: [인턴]}\nlocation_filter: {allow: [서울], block: [부산]}\n")
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
                dict(url="https://a.example/busan", company="자차카", title="백엔드 개발자", source="jobkorea", location="부산 해운대구"),
                dict(url="https://a.example/web", company="하하하", title="백엔드 인턴 아닌 웹 애플리케이션 엔지니어", source="jobkorea"),
                dict(url="https://a.example/ok", company="타파하", title="SRE 엔지니어", source="firecrawl:타파하",
                     location="서울 강남구", career=[3, 7], closes_at="2026-12-31", text="자격요건\n- Go 3년 이상"),
            ], f, allow_unicode=True)
        self.assertEqual(scan.main(["--add", path]), 0)
        hist = {r["url"]: r["status"] for r in K.read_history()}
        # 이미 대기에 있는 공고는 다시 기록하지 않는다. 제목 필터(인턴 제외, 양성어 없음)는 걸지 않는다
        self.assertEqual(hist, {"https://a.example/busan": "skipped_location", "https://a.example/web": "added", "https://a.example/ok": "added"})
        md = K.read_text(K.P["pipeline"])
        line = next(l for l in md.split("\n") if "a.example/ok" in l)
        self.assertIn("| 타파하 | SRE 엔지니어 | 서울 강남구 | 선별 전 | firecrawl:타파하 · ", line)
        body = os.path.join(K.P["inbox"], os.path.basename(line.split("본문: ")[1]))
        self.assertIn("- Go 3년 이상", K.read_text(body))
        self.assertNotIn("busan", md)

    def test_near_flag(self):
        """다른 사이트의 비슷한 공고는 거르지 않고 줄과 본문에 표시한다. "(주)" 만 같은 다른 회사는 표시도 안 한다 (#56)."""
        with open(K.P["pipeline"], "a", encoding="utf-8") as f:
            f.write("- [ ] https://b.example/1 | 사아자랩 | [경력] 백엔드 엔지니어 (결제) | 3.8\n"
                    "- [ ] https://b.example/2 | (주)다라테크 | 백엔드 개발자 채용 | 3.8\n")
        path = os.path.join(TMP, "found.yaml")
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump([dict(url="https://c.example/1", company="사아자랩(Saaja)", title="백엔드 엔지니어 (결제)", source="jobkorea"),
                            dict(url="https://c.example/2", company="(주)마바소프트", title="백엔드 개발자 채용", source="jobkorea")],
                           f, allow_unicode=True)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(scan.main(["--add", path]), 0)
        lines = {l.split(" | ")[0][6:]: l for l in K.read_text(K.P["pipeline"]).split("\n") if "c.example" in l}
        self.assertIn("[같은 공고일 수 있음]", lines["https://c.example/1"])
        self.assertNotIn("b.example", lines["https://c.example/1"])          # 다른 줄 URL 은 본문에만
        body = os.path.join(K.P["inbox"], os.path.basename(lines["https://c.example/1"].split("본문: ")[1]))
        self.assertIn("- 같은 공고일 수 있음: https://b.example/1 (사아자랩 / [경력] 백엔드 엔지니어 (결제))", K.read_text(body))
        self.assertNotIn("같은 공고일 수 있음", lines["https://c.example/2"])

    def test_recheck_dups(self):
        """예전 버전이 "(주)" 로 잘못 거른 skipped_dup 줄만 지운다. 진짜 중복은 남긴다."""
        K.append_history([
            dict(url="https://d.example/1", company="(주)다라테크", title="백엔드 개발자 채용", status="added"),
            dict(url="https://d.example/2", company="(주)마바소프트", title="백엔드 개발자 채용", status="skipped_dup"),
            dict(url="https://d.example/3", company="바사아", title="[바사아] 백엔드", status="skipped_dup"),   # 대기의 바사아 / 백엔드
            dict(url="https://d.example/4", company="다라테크", title="백엔드 개발자", status="skipped_dup"),   # 1 번과 같은 공고
        ])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(scan.main(["--recheck-dups", "--dry-run"]), 0)
            self.assertEqual(len(K.read_history()), 4)
            self.assertEqual(scan.main(["--recheck-dups"]), 0)
        self.assertEqual([r["url"] for r in K.read_history()], ["https://d.example/1", "https://d.example/3", "https://d.example/4"])


class Report(unittest.TestCase):
    def test_partial_marked(self):
        """출처가 일부만 받았으면(Partial) 요약 줄에 이유를 남긴다."""
        mod = SimpleNamespace(__name__="fake", collect=lambda cfg: K.Partial([], "요청 제한(429)으로 못 받음: 'x' 2쪽부터"),
                              detail=lambda j: "")
        saved, scan.plan = scan.plan, lambda sources, only: ([("가짜", mod, {})], [])
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                scan.main(["--dry-run", "--no-detail"])
        finally:
            scan.plan = saved
        self.assertIn("가짜                     받음    0 · 새 공고 0 · ⚠ 일부만 — 요청 제한(429)으로 못 받음: 'x' 2쪽부터", out.getvalue())


if __name__ == "__main__":
    unittest.main()
