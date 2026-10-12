# -*- coding: utf-8 -*-
"""jobkit 공통 함수: 필터, 회사 이름 비교, 지원 현황표·pipeline.md 읽기·쓰기 (스크립트가 제목·표 머리를 글자 그대로 찾는다)."""
import os
import unittest

from support import K


def _write(key, text):
    with open(K.P[key], "w", encoding="utf-8") as f:
        f.write(text)


class Filters(unittest.TestCase):
    def test_title_ok(self):
        tf = {"positive": ["백엔드", "Backend", "word:Go", "SRE"], "negative": ["인턴", "word:QA"]}
        self.assertIsNone(K.title_ok("백엔드 개발자", tf))
        self.assertIsNone(K.title_ok("Go Developer", tf))
        self.assertIsNone(K.title_ok("Senior SRE", tf))
        self.assertEqual(K.title_ok("Google Ads 운영", tf), "skipped_title")      # word: 는 단어 단위
        self.assertEqual(K.title_ok("SREs 담당", tf), "skipped_title")            # 2~3자 영문은 단어 단위
        self.assertEqual(K.title_ok("백엔드 인턴", tf), "skipped_title")           # 제외어가 우선
        self.assertEqual(K.title_ok("QA 백엔드", tf), "skipped_title")
        self.assertIsNone(K.title_ok("아무 제목", {"negative": ["인턴"]}))       # positive 가 없으면 제외어만

    def test_location_check(self):
        lf = {"always_allow": ["재택"], "block": ["부산", "경기"], "allow": ["서울", "판교"]}
        self.assertEqual(K.location_check("서울 강남구", lf), "ok")
        self.assertEqual(K.location_check("부산 해운대구", lf), "block")
        self.assertEqual(K.location_check("경기 성남시 판교", lf), "block")      # block 이 allow 보다 먼저
        self.assertEqual(K.location_check("경기 (재택 가능)", lf), "ok")          # always_allow 가 가장 먼저
        self.assertEqual(K.location_check("", lf), "unknown")

    def test_career_check(self):
        cf = {"exclude_if_max_below": 3, "exclude_if_min_at_least": 10}
        self.assertIsNone(K.career_check((3, 7), cf))
        self.assertEqual(K.career_check((0, 2), cf), "skipped_career")
        self.assertEqual(K.career_check((10, None), cf), "skipped_career")
        self.assertIsNone(K.career_check((5, 0), cf))                            # 최대 0 = 상한 없음
        self.assertIsNone(K.career_check((None, None), cf))                      # 값이 없으면 통과
        self.assertIsNone(K.career_check(("x", 3), cf))

    def test_stack_hint(self):
        self.assertEqual(K.stack_hint("Java 3년 이상 경험이 필요합니다\nKotlin 경험이 있으면 좋아요"), "필수 추정 Java; 우대·언급 Kotlin")
        self.assertEqual(K.stack_hint("Go 또는 Golang 개발 경험 필수"), "필수 추정 Go")
        self.assertEqual(K.stack_hint("C# 과 C++ 사용"), "우대·언급 C#/C++")
        self.assertEqual(K.stack_hint("Django 경험"), "언어 언급 없음")

    def test_html_text(self):
        self.assertEqual(K.html_text("<p>가&amp;나</p><ul><li>하나</li><li>둘</li></ul>"), "가&나\n• 하나\n• 둘")
        self.assertEqual(K.html_text(None), "")


class Companies(unittest.TestCase):
    def setUp(self):
        K._ALIAS = None

    def test_norm_company(self):
        self.assertEqual(K.norm_company("Ganada Lab"), "가나다랩")                  # 별칭 (tests/fixtures/sources.yaml)
        self.assertEqual(K.norm_company("GANADA (가나다랩)"), "가나다랩")
        self.assertEqual(K.norm_company("주식회사 라바소"), "라바소")
        self.assertEqual(K.norm_company("㈜라바소"), "라바소")

    def test_dup_keys(self):
        a = K.dup_keys("가나다랩(Ganada Lab)", "[가나다랩] 백엔드 개발자 채용")
        b = K.dup_keys("GANADA", "백엔드 개발자")
        self.assertTrue(a & b)
        self.assertFalse(K.dup_keys("가나다랩", "백엔드 개발자 (결제팀)") & K.dup_keys("가나다랩", "백엔드 개발자 (검색팀)"))
        self.assertIn(("gn300", "데이터엔지니어"), K.dup_keys("GN300 - 지엔삼백", "데이터 엔지니어"))   # LinkedIn 의 "영문 - 한글" 표기

    def test_company_in(self):
        self.assertEqual(K.company_in("가나다랩 증권", ["가나다랩"]), "가나다랩")
        self.assertIsNone(K.company_in("가나다랩증권", ["가나다랩"], exact=True))

    def test_blacklist(self):
        _write("blacklist", "| 회사 | 날짜 | 이유 |\n|---|---|---|\n| Ganada Lab | 2026-01-01 | 가상 |\n")
        self.assertEqual(K.blacklist_companies(), {"가나다랩"})


