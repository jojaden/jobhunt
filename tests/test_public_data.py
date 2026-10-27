# -*- coding: utf-8 -*-
"""국민연금 가입 사업장(nps)·OpenDART(dart)·API 키(keys)와 jobhunt company 의 키 연동. 응답은 명세의 구조를 따른 가상 회사다."""
import contextlib
import io
import json
import os
import stat
import urllib.parse
import zipfile
from datetime import date
from unittest import TestCase, main, mock

import yaml

from support import K

import company
import dart
import keys
import nps
import prep_page

NKEY, DKEY = "nps+key/가짜==", "d" * 40
WANTED = "https://www.wanted.co.kr/company/900"
PAGE = ("<html><head><title>가나다랩(Ganada) 기업정보 | 원티드</title></head><body>"
        "<dl><dt>매출액</dt><dd>120억</dd></dl><dl><dt>평균연봉</dt><dd>5,000만원</dd></dl>"
        "<dl><dt>대표자명</dt><dd>김가나</dd></dl><dl><dt>국민연금 가입 사원수</dt><dd>79명</dd></dl></body></html>")


class Api:
    """주소 경로 끝 + 쿼리 일부 → (상태, 본문). 맞는 게 없으면 실패시킨다 (네트워크 없음)."""

    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def __call__(self, url, accept="application/json", delay=1.0, timeout=20, headers=None, data=None):
        u = urllib.parse.urlsplit(url)
        q = dict(urllib.parse.parse_qsl(u.query))
        self.calls.append((u.path, q))
        for path, sub, (status, body) in self.routes:
            if u.path.endswith(path) and all(q.get(k) == v for k, v in sub.items()):
                return status, body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)
        raise AssertionError(f"고정 응답 없는 요청: {u.path} {q}")


@contextlib.contextmanager
def api(routes):
    fake = Api(routes)
    with mock.patch.object(K, "http_get", fake):
        yield fake


def nps_ok(items):
    return 200, {"response": {"header": {"resultCode": "00", "resultMsg": "NORMAL_CODE"},
                              "body": {"items": {"item": items}, "pageNo": 1, "numOfRows": 100, "totalCount": len(items)}}}


NPS_EMPTY = (200, {"response": {"header": {"resultCode": "00"}, "body": {"items": "", "totalCount": 0}}})
MONTHS = nps.last_months("202609")
ROWS = [dict(dataCrtYm=m, seq=str(100 + i), wkplNm="주식회사 가나다랩", wkplRoadNmDtlAddr="서울특별시 강남구 테헤란로",
             wkplJnngStcd="1", bzowrRgstNo="123456****") for i, m in enumerate(MONTHS)]
OTHER = dict(ROWS[-1], wkplNm="주식회사 가나다랩스", seq="900")         # 이름이 비슷한 다른 회사


def nps_routes():
    # 80명, 고지액 = 80 × 월 500만 원 × 9.5% (2026년 보험료율) → 연 6,000만 원
    return [("getBassInfoSearchV2", {"wkplNm": "가나다랩"}, NPS_EMPTY),
            ("getBassInfoSearchV2", {"wkplNm": "주식회사 가나다랩"}, nps_ok(ROWS + [OTHER])),
            ("getDetailInfoSearchV2", {"seq": "111"}, nps_ok([{"jnngpCnt": "80", "crrmmNtcAmt": "38000000"}])),
            ("getDetailInfoSearchV2", {"seq": "100"}, nps_ok([{"jnngpCnt": 70, "crrmmNtcAmt": "30000000"}])),
            ("getPdAcctoSttusInfoSearchV2", {}, nps_ok([{"nwAcqzrCnt": "3", "lssJnngpCnt": "2"}]))]


