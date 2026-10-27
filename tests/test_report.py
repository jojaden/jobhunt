# -*- coding: utf-8 -*-
"""report_html: 직접 확인한 곳에는 스크립트가 수집하지 못하는 채널만 나온다. 준비 자료(prep_page)가 있는 공고 줄에 그 쪽 링크가 붙는다."""
import os
import tempfile
import unittest

import yaml

from support import K

import prep_page
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


PREP = """
posting: {company: 가나다랩, title: 서버 개발자, url: "https://www.linkedin.com/jobs/view/server-at-ganadalab-4100000001"}
updated: 2026-10-20
prepare:
  - {item: 멱등 키 설명 연습, priority: 높음, done: false}
  - {item: 코딩테스트 5문제, priority: 보통, done: true}
questions:
  - {q: "<script>같은 요청이 두 번 오면?</script>", from: 이력서, follow: ["유니크 제약과 차이는?"]}
company:
  numbers:
    - {label: 국민연금 가입자, value: 50명, source: 1}
  finance:
    - {year: 2025, revenue: 120, operating_profit: 18, source: 1}
    - {year: 2024, revenue: 100, operating_profit: -5, source: 1}
sources:
  - {id: 1, title: 원티드 회사 정보, url: "https://example.com/c", read: 2026-10-20}
"""


class Prep(unittest.TestCase):
    def setUp(self):
        os.makedirs(K.P["postings"], exist_ok=True)
        self.path = os.path.join(K.P["postings"], "2026-10-20_가나다랩_서버.prep.yaml")
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(PREP)

    def tearDown(self):
        os.remove(self.path)

    def test_row_link(self):
        # LinkedIn 은 같은 공고의 제목 조각을 바꾼다: 대기함 주소와 준비 자료 주소가 달라도 공고 번호로 잇는다
        row = dict(url="https://kr.linkedin.com/jobs/view/backend-at-ganadalab-4100000001", company="가나다랩", title="서버")
        other = dict(url="https://example.com/jobs/9", company="다라마", title="백엔드")
        data = dict(rows=[row, other], apps=[])
        report_html.attach(data, prep_page.index(K.P["postings"]).values())
        self.assertEqual(row["prep"]["left"], 1)
        self.assertTrue(row["prep"]["href"].startswith("prep/") and row["prep"]["href"].endswith(".html"))
        self.assertIsNone(other["prep"])
        self.assertIn('href="prep/', report_html._prep_link(row))

    def test_page(self):
        d = prep_page.load(self.path)
        self.assertEqual(prep_page.problems(d), [])
        with tempfile.TemporaryDirectory() as tmp:
            [path] = prep_page.write_pages([d], tmp, back="postings.html")
            self.assertEqual(os.path.basename(path), prep_page.slug(d["posting"]["url"]) + ".html")
            page = open(path, encoding="utf-8").read()
        self.assertTrue(page.startswith("<!doctype html>"))
        self.assertIn('href="../postings.html"', page)
        self.assertNotIn("<script>같은", page)          # 글은 모두 이스케이프
        self.assertNotIn(K.P["postings"], page)          # 로컬 경로는 쪽에 싣지 않는다

    def test_finance(self):
        rows = prep_page.finance_rows(prep_page.load(self.path)["company"]["finance"])
        self.assertEqual([r["year"] for r in rows], [2024, 2025])
        self.assertEqual(rows[0]["margin"], -5.0)
        self.assertIsNone(rows[0]["yoy"])
        self.assertEqual((rows[1]["margin"], rows[1]["yoy"]), (15.0, 20.0))
        # 빠진 해를 건너뛴 증가율은 전년 대비가 아니다
        gap = prep_page.finance_rows([{"year": 2023, "revenue": 100}, {"year": 2025, "revenue": 200}])
        self.assertIsNone(gap[1]["yoy"])

    def test_tracker_url(self):
        # 주소를 직접 받아 평가한 공고는 대기함에 없다: 대기함 줄 → 평가 파일 → 메모 순서로 찾는다
        a = dict(num=7, eval="", memo="근무지 서울 · https://example.com/jobs/7")
        self.assertEqual(report_html._tracker_url(a, ""), "https://example.com/jobs/7")
        self.assertEqual(report_html._tracker_url(a, "- [ ] #007 | https://example.com/jobs/70 | 가나다랩"),
                         "https://example.com/jobs/70")
        os.makedirs(os.path.dirname(K.P["tracker"]), exist_ok=True)
        ev = os.path.join(os.path.dirname(K.P["tracker"]), "eval7.md")
        with open(ev, "w", encoding="utf-8") as f:
            f.write("# 가나다랩\n**URL:** https://example.com/jobs/77\n")
        self.addCleanup(os.remove, ev)
        a["eval"] = "[평가](eval7.md)"
        self.assertEqual(report_html._tracker_url(a, ""), "https://example.com/jobs/77")

    def test_fragment_same_folder(self):
        # 현황표와 뼈대 없는 판을 같은 폴더에 써도 현황표 쪽의 복귀 링크는 현황표 파일을 가리킨다
        name = prep_page.slug(prep_page.example()["posting"]["url"]) + ".html"
        with tempfile.TemporaryDirectory() as tmp:
            report_html.main(["--demo", "--today", "2026-10-27", "-o", os.path.join(tmp, "postings.html"),
                              "--fragment", os.path.join(tmp, "fragment.html")])
            full = open(os.path.join(tmp, "prep", name), encoding="utf-8").read()
            pub = open(os.path.join(tmp, "prep-publish", name), encoding="utf-8").read()
        self.assertIn('href="../postings.html"', full)
        self.assertIn('href="../"', pub)

    def test_problems(self):
        d = prep_page.load(self.path)
        d["company"]["leaders"] = [{"name": "김가나", "note": "창업자", "결제 출신": None, "source": 7}]
        msgs = prep_page.problems(d)
        self.assertTrue(any("결제 출신" in m and "따옴표" in m for m in msgs))
        self.assertTrue(any("source 7" in m for m in msgs))

    def test_example(self):
        """견본 준비 자료(examples/prep.example.yaml)는 문제 없이 읽힌다."""
        self.assertEqual(prep_page.problems(prep_page.example()), [])


if __name__ == "__main__":
    unittest.main()
