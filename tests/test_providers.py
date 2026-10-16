# -*- coding: utf-8 -*-
"""공급원(scripts/providers) 고정 응답 테스트. 공급원마다 tests/fixtures/providers/<이름>.json.

고정 응답 파일 형식 (회사·공고 내용은 가상, 구조는 실제 응답과 같게):
  {"cases": [{
     "name": "무엇을 확인하는지",
     "cfg": {...},                              collect 에 넘길 설정 (sources.yaml 항목과 같은 꼴)
     "responses": {"<주소>": {"status": 200, "json"|"next_data"|"html": ...} 또는 [차례로 돌려줄 응답, ...]},
     "jobs": [{"<Job 필드>": 값, "text_has": [...], "text_lacks": [...]}],   collect 결과 (순서·개수까지)
     "error": "ShapeError",                     collect 가 이 오류를 내야 함 (jobs 대신)
     "detail": {"<id>": {"has": [...], "lacks": [...], "job": {detail 뒤 Job 필드}}},
     "alive": [["<공고 주소>", true | false | null]],
     "handles": [["<주소>", true | false]]
  }]}
요청마다 응답을 처음부터 다시 돌려준다 (collect · detail 하나 · alive 하나가 각각 따로).
"""
import dataclasses
import json
import os
import unittest

from support import FIXTURES, K, load_fixture, providers, replay

NAMES = sorted(m.__name__.split(".")[-1] for m in providers.ALL)


def _plain(v):
    return json.loads(json.dumps(v, ensure_ascii=False))       # 튜플 → 목록 (JSON 기대값과 비교)


class ProviderFixtures(unittest.TestCase):
    maxDiff = None

    def test_every_provider_has_fixture(self):
        have = sorted(f[:-5] for f in os.listdir(os.path.join(FIXTURES, "providers")) if f.endswith(".json"))
        self.assertEqual(have, NAMES, "공급원마다 tests/fixtures/providers/<이름>.json 이 있어야 한다")

    def check_job(self, job, want: dict):
        got = _plain(dataclasses.asdict(job))
        for k, v in want.items():
            if k == "text_has":
                for s in v:
                    self.assertIn(s, job.text)
            elif k == "text_lacks":
                for s in v:
                    self.assertNotIn(s, job.text)
            elif k == "extra":
                self.assertEqual({x: got["extra"].get(x) for x in v}, v)
            else:
                self.assertEqual(got[k], v, f"Job.{k}")

    def run_case(self, mod, case: dict):
        res = case["responses"]
        jobs = []
        if "error" in case:
            with replay(res), self.assertRaises(getattr(K, case["error"])):
                mod.collect(case["cfg"])
        elif "jobs" in case:
            with replay(res):
                jobs = mod.collect(case["cfg"])
            self.assertEqual(len(jobs), len(case["jobs"]), [j.id for j in jobs])
            for job, want in zip(jobs, case["jobs"]):
                with self.subTest(job=job.id):
                    self.check_job(job, want)
        for jid, want in (case.get("detail") or {}).items():
            with self.subTest(detail=jid):
                job = next(j for j in jobs if str(j.id) == jid)
                with replay(res):
                    text = mod.detail(job)
                for s in want.get("has", []):
                    self.assertIn(s, text)
                for s in want.get("lacks", []):
                    self.assertNotIn(s, text)
                self.check_job(job, want.get("job") or {})
        for url, want in case.get("alive") or []:
            with self.subTest(alive=url), replay(res):
                self.assertIs(mod.alive(url), want)
        for url, want in case.get("handles") or []:
            with self.subTest(handles=url):
                self.assertIs(mod.handles(url), want)


def _make(name):
    def test(self):
        mod = getattr(providers, name)
        for case in load_fixture("providers", f"{name}.json")["cases"]:
            with self.subTest(case=case["name"]):
                self.run_case(mod, case)
    return test