class Nps(TestCase):
    def test_rate_and_cap(self):
        self.assertEqual([nps.rate(y) for y in ("202512", "202601", "202701", "203301", "204001")], [0.09, 0.095, 0.1, 0.13, 0.13])
        self.assertEqual((nps.cap("202606"), nps.cap("202607")), (6_370_000, 6_590_000))
        self.assertEqual(MONTHS[0], "202510")

    def test_numbers(self):
        with api(nps_routes()) as fake:
            src, rows = nps.numbers(NKEY, "가나다랩", 5, "2026-10-27")
        by = {r["label"]: r for r in rows}
        self.assertEqual(by["국민연금 가입자"]["value"], "80명 (2025-10 70명)")
        self.assertEqual(by["평균연봉 (국민연금 고지액 기반 추정)"]["value"], "약 6,000만원")
        self.assertIn("9.5%", by["평균연봉 (국민연금 고지액 기반 추정)"]["note"])
        self.assertIn("6,590,000", by["평균연봉 (국민연금 고지액 기반 추정)"]["note"])
        self.assertEqual(by["최근 1년 입사 · 퇴사"]["value"], "입사 36명 · 퇴사 24명")
        self.assertEqual((src["id"], src["read"]), (5, "2026-10-27"))
        self.assertIn("주식회사 가나다랩,", src["title"])
        self.assertEqual(fake.calls[0][1]["serviceKey"], NKEY)        # 키는 인코딩해 보내고 받는 쪽에서 원래 값이 된다

    def test_same_name_workplaces(self):
        # 사업자등록번호가 다른 같은 이름 사업장은 고르게 하고, 주소 일부로 좁힌다
        two = ROWS[-1:] + [dict(ROWS[-1], seq="777", bzowrRgstNo="654321****", wkplRoadNmDtlAddr="부산광역시 해운대구 센텀로")]
        with api([("getBassInfoSearchV2", {}, nps_ok(two))]):
            with self.assertRaises(nps.Ambiguous):
                nps.workplace(NKEY, "주식회사 가나다랩")
            self.assertEqual(nps.workplace(NKEY, "주식회사 가나다랩", addr="해운대")[2][0]["seq"], "777")

    def test_moved_workplace_is_one(self):
        # 이사한 회사: 달마다 주소가 달라도 같은 사업장이고, 최근 주소를 쓴다 (2026-10-27 실제 응답에서 본 경우)
        moved = [dict(r, wkplRoadNmDtlAddr="서울특별시 서초구 사평대로") if r["dataCrtYm"] < "202512" else r for r in ROWS]
        with api([("getBassInfoSearchV2", {}, nps_ok(moved))]):
            name, addr, months = nps.workplace(NKEY, "가나다랩")
        self.assertEqual((name, addr, len(months)), ("주식회사 가나다랩", "서울특별시 강남구 테헤란로", 12))

    def test_errors_never_show_key(self):
        cases = [((200, "<OpenAPI_ServiceResponse><cmmMsgHeader><returnReasonCode>30</returnReasonCode></cmmMsgHeader>"
                        "</OpenAPI_ServiceResponse>"), RuntimeError, "활용신청"),
                 ((401, ""), RuntimeError, "활용신청"),
                 ((429, ""), RuntimeError, "요청 제한"),
                 ((200, {"response": {"header": {"resultCode": "22"}}}), RuntimeError, "요청 제한"),
                 ((200, {"response": {"body": {}}}), K.ShapeError, "header"),
                 ((200, "<html>점검</html>"), K.ShapeError, "JSON")]
        for resp, exc, word in cases:
            with self.subTest(resp=resp), api([("getBassInfoSearchV2", {}, resp)]):
                with self.assertRaises(exc) as cm:
                    nps.ping(NKEY)
                self.assertIn(word, str(cm.exception))
                self.assertNotIn(NKEY, str(cm.exception))

    def test_not_found(self):
        with api([("getBassInfoSearchV2", {}, (200, {"response": {"header": {"resultCode": "03"}}}))]):
            with self.assertRaises(LookupError):
                nps.workplace(NKEY, "없는회사")


