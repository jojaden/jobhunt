# -*- coding: utf-8 -*-
"""company: 원티드 회사 정보 표 → 준비 자료 YAML. 응답은 실제 구조를 따른 가상 회사다 (2026-10-27 실측 구조)."""
import contextlib
import io
import unittest

import yaml

from support import K, replay

import company
import prep_page

BASE = "https://www.wanted.co.kr"


def _row(k, v, unit=""):
    tail = f'<div class="CompanyInfoTable_definition__trailingText__x1">{unit}</div>' if unit else ""
    return (f'<dl class="CompanyInfoTable_definition__a1"><dt class="CompanyInfoTable_definition__dt__b2">{k}</dt>'
            f'<dd class="CompanyInfoTable_definition__dd__c3">{v}{tail}</dd></dl>')


PAGE = ("<html><head><title>가나다랩(Ganada) 기업정보 - 채용 3건, 평균연봉 6,100만원, 인원 80명 | 원티드</title></head><body>"
        '<section><h2>기업 정보</h2><div class="CompanyInfoTable_wrapper__z">'
        + _row("연혁", '9<!-- -->년 (<time dateTime="2017">2017</time>년 설립)')
        + _row("매출액", "120억 5,000만", "원") + _row("평균연봉", "6,100", "만원") + _row("대표자명", "김가나")
        + _row("고용보험 가입 사원수", "70", "명") + _row("국민연금 가입 사원수", "80", "명") + _row("퇴사/입사 (1년)", "-")
        + "</div></section></body></html>")
COMPANY = f"{BASE}/company/900"
SEARCH = f"{BASE}/api/chaos/search/v1/autocomplete?query="


class CompanyId(unittest.TestCase):
    def test_company_url(self):
        with replay({}):                                  # 요청 없이 주소에서 번호를 읽는다
            self.assertEqual(company.company_id(COMPANY + "?tab=info"), 900)

    def test_posting_url(self):
        with replay({f"{BASE}/api/v4/jobs/5100": {"json": {"job": {"id": 5100, "company": {"id": 900, "name": "가나다랩"}}}}}):
            self.assertEqual(company.company_id(f"{BASE}/wd/5100"), 900)

    def test_name(self):
        res = {SEARCH + "%EB%8B%A4%EB%9D%BC": {"json": {"companies": [
            {"id": 901, "name": "다라마페이"}, {"id": 902, "name": "가나다랩(다라,Dara)"}]}}}
        with replay(res):
            self.assertEqual(company.company_id("다라"), 902)    # 괄호 안 서비스 이름이 정확히 같은 회사

    def test_ambiguous_and_missing(self):
        res = {SEARCH + "%EA%B0%80%EB%82%98": {"json": {"companies": [{"id": 901, "name": "가나페이"}, {"id": 903, "name": "가나랩"}]}},
               SEARCH + "%EC%97%86%EC%9D%8C": {"json": {"companies": []}}}
        with replay(res):
            with self.assertRaises(company.Ambiguous):
                company.company_id("가나")
            with self.assertRaises(LookupError):
                company.company_id("없음")

    def test_not_wanted(self):
        with self.assertRaises(ValueError):
            company.company_id("https://example.com/jobs/1")

    def test_shape_change(self):
        with replay({f"{BASE}/api/v4/jobs/5101": {"json": {"job": {"id": 5101}}},
                     SEARCH + "%EA%B0%80": {"json": {"keywords": []}}}):
            with self.assertRaises(K.ShapeError):
                company.company_id(f"{BASE}/wd/5101")
            with self.assertRaises(K.ShapeError):
                company.company_id("가")


class Info(unittest.TestCase):
    def test_table(self):
        with replay({COMPANY: {"html": PAGE}}):
            name, table = company.fetch(900)
        self.assertEqual(name, "가나다랩(Ganada)")
        self.assertEqual(table["평균연봉"], "6,100만원")
        self.assertEqual(table["연혁"], "9년 (2017년 설립)")
        self.assertNotIn("퇴사/입사 (1년)", table)            # '-' 는 값이 없는 것

    def test_no_table(self):
        with replay({COMPANY: {"html": "<html><body><h2>기업 정보</h2></body></html>"}}):
            with self.assertRaises(K.ShapeError):
                company.fetch(900)

    def test_prep_yaml(self):
        """낸 YAML 은 준비 자료에 그대로 합쳐지고, 준비 쪽 검사에 걸리지 않는다."""
        with replay({COMPANY: {"html": PAGE}}):
            name, table = company.fetch(900)
        d = yaml.safe_load(company.dump(company.to_prep(900, name, table, 4, "2026-10-27")))
        nums = {n["label"]: n for n in d["company"]["numbers"]}
        self.assertEqual(nums["국민연금 가입자"]["value"], "80명")
        self.assertIn("상한", nums["평균연봉 (국민연금 기반 추정)"]["note"])
        self.assertEqual(nums["최근 1년 퇴사 · 입사"]["value"], "확인 못 함")
        self.assertEqual(d["company"]["leaders"], [{"name": "김가나", "role": "대표자", "source": 4}])
        self.assertEqual(d["sources"][0]["url"], COMPANY)
        prep = dict(posting=dict(company="가나다랩", url="https://example.com/jobs/1"), **d)
        self.assertEqual(prep_page.problems(prep), [])

    def test_rate_limit(self):
        # 회사 쪽뿐 아니라 공고 상세·회사 검색의 429 도 응답 형식 변경이 아니라 요청 제한으로 알린다
        for query, res in [(COMPANY, {COMPANY: {"status": 429}}),
                           (f"{BASE}/wd/5102", {f"{BASE}/api/v4/jobs/5102": {"status": 429}}),
                           ("가나다", {SEARCH + "%EA%B0%80%EB%82%98%EB%8B%A4": {"status": 429}})]:
            err = io.StringIO()
            with self.subTest(query=query), replay(res), contextlib.redirect_stderr(err):
                self.assertEqual(company.main([query]), 1)
                self.assertIn("요청 제한", err.getvalue())
                self.assertNotIn("응답 형식 변경", err.getvalue())


if __name__ == "__main__":
    unittest.main()
