# -*- coding: utf-8 -*-
"""score.py: 같은 판정이면 같은 점수. 등급·상한·검토 조정이 references/scoring.md 대로 걸리는지."""
import os
import unittest

import yaml

from support import TMP, K

import score as S

CFG = {"prefer_work": {"payments": ""}, "avoid_work": {"ops_only": ""}, "avoid_cap": 3.4,
       "signals": {"b2c": 0.3, "crunch": -0.2}, "priority_bonus": 0.2}
YES, NO = {"met": "yes"}, {"met": "no"}


def j(**kw):
    out = dict(gates={}, work=[{"fit": "done"}], required=[YES], preferred=[], direction={})
    out.update(kw)
    return out


class Score(unittest.TestCase):
    def check(self, judgment, total, verdict, band=None, caps=()):
        r = S.score(judgment, CFG)
        self.assertEqual((r["total"], r["verdict"]), (total, verdict), r)
        if band:
            self.assertTrue(r["band"].startswith(band), r["band"])
        self.assertEqual([c.split(" → ")[0] for c in r["caps"]], list(caps))
        return r

    def test_gate_and_empty(self):
        r = S.score(j(gates={"location": "fail", "stack": "pass"}), CFG)
        self.assertEqual((r["total"], r["triage"], r["gate"]), (None, "FAIL", ["location"]))
        r = S.score(j(work=[], required=[]), CFG)
        self.assertEqual((r["total"], r["verdict"]), (None, "확인 필요"))

    def test_bands(self):
        self.check(j(preferred=[YES], direction={"primary": "payments"}, signals=["b2c"]), 5.0, "지원 권장", "S 4.9–5.0")
        self.check(j(work=[{"fit": "done"}, {"fit": "adjacent"}], preferred=[dict(YES, key=True, line="핵심"), NO], priority=True),
                   4.6, "지원 권장", "A 4.5–4.8")
        self.check(j(), 4.1, "지원 권장", "B 4.0–4.4: 필수 충족 + 우대 사항 없음")
        self.check(j(preferred=[NO, NO, {"met": "partial"}]), 3.6, "지원 고려", "C 1.0–3.9: 우대 절반 미만")
        self.check(j(work=[{"fit": "new"}, {"fit": "done"}]), 3.5, "지원 고려", "C 1.0–3.9: 주요 업무 2줄 중 1줄이 처음")
        self.check(j(preferred=[dict(NO, key=True, line="쿠버네티스 운영 경험")]), 3.6, "지원 고려", "C 1.0–3.9: 포지션 핵심 우대 못 채움")

    def test_caps(self):
        self.check(j(required=[YES, dict(NO, gap="core")]), 3.4, "보류", "C", ["필수 핵심 빈틈 1개"])
        self.check(j(required=[YES, dict(NO, gap="core", alt=True)]), 3.5, "지원 고려", "C")      # 준하는 경험 인정: 상한 3.6
        self.check(j(required=[dict(NO, gap="core"), dict(NO, gap="core")]), 2.9, "제외", "C", ["필수 핵심 빈틈 2개"])
        self.check(j(work=[{"fit": "new"}]), 3.1, "보류", "C", [])                                # 업무 적합 1.5: 원점수 3.15 가 상한 3.9 아래
        self.check(j(preferred=[YES], domain_new="결제"), 3.9, "지원 고려", "S", ["핵심 도메인 처음 (결제)"])
        self.check(j(direction={"primary": "ops_only"}, signals=["crunch"]), 3.4, "보류", "B", ["주 업무 방향 'ops_only'"])

    def test_review(self):
        r = self.check(j(review={"delta": -2, "why": "가상 사유"}), 3.1, "보류", "B", ["검토 -1.0: 가상 사유"])
        self.assertIn("가상 사유", r["caps"][0])
        self.check(j(review={"delta": 0.5}), 4.4, "지원 권장", "B", ["검토 +0.3: "])             # 올림은 0.3, 등급 상한까지

    def test_yaml_bool_met(self):
        d = yaml.safe_load("work: [{fit: done}]\nrequired: [{met: yes}]\npreferred: [{met: no}, {met: yes}]\n")
        self.check(dict(d, gates={}), 4.1, "지원 권장", "B 4.0–4.4: 필수 충족 + 우대 절반 이상")

    def test_init(self):
        path = os.path.join(TMP, "body.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write("# 가나다랩 — 백엔드 개발자\n\n- URL: https://a.example/1\n\n## 주요업무\n• 결제 API 개발\n• 정산 배치\n\n"
                    "## 자격요건\n- Go 3년 이상\n\n[이렇게 일합니다]\n- 주 1회 회고\n\n우대사항\n1) 쿠버네티스 운영\n")
        out = S.init(path)
        self.assertEqual((out["company"], out["title"], out["url"]), ("가나다랩", "백엔드 개발자", "https://a.example/1"))
        self.assertEqual([x["line"] for x in out["work"]], ["결제 API 개발", "정산 배치"])
        self.assertEqual(out["required"], [{"line": "Go 3년 이상", "met": ""}])
        self.assertEqual(out["preferred"], [{"line": "쿠버네티스 운영", "met": "", "key": False}])

    def test_init_preferred_headings(self):
        """자격요건 낱말을 품은 우대 머리말은 우대로. "더 좋은 …" 같은 문장은 머리말이 아니다."""
        path = os.path.join(TMP, "body2.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write("# 가나다랩 — 서버\n\nQualifications\n- 서버 개발 3년\n\nPreferred Qualifications\n- Kafka 운영\n\n"
                    "이런 분과 함께하고 싶어요\n- 장애 대응 경험\n더 좋은 코드를 함께 고민하는 분\n\n이런 분이면 더 좋아요\n- 결제 도메인\n")
        out = S.init(path)
        self.assertEqual([x["line"] for x in out["required"]], ["서버 개발 3년", "장애 대응 경험", "더 좋은 코드를 함께 고민하는 분"])
        self.assertEqual([x["line"] for x in out["preferred"]], ["Kafka 운영", "결제 도메인"])

    def test_stack_draft(self):
        """사용자 언어에 없는 언어를 꼭 요구할 때만 근거 줄. 열린 목록·대체 허용·사용자 언어 언급·우대 투·기술 나열은 초안 없음."""
        req = lambda *ls: [{"line": x} for x in ls]
        known = ["Go", "Shell"]
        self.assertEqual(S.stack_draft(req("Java/Spring 기반 서버 개발 경험 3년 이상"), known), "Java/Spring 기반 서버 개발 경험 3년 이상")
        self.assertEqual(S.stack_draft(req("NestJS로 서비스를 운영해 보신 분"), known), "NestJS로 서비스를 운영해 보신 분")
        for lines in (("Java, Python 등 하나 이상의 언어로 개발한 경험",),
                      ("Kotlin 또는 Go 로 서버를 개발한 경험",),
                      ("Java/Spring 경험", "Go 언어 사용 경험"),
                      ("Kotlin/Spring 4년 이상 또는 이에 준하는(언어 무관) 역량",),
                      ("Python 경험이 있으면 좋아요",),
                      ("Kotlin, Spring Boot, JPA, gRPC",),
                      ("JavaScript 가 아닌 Go 경험",),
                      ("JAVA 또는 GO 개발 경험",),
                      ("Experience designing scalable distributed systems",),
                      ("Kubernetes node 장애 대응 및 운영 경험",),
                      ("Javadoc 기반 API 문서화 경험",),
                      ("AI guard rails 설계 경험",)):
            self.assertEqual(S.stack_draft(req(*lines), known), "", lines)
        self.assertEqual(S.stack_draft(req("Java 개발 경험"), []), "")     # 사용자 언어를 적지 않았으면 초안 없음
        self.assertEqual(S.stack_draft(req("Go 개발 경험"), ["Java"]), "Go 개발 경험")
        self.assertEqual(S.stack_draft(req("Google Cloud 개발 경험"), ["Java"]), "")   # Go 는 낱말로만
        self.assertEqual(S.stack_draft(req("Node.js 서버 개발 경험"), ["TypeScript"]), "")   # 같은 언어의 다른 이름
        self.assertEqual(S.stack_draft(req("Spring Boot 개발 경험"), ["Java"]), "")

    def test_init_stack_draft(self):
        """targets.yaml gates.stack_languages 가 있으면 init 이 stack 관문 초안과 근거를 채운다."""
        path = os.path.join(TMP, "body3.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write("# 가나다랩 — 서버\n\n## 자격요건\n- Java/Spring 서버 개발 경험 3년 이상\n\n## 우대사항\n- Go 경험\n")
        with open(K.P["targets"], "w", encoding="utf-8") as f:
            f.write("gates:\n  stack_languages: [Go, Shell]\n")
        try:
            out = S.init(path)
        finally:
            os.remove(K.P["targets"])
        self.assertEqual(out["gates"]["stack"], "fail")
        self.assertEqual(out["gate_note"], "자격요건 'Java/Spring 서버 개발 경험 3년 이상' — Go/Shell 없음")
        self.assertIn("draft", out)
        self.assertNotIn("draft", S.init(path))      # 설정이 없으면 초안 없음


class Apply(unittest.TestCase):
    def test_labels(self):
        """선별 전에서 온 공고는 "선별", 대기에 있던 공고를 다시 매기면 "재채점"으로 적는다."""
        for key, text in (("tracker", ""), ("pipeline", "# 공고 대기함\n\n## 새로 수집 (선별 전)\n\n"
                          "- [ ] https://a.example/1 | 바사아 | 백엔드 | 서울 | 선별 전 | 가상\n"
                          "- [ ] https://a.example/2 | 자차카 | SRE | 서울 | 선별 전 | 가상\n\n## 대기\n\n"
                          "- [ ] https://a.example/3 | 타파하 | 백엔드 | 서울 | triage: PASS 3.8/5 | 가상 | 판정: x\n\n"
                          "## 지원 완료 — 재지원 쿨다운 (6개월)\n")):
            with open(K.P[key], "w", encoding="utf-8") as f:
                f.write(text)
        files = []
        for n, gates in ((1, {}), (2, {"location": "fail"}), (3, {"location": "fail"})):
            files.append(os.path.join(TMP, f"apply{n}.yaml"))
            with open(files[-1], "w", encoding="utf-8") as f:
                yaml.safe_dump(j(url=f"https://a.example/{n}", company="가상", title="가상", gates=gates), f, allow_unicode=True)
        S.apply(files)
        md = K.read_text(K.P["pipeline"])
        today = K.TODAY
        self.assertIn(f"triage: PASS 4.1/5 (선별 {today})", md)
        self.assertIn(f"## 제외 (선별 {today})\n\n- [x] https://a.example/2", md)
        self.assertIn(f"## 제외 (재채점 {today})\n\n- [x] https://a.example/3 | 가상 | 가상 | FAIL (재채점 {today}, 이전 PASS 3.8)", md)
        self.assertNotIn("선별 전 | 가상", md)


if __name__ == "__main__":
    unittest.main()