def corp_zip(entries):
    xml = "<result>" + "".join(f"<list><corp_code>{c}</corp_code><corp_name>{n}</corp_name><stock_code>{s}</stock_code>"
                                f"<modify_date>20260101</modify_date></list>" for c, n, s in entries) + "</result>"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("CORPCODE.xml", xml)
    return buf.getvalue()


def te(code, name, *vals):
    cells = "".join(f'<TE ALIGN="RIGHT" ACODE="{code}">{v}</TE>' for v in vals)
    return f'<TR><TE ACODE="{code}" ALEVEL="0">{name}</TE>{cells}</TR>'


def audit_xml(year, rev, op, unit="원", code_rev="12100000010000", code_op="12500000010000", op_name="Ⅲ. 영업이익(손실)"):
    """감사보고서 원문: 손익계산서는 TABLE-GROUP 안 표, 줄마다 표준계정코드(ACODE), 금액은 [소계, 합계] × 당기·전기."""
    period = "".join(f"<TR><TD>제{n}기 {y}년 1월 1일부터 {y}년 12월 31일까지</TD></TR>" for n, y in ((9, year), (8, year - 1)))
    return ('<?xml version="1.0" encoding="utf-8"?><DOCUMENT><BODY>'
            '<TABLE-GROUP ACLASS="PBS-2:A"><TABLE><TR><TD>재 무 상 태 표</TD></TR></TABLE></TABLE-GROUP>'
            f'<P>손 익 계 산 서</P><TABLE-GROUP ACLASS="PIS-2:A"><TABLE ACLASS="EXTRACTION">{period}'
            f'<TR><TD>주식회사 가나다랩</TD><TD>(단위 : {unit})</TD></TR></TABLE><TABLE ACLASS="FINANCE">'
            '<TR><TH>과 목</TH><TH>제 9(당) 기</TH><TH>제 8(전) 기</TH></TR>'
            + te(code_rev, "Ⅰ. 영업수익(주석13)", "", rev[0], "", rev[1])
            + te("99999999999999", "광고수익", rev[0], "", rev[1], "")
            + te(code_op, op_name, "", op[0], "", op[1])
            + "</TABLE></TABLE-GROUP><TABLE-GROUP ACLASS=\"INS_NUT\"><P>영업이익은 주석 참조</P></TABLE-GROUP></BODY></DOCUMENT>")


def doc_zip(xml):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("20260401000000_00760.xml", xml)
    return buf.getvalue()


CORPS = [("00000001", "가나다랩", " "), ("00000002", "가나다랩", " "), ("00000003", "라마바", "123456")]


def dart_ok(**kw):
    return 200, dict(status="000", message="정상", **kw)


def info(code, ceo):
    return dart_ok(corp_name="가나다랩", ceo_nm=ceo, bizr_no="1234567890", corp_cls="E", adres="서울특별시 강남구")


NODATA = (200, {"status": "013", "message": "조회된 데이타가 없습니다."})


def acnt(fs, name, a, b, c):
    return dict(rcept_no="20260310000001", fs_div=fs, account_nm=name, thstrm_amount=a, frmtrm_amount=b, bfefrmtrm_amount=c)


class DartList(TestCase):
    """고유번호 목록(zip) 받기를 가상 목록으로 바꾸고, 테스트마다 캐시(support 가 임시 폴더로 돌려 둠)를 비운다."""

    docs: dict = {}

    def setUp(self):
        self.dl = mock.patch.object(dart, "_download", side_effect=self.fake_download)
        self.download = self.dl.start()
        self.corp = corp_zip(CORPS)

    def fake_download(self, url):
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
        return self.docs[q["rcept_no"]] if "rcept_no" in q else self.corp

    def tearDown(self):
        self.dl.stop()
        if os.path.exists(dart.CACHE):
            os.remove(dart.CACHE)