for _n in NAMES:
    if os.path.exists(os.path.join(FIXTURES, "providers", f"{_n}.json")):
        setattr(ProviderFixtures, f"test_{_n}", _make(_n))


class GreetinghrSeen(unittest.TestCase):
    def test_links_skip_seen(self):
        """홈페이지 링크 방식: cfg 의 seen_urls(scan.py 가 넘김)에 있는 공고는 상세를 받지 않고 건너뛴다."""
        case = next(c for c in load_fixture("providers", "greetinghr.json")["cases"] if "링크" in c["name"])
        seen_url = "https://rabaso.career.greetinghr.com/ko/o/201"
        responses = {u: r for u, r in case["responses"].items() if u != seen_url}
        with replay(responses) as fake:
            jobs = providers.greetinghr.collect(dict(case["cfg"], seen_urls=frozenset([seen_url])))
        self.assertNotIn(seen_url, [u for u, _ in fake.calls])
        self.assertNotIn(seen_url, [j.url for j in jobs])


class LinkedinRateLimit(unittest.TestCase):
    def test_partial_on_429(self):
        """429 가 두 번 나면 그 키워드는 멈추고, 받은 공고와 멈춘 곳을 Partial 로 돌려준다."""
        case = next(c for c in load_fixture("providers", "linkedin.json")["cases"] if c["name"].startswith("검색 카드"))
        first = next(iter(case["responses"]))
        nxt = first.replace("keywords=backend", "keywords=server")
        responses = dict(case["responses"], **{nxt: {"status": 429, "html": ""}})
        saved, providers.linkedin.time.sleep = providers.linkedin.time.sleep, lambda s: None
        try:
            with replay(responses):
                jobs = providers.linkedin.collect(dict(case["cfg"], keywords=["backend", "server"], max_pages=1))
        finally:
            providers.linkedin.time.sleep = saved
        self.assertIsInstance(jobs, K.Partial)
        self.assertEqual(len(jobs), len(case["jobs"]))
        self.assertIn("'server' 1쪽부터", jobs.why)


class RememberCategories(unittest.TestCase):
    URL = "https://career-api.rememberapp.co.kr/job_postings/search"

    def page(self, cats):
        return {"json": {"data": [{"id": 1, "title": "백엔드", "job_category_ids": cats, "organization": {"name": "가나다"}}],
                         "meta": {"total_pages": 1}}}

    def test_categories(self):
        """직군으로 찾는다. 키워드가 있으면 키워드마다 직군과 함께."""
        with replay({self.URL: self.page([310, 312])}) as fake:
            self.assertEqual(len(providers.remember.collect({"job_category_ids": [310, 323]})), 1)
            providers.remember.collect({"job_category_ids": [310], "keywords": ["Go", "서버"]})
        sent = [json.loads(d)["search"] for _, d in fake.calls]
        self.assertEqual(sent, [{"job_category_ids": [310, 323]},
                                {"job_category_ids": [310], "keywords": ["Go"]}, {"job_category_ids": [310], "keywords": ["서버"]}])

    def test_unknown_category(self):
        """모르는 직군 번호는 전체 공고가 나와서, 받은 공고에 그 직군이 없으면 멈춘다."""
        with replay({self.URL: self.page([161])}), self.assertRaisesRegex(ValueError, "직군 번호"):
            providers.remember.collect({"job_category_ids": [99999]})

    def test_partial_on_429(self):
        """429 가 나면 그 검색은 멈추고, 받은 공고와 멈춘 곳을 Partial 로 돌려준다 (형식 변경으로 보고하지 않음)."""
        first = {"json": dict(self.page([310])["json"], meta={"total_pages": 3})}
        with replay({self.URL: [first, {"status": 429, "html": ""}]}):
            jobs = providers.remember.collect({"job_category_ids": [310]})
        self.assertIsInstance(jobs, K.Partial)
        self.assertEqual([j.id for j in jobs], ["1"])
        self.assertIn("'직군' 2쪽부터", jobs.why)


if __name__ == "__main__":
    unittest.main()