class Files(unittest.TestCase):
    TRACKER = ("# 지원 현황\n\n" + K.TRACKER_HEAD + "\n|---|---|---|---|---|---|---|---|---|\n"
               "| 1 | 2026-10-01 | 가나다랩 | 백엔드 개발자 | 4.5 | 지원함 | resume.pdf | a.eval.md | 메모 | 추가 |\n"
               "| 2 | 2026-09-01 | 라바소 | SRE | 3.8 | 평가함 |  |  |  |\n")

    def test_tracker_roundtrip(self):
        _write("tracker", self.TRACKER)
        rows = K.read_tracker()
        self.assertEqual([r["num"] for r in rows], [1, 2])
        self.assertEqual((rows[0]["company"], rows[0]["state"], rows[0]["memo"]), ("가나다랩", "지원함", "메모|추가"))   # 메모 안의 | 는 공백 없이 다시 잇는다
        self.assertEqual(K.tracker_line(rows[1]), "| 2 | 2026-09-01 | 라바소 | SRE | 3.8 | 평가함 |  |  |  |")

    def test_cooldown(self):
        today = K.date.today()
        recent = K.date.fromordinal(today.toordinal() - 10).isoformat()
        old = K.date.fromordinal(today.toordinal() - 400).isoformat()
        _write("tracker", K.TRACKER_HEAD + "\n"
               f"| 1 | {recent} | 가나다랩(Ganada Lab) | 백엔드 | 4.5 | 지원함 |  |  |  |\n"
               f"| 2 | {old} | 라바소 | SRE | 4.0 | 불합격 |  |  |  |\n"
               f"| 3 | {recent} | 다라마 | SRE | 4.0 | 평가함 |  |  |  |\n"
               f"| 4 | {recent} | 마바사 | SRE | 4.0 | 지원함 |  |  | 쿨다운 제외 |\n")
        end = K.date.fromordinal(today.toordinal() - 10 + 180).isoformat()
        self.assertEqual(K.cooldown_companies(180), {"가나다랩": end})

    def test_insert_under(self):
        md = "# 공고함\n\n## 새로 수집 (선별 전)\n\n- [ ] 기존\n\n## 대기\n"
        self.assertIn("## 새로 수집 (선별 전)\n\n- [ ] 새 줄\n\n- [ ] 기존", K.insert_under(md, "## 새로 수집 (선별 전)", ["- [ ] 새 줄"]))
        out = K.insert_under(md, "## 제외", ["- [-] 뺀 줄"], before="## 대기")
        self.assertLess(out.index("## 제외"), out.index("## 대기"))
        self.assertTrue(K.insert_under("# 공고함\n", "## 제외", ["x"]).endswith("## 제외\n\nx\n\n"))

    def test_move_line(self):
        md = ("## 대기\n\n- [ ] https://a.example/1 | 가나다랩 | 백엔드\n- [ ] https://a.example/2 | 라바소 | SRE\n\n"
              "## 지원 완료 — 재지원 쿨다운 (6개월)\n")
        out = K.move_line(md, "https://a.example/1", "## 지원 완료", "지원 2026-10-08")
        self.assertEqual(out.count("https://a.example/1"), 1)
        self.assertIn("(6개월)\n\n- [-] https://a.example/1 | 가나다랩 | 백엔드 | 지원 2026-10-08", out)
        self.assertEqual(K.move_line(md, "https://nope.example", "## 지원 완료", "x"), md)

    def test_pipeline_keys_and_urls(self):
        _write("pipeline", "## 대기\n\n- [ ] https://a.example/1 | Ganada Lab | 백엔드 개발자 채용 | 4.5\n메모 https://b.example/x)\n")
        self.assertIn(("가나다랩", "백엔드개발자"), K.pipeline_keys())
        self.assertEqual(K.pipeline_urls(), {"https://a.example/1", "https://b.example/x"})

    def test_history_roundtrip(self):
        if os.path.exists(K.P["history"]):
            os.remove(K.P["history"])
        K.append_history([{"url": "https://a.example/1", "title": "탭\t있는\n제목", "company": "가나다랩"}])
        K.append_history([{"url": "https://a.example/2"}])
        rows = K.read_history()
        self.assertEqual([r["url"] for r in rows], ["https://a.example/1", "https://a.example/2"])
        self.assertEqual(rows[0]["title"], "탭 있는 제목")
        self.assertEqual(set(rows[1]), set(K.HISTORY_COLS))


class Http(unittest.TestCase):
    def test_site(self):
        self.assertEqual(K.site("a.career.greetinghr.com"), "greetinghr.com")
        self.assertEqual(K.site("jumpit.saramin.co.kr"), "saramin.co.kr")
        self.assertEqual(K.site("www.wanted.co.kr:443"), "wanted.co.kr")
        self.assertEqual(K.site("toss.im"), "toss.im")

    def test_spacing_per_site(self):
        """같은 사이트는 앞 요청이 끝난 뒤 delay 만큼 쉬고, 다른 사이트는 기다리지 않는다."""
        import threading
        import time
        starts, ends = {}, {}

        class Resp:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return b""

        class Opener:
            def open(self, req, timeout):
                starts[req.full_url] = time.time()
                time.sleep(0.05)
                ends[req.full_url] = time.time()
                return Resp()

        saved, K._OPENER = K._OPENER, Opener()
        try:
            urls = ["https://a.spacing.test/1", "https://b.spacing.test/2", "https://other.test/3"]
            ts = [threading.Thread(target=K.http_get, args=(u,), kwargs=dict(delay=0.3)) for u in urls]
            for t in ts:
                t.start()
            for t in ts:
                t.join()
        finally:
            K._OPENER = saved
        first, second = sorted(urls[:2], key=starts.get)
        self.assertGreaterEqual(starts[second] - ends[first], 0.29)
        self.assertLess(starts[urls[2]], starts[second])


if __name__ == "__main__":
    unittest.main()