class Dart(DartList):

    def test_find_by_ceo(self):
        routes = [("company.json", {"corp_code": "00000001"}, info("00000001", "이다라")),
                  ("company.json", {"corp_code": "00000002"}, info("00000002", "김가나"))]
        with api(routes):
            self.assertEqual(dart.find(DKEY, "(주)가나다랩", ceo="김가나")["corp_code"], "00000002")
            with self.assertRaises(dart.Ambiguous):
                dart.find(DKEY, "가나다랩")
            with self.assertRaises(LookupError):
                dart.find(DKEY, "없는회사")
        self.assertEqual(self.download.call_count, 1)            # 고유번호 목록은 캐시에서 다시 읽는다

    def test_finance_listed(self):
        rows = [acnt("CFS", "매출액", "65,500,000,000", "52,000,000,000", "41,000,000,000"),
                acnt("CFS", "영업이익", "6,100,000,000", "2,230,000,000", "-3,500,000,000"),
                acnt("OFS", "매출액", "1", "1", "1")]
        with api([("fnlttSinglAcnt.json", {"bsns_year": "2025"}, dart_ok(list=rows))]):
            rcept, fin = dart.finance(DKEY, "00000003", 2026)
        self.assertEqual(rcept, "20260310000001")
        self.assertEqual(fin, [dict(year=2023, revenue=410, operating_profit=-35), dict(year=2024, revenue=520, operating_profit=22.3),
                               dict(year=2025, revenue=655, operating_profit=61)])

    def test_statement(self):
        fin = dart.statement(audit_xml(2025, ("46,346,472,738", "33,892,942,924"), ("(1,227,993,176)", "18,760,584,894")))
        self.assertEqual(fin, {2025: dict(year=2025, revenue=463.5, operating_profit=-12.3),
                               2024: dict(year=2024, revenue=338.9, operating_profit=187.6)})
        # 코드가 없어도 계정 이름으로, 천원 단위는 원으로 바꿔서
        fin = dart.statement(audit_xml(2025, ("4,634,647", "3,389,294"), ("△122,799", "1,876,058"), unit="천원",
                                       code_rev="99999999999999", code_op="99999999999999", op_name="영업이익(손실)"))
        self.assertEqual(fin[2025], dict(year=2025, revenue=46.3, operating_profit=-1.2))
        # '영업손실' 줄은 손실 금액이 양수로 적힌다
        fin = dart.statement(audit_xml(2025, ("100,000,000", "0"), ("50,000,000", "0"), code_op="9", op_name="영업손실"))
        self.assertEqual(fin[2025]["operating_profit"], -0.5)
        with self.assertRaises(K.ShapeError):
            dart.statement("<DOCUMENT><TABLE-GROUP><TR><TD>재무상태표</TD></TR></TABLE-GROUP></DOCUMENT>")

    def test_unlisted_reads_audit_reports(self):
        audits = [dict(rcept_no=r, report_nm=nm, rcept_dt=dt) for r, nm, dt in
                  [("20260401000000", "감사보고서 (2025.12)", "20260401"), ("20250401000000", "감사보고서 (2024.12)", "20250401"),
                   ("20260401000009", "연결감사보고서 (2025.12)", "20260402"), ("20250601000000", "회계법인사업보고서", "20250601")]]
        self.docs = {"20260401000000": doc_zip(audit_xml(2025, ("65,500,000,000", "52,000,000,000"), ("6,100,000,000", "2,200,000,000"))),
                     "20250401000000": doc_zip(audit_xml(2024, ("51,000,000,000", "41,000,000,000"), ("2,000,000,000", "-3,500,000,000")))}
        routes = [("fnlttSinglAcnt.json", {}, NODATA), ("list.json", {"pblntf_ty": "F"}, dart_ok(list=audits))]
        with api(routes):
            sources, part, notes = dart.to_prep(DKEY, dict(corp_code="00000002", corp_name="(주)가나다랩", ceo_nm="김가나"), 3, date(2026, 10, 27))
        self.assertEqual([s["id"] for s in sources], [3, 4, 5])                 # 연결감사보고서는 빼고 별도 두 개
        self.assertTrue(sources[0]["url"].endswith("textCrpNm=%EA%B0%80%EB%82%98%EB%8B%A4%EB%9E%A9"))   # 법인 표기 뗀 이름
        self.assertTrue(sources[1]["url"].endswith("rcpNo=20260401000000"))
        self.assertEqual(part["finance"], [dict(year=2023, revenue=410, operating_profit=-35, source=5),
                                           dict(year=2024, revenue=520, operating_profit=22, source=4),     # 겹치는 해는 새 보고서
                                           dict(year=2025, revenue=655, operating_profit=61, source=4)])
        self.assertEqual(notes, [])

    def test_unreadable_audit_report(self):
        self.docs = {"20260401000000": doc_zip("<DOCUMENT>스캔본</DOCUMENT>")}
        routes = [("fnlttSinglAcnt.json", {}, NODATA),
                  ("list.json", {}, dart_ok(list=[dict(rcept_no="20260401000000", report_nm="감사보고서 (2025.12)", rcept_dt="20260401")]))]
        with api(routes):
            _, part, notes = dart.to_prep(DKEY, dict(corp_code="00000002", corp_name="가나다랩"), 3, date(2026, 10, 27))
        self.assertNotIn("finance", part)
        self.assertIn("출처 4 의 손익계산서에서 옮겨 적으세요", notes[0])

    def test_key_errors(self):
        self.corp = b'{"status":"010","message":"\\ub4f1\\ub85d\\ub418\\uc9c0 \\uc54a\\uc740 \\ud0a4"}'
        with self.assertRaises(RuntimeError) as cm:
            dart.corp_codes(DKEY)
        self.assertIn("jobhunt keys", str(cm.exception))
        with api([("company.json", {}, (200, {"status": "020", "message": "제한"}))]):
            with self.assertRaises(RuntimeError) as cm:
                dart.ping(DKEY)
        self.assertIn("요청 제한", str(cm.exception))
        self.assertNotIn(DKEY, str(cm.exception))


class Keys(TestCase):
    def tearDown(self):
        if os.path.exists(keys.FILE):                                # support 가 임시 폴더로 돌려 둔 파일
            os.remove(keys.FILE)

    def test_save_and_get(self):
        keys.save("dart", DKEY)
        keys.save("data_go_kr", "abc%2Bdef%3D%3D")             # 포털의 인코딩된 키를 넣어도 원래 값으로
        self.assertEqual(stat.S_IMODE(os.stat(keys.FILE).st_mode), 0o600)
        self.assertEqual((keys.get("dart"), keys.get("data_go_kr")), (DKEY, "abc+def=="))
        with mock.patch.dict(os.environ, {"JOBHUNT_DART_KEY": "env-key"}):
            self.assertEqual(keys.get("dart"), "env-key")            # 환경 변수가 먼저
        self.assertEqual(keys.missing(), [])

    def test_set_from_pipe_and_status(self):
        out = io.StringIO()
        with mock.patch("sys.stdin", io.StringIO(DKEY + "\n")), mock.patch.object(keys, "ping") as ping, \
                contextlib.redirect_stdout(out):
            self.assertEqual(keys.main(["set", "dart"]), 0)
        ping.assert_called_once_with("dart", DKEY)
        self.assertNotIn(DKEY, out.getvalue())
        out = io.StringIO()
        with mock.patch.object(keys, "ping"), contextlib.redirect_stdout(out):
            self.assertEqual(keys.main([]), 1)                       # 공공데이터포털 키가 없다
        self.assertIn("data.go.kr/data/3046071", out.getvalue())
        self.assertIn("✓ OpenDART", out.getvalue())
        self.assertNotIn(DKEY, out.getvalue())


class CompanyWithKeys(DartList):
    def run_main(self, routes, env, argv=("가나다랩",)):
        out, err = io.StringIO(), io.StringIO()
        search = ("autocomplete", {"query": "가나다랩"}, (200, {"companies": [{"id": 900, "name": "가나다랩(Ganada)"}]}))
        with api([search, ("/company/900", {}, (200, PAGE))] + routes), mock.patch.object(keys, "get", lambda n: env.get(n)), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = company.main(list(argv) + ["--source", "4"])
        return code, out.getvalue(), err.getvalue()

    def test_all_keys(self):
        dart_routes = [("company.json", {"corp_code": "00000001"}, info("00000001", "이다라")),
                       ("company.json", {"corp_code": "00000002"}, info("00000002", "김가나")),
                       ("fnlttSinglAcnt.json", {}, NODATA), ("list.json", {}, dart_ok(list=[
                           dict(rcept_no="20260401000000", report_nm="감사보고서 (2025.12)", rcept_dt="20260401")]))]
        self.docs = {"20260401000000": doc_zip(audit_xml(2025, ("65,500,000,000", "52,000,000,000"), ("6,100,000,000", "2,200,000,000")))}
        code, out, err = self.run_main(dart_routes + nps_routes(), {"dart": DKEY, "data_go_kr": NKEY})
        self.assertEqual(code, 0, err)
        d = yaml.safe_load(out)
        self.assertEqual([s["id"] for s in d["sources"]], [4, 5, 6, 7])          # 원티드 · DART 개황 · 감사보고서 · 국민연금
        labels = [n["label"] for n in d["company"]["numbers"]]
        self.assertEqual(labels[:3], ["국민연금 가입자", "평균연봉 (국민연금 고지액 기반 추정)", "최근 1년 입사 · 퇴사"])
        self.assertNotIn("평균연봉 (국민연금 기반 추정)", labels)                   # 원티드의 같은 숫자는 뺀다
        self.assertEqual(d["company"]["leaders"], [{"name": "김가나", "role": "대표자", "source": 5}])
        self.assertEqual([f["year"] for f in d["company"]["finance"]], [2024, 2025])
        self.assertNotIn("매출액 (원티드 표시, 연도 표기 없음)", labels)              # 연도별 매출이 있으면 원티드 매출은 뺀다
        self.assertNotIn("키가 없어", err)
        prep = dict(posting=dict(company="가나다랩", url="https://example.com/jobs/1"), **d)
        self.assertEqual(prep_page.problems(prep), [])

    def test_no_keys(self):
        code, out, err = self.run_main([], {})
        self.assertEqual(code, 0)
        self.assertIn("평균연봉 (국민연금 기반 추정)", out)
        self.assertIn("jobhunt keys", err)

    def test_network_failure_keeps_wanted(self):
        def down(url, **kw):
            if "apis.data.go.kr" in url:
                raise TimeoutError("timed out")
            return fake(url, **kw)
        fake = Api([("autocomplete", {}, (200, {"companies": [{"id": 900, "name": "가나다랩(Ganada)"}]})), ("/company/900", {}, (200, PAGE))])
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(K, "http_get", down), mock.patch.object(keys, "get", lambda n: NKEY if n == "data_go_kr" else None), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(company.main(["가나다랩"]), 0)
        self.assertIn("공공데이터포털 연결 실패 (TimeoutError)", err.getvalue())
        self.assertIn("평균연봉 (국민연금 기반 추정)", out.getvalue())

    def test_key_failure_keeps_wanted(self):
        code, out, err = self.run_main([("getBassInfoSearchV2", {}, (401, ""))], {"data_go_kr": NKEY})
        self.assertEqual(code, 0)
        self.assertIn("평균연봉 (국민연금 기반 추정)", out)
        self.assertIn("활용신청", err)
        self.assertNotIn(NKEY, out + err)


if __name__ == "__main__":
    main()
