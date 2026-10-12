# -*- coding: utf-8 -*-
"""공고 점수 계산 (LLM 호출 없음). 기준은 references/scoring.md.

AI 에이전트(Claude·Codex·Grok 등)는 공고를 한 줄씩 분류만 해서 판정 파일(yaml)을 채우고, 점수는 이 스크립트가 계산한다.
같은 판정이면 언제나 같은 점수가 나오고, 어디서 깎였는지 항목별로 남는다.

  python3 scripts/score.py init <본문.md> [-o 판정.yaml]   본문의 주요업무·자격요건·우대사항을 줄 단위 뼈대로
  python3 scripts/score.py <판정.yaml>...                  점수표 출력
  python3 scripts/score.py --json <판정.yaml>...           한 줄에 하나씩 JSON (다른 스크립트용)
  python3 scripts/score.py apply <판정.yaml>...            pipeline.md 에 반영 (선별 전·대기 줄을 새 점수로, FAIL 은 제외 섹션으로)

점수 = 공통 기준 + 개인 선호.
  공통 기준(이 파일의 상수): 필수·우대 충족도로 등급(S 4.9–5.0 · A 4.5–4.8 · B 4.0–4.4 · C 3.9 이하)을 정하고, 핵심 빈틈·도메인 상한을 건다.
  개인 선호(data/profile/targets.yaml 의 scoring, 없으면 예시 파일): 하고 싶은 일·피하는 일·신호. 등급 범위 안에서 순서만 바꾼다.
  에이전트 검토(판정 파일 review): references/judgment.md 기준으로 내리거나 조금 올린다.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import jobkit as K  # noqa: E402

FIT = {"done": 5.0, "adjacent": 3.5, "new": 1.5}            # 주요 업무: 해 본 일 / 비슷한 일 / 처음
REQ = {"yes": 5.0, "partial": 3.5}                          # 필수: 못 채우면 gap 종류로
REQ_NO = {"bridge": 2.5, "core": 1.0}
PREF = {"yes": 1.0, "partial": 0.5, "no": 0.0}
# 공통 기준 (references/scoring.md). 개인 설정으로 바꾸지 않는다
WEIGHTS = {"work": 0.30, "required": 0.30, "preferred": 0.10, "direction": 0.30}   # 등급 범위 안에서 순서를 정할 때만 쓴다
CORE_GAP_CAPS = {1: 3.4, 2: 2.9}      # 필수 핵심 빈틈 개수 → 상한
CORE_ALT = (1.75, 0.2)                # 핵심 빈틈이지만 '이에 준하는 경험' 인정: 필수 점수, 상한 가산
LOW_WORK = (2.5, 3.9)                 # 업무 적합이 이 미만이면 → 상한
DOMAIN_NEW_CAP = 3.9                  # 팀 제품의 전문 기술 도메인이 처음이면 → 상한
REVIEW = (-1.0, 0.3)                  # 에이전트 검토 조정 폭 (내림, 올림)
RAW_SPAN = (3.5, 5.5)                 # 등급 범위 안에서 원점수를 펼치는 구간
VERDICTS = [(4.0, "지원 권장", "PASS"), (3.5, "지원 고려", "PASS"), (3.0, "보류", "MARGINAL"), (0, "제외", "FAIL")]
SECTIONS = [("work", r"주요\s*업무|담당\s*업무|하는\s*일|이런\s*일|합류하면|What you('|’)ll do|Responsibilit"),
            ("required", r"자격\s*요건|필수|지원\s*자격|이런\s*분|Requirements|Qualifications|Must"),
            ("preferred", r"우대|Preferred|Nice to have|Plus")]


def config() -> dict:
    t = K.load_yaml(K.P["targets"]) or {}
    if "scoring" not in t:
        t = K.load_yaml(os.path.join(os.path.dirname(K.P["targets"]), "targets.example.yaml")) or {}
    return t.get("scoring") or {}


def _met(x) -> str:
    """YAML 1.1 은 yes/no 를 참/거짓으로 읽는다. 문자열로 되돌린다."""
    v = x.get("met")
    return {True: "yes", False: "no"}.get(v, v) if isinstance(v, bool) else str(v)


def _avg(xs, default):
    return sum(xs) / len(xs) if xs else default


def score(j: dict, cfg: dict) -> dict:
    """판정 dict → {total, verdict, triage, parts, caps, gate}"""
    gates = j.get("gates") or {}
    failed = [k for k, v in gates.items() if v == "fail"]
    if failed:
        return dict(total=None, verdict="제외", triage="FAIL", parts={}, caps=[], gate=failed)
    if not (j.get("work") or j.get("required")):              # 본문을 못 받아 분류할 줄이 없다
        return dict(total=None, verdict="확인 필요", triage="MARGINAL", parts={}, caps=[], gate=[])

    # ── 공통 기준: 공고 요건을 얼마나 채우는가 (모든 사용자 같음) ──
    work = _avg([FIT[x["fit"]] for x in j.get("work") or []], 3.0)
    req_items = j.get("required") or []

    def req_value(x):
        if _met(x) in REQ:
            return REQ[_met(x)]
        return CORE_ALT[0] if x.get("gap") == "core" and x.get("alt") else REQ_NO[x.get("gap", "bridge")]
    req = _avg([req_value(x) for x in req_items], 3.0)
    pref_items = j.get("preferred") or []
    pref = 1 + 4 * _avg([PREF[_met(x)] for x in pref_items], 0.5)
    name, lo, hi, band_why = band(req_items, pref_items, j.get("work") or [])

    # ── 개인 선호: 하고 싶은 일·피하는 일·신호 (data/profile/targets.yaml) ──
    prefer, avoid = set(cfg.get("prefer_work") or {}), set(cfg.get("avoid_work") or {})
    kind = lambda t: 1 if t in prefer else (-1 if t in avoid else 0)   # noqa: E731
    d = j.get("direction") or {}
    dir_ = {1: 5.0, 0: 3.0, -1: 1.5}[kind(d.get("primary"))] + 0.5 * sum(kind(t) for t in d.get("secondary") or [])
    dir_ = min(5.0, max(1.0, dir_))
    sig = cfg.get("signals") or {}
    bonus = sum(float(sig.get(s, 0)) for s in j.get("signals") or [])
    if j.get("priority"):
        bonus += float(cfg.get("priority_bonus", 0))

    # 등급이 점수 범위를 정하고, 업무·방향·신호는 그 범위 안에서 순서를 정한다
    parts = dict(work=work, required=req, preferred=pref, direction=dir_)
    raw = sum(WEIGHTS[k] * v for k, v in parts.items()) + bonus
    if name == "C":                          # 3.5 이상은 3.5~3.9 에 펼쳐 지원 고려 안에서도 순서가 남게
        total = max(1.0, raw) if raw < 3.5 else 3.5 + 0.4 * min(1.0, (raw - RAW_SPAN[0]) / (RAW_SPAN[1] - RAW_SPAN[0]))
    else:                                    # 원점수 3.5~5.5 를 등급 범위에 고르게 펼친다 (상한에 몰려 순서가 사라지지 않게)
        total = lo + (hi - lo) * min(1.0, max(0.0, (raw - RAW_SPAN[0]) / (RAW_SPAN[1] - RAW_SPAN[0])))

    caps = []

    def cap(limit, why):
        nonlocal total
        if total > limit:
            caps.append(f"{why} → 상한 {limit}")
            total = limit
    cores = [x for x in req_items if _met(x) == "no" and x.get("gap") == "core"]
    for n, limit in sorted(CORE_GAP_CAPS.items(), reverse=True):
        if len(cores) >= n:
            if all(x.get("alt") for x in cores):          # 모두 '준하는 경험 인정' 빈틈이면 상한을 조금 올린다
                limit = round(limit + CORE_ALT[1], 1)
            cap(limit, f"필수 핵심 빈틈 {len(cores)}개")
            break
    if work < LOW_WORK[0]:
        cap(LOW_WORK[1], f"업무 적합 {work:.1f} < {LOW_WORK[0]}")
    if j.get("domain_new"):
        cap(DOMAIN_NEW_CAP, f"핵심 도메인 처음 ({j['domain_new']})")
    if kind(d.get("primary")) < 0:                              # 개인: 주 업무가 피하고 싶은 일
        cap(float(cfg.get("avoid_cap", 3.4)), f"주 업무 방향 '{d.get('primary')}'")

    # 에이전트 검토 조정 (references/judgment.md): 내리는 건 1.0까지, 올리는 건 0.3까지, 등급 위로는 못 올림
    rv = j.get("review") or {}
    if rv.get("delta"):
        delta = min(REVIEW[1], max(REVIEW[0], float(rv["delta"])))
        total = min(hi, max(1.0, total + delta))
        caps.append(f"검토 {delta:+.1f}: {rv.get('why', '')}")
    total = round(total, 1)
    verdict, triage = next((v, t) for lim, v, t in VERDICTS if total >= lim)
    return dict(total=total, verdict=verdict, triage=triage, parts=parts, bonus=bonus, caps=caps, gate=[],
                band=f"{name} {lo}–{hi}: {band_why}")


def band(req_items, pref_items, work_items):
    """필수·우대 충족도 → (등급, 하한, 상한, 이유). 공통 기준이라 개인 설정을 읽지 않는다."""
    req_no = [x for x in req_items if _met(x) not in REQ]
    keys = [x for x in pref_items if x.get("key")]
    key_miss = [x for x in keys if _met(x) != "yes"]
    ratio = _avg([PREF[_met(x)] for x in pref_items], None)
    if req_no:
        return ("C", 1.0, 3.9, f"필수 {len(req_no)}줄 못 채움")
    new = sum(1 for x in work_items if x.get("fit") == "new")
    if work_items and new * 2 >= len(work_items):   # 요건 문구가 일반적이라 쉽게 채워져도 매일 할 일의 절반 이상이 처음이면 하한을 주지 않는다
        return ("C", 1.0, 3.9, f"주요 업무 {len(work_items)}줄 중 {new}줄이 처음")
    if key_miss:
        return ("C", 1.0, 3.9, "포지션 핵심 우대 못 채움: " + ", ".join(x["line"][:20] for x in key_miss))
    if pref_items and ratio == 1 and all(_met(x) == "yes" for x in req_items):
        return ("S", 4.9, 5.0, "필수·우대 모두 충족")
    if keys:
        return ("A", 4.5, 4.8, "필수 충족 + 핵심 우대 충족")
    if pref_items and ratio >= 0.75:
        return ("A", 4.5, 4.8, "필수 충족 + 우대 대부분 충족")
    if not pref_items or ratio >= 0.5:
        return ("B", 4.0, 4.4, "필수 충족 + " + ("우대 사항 없음" if not pref_items else "우대 절반 이상"))
    return ("C", 1.0, 3.9, "우대 절반 미만")


def init(path: str) -> dict:
    """본문에서 주요업무·자격요건·우대사항 줄을 뽑아 판정 뼈대를 만든다. 분류(fit·met·gap·type)는 비워 둔다."""
    text = K.read_text(path) or ""
    head = re.search(r"^# (.+?) — (.+)$", text, re.M)
    url = re.search(r"^- URL: (\S+)", text, re.M)
    out = dict(url=url.group(1) if url else "", company=head.group(1) if head else "", title=head.group(2) if head else "",
               source=path, gates=dict(location="", language="", stack="", years="", employment="", comp=""),
               gate_note="", work=[], required=[], preferred=[], direction=dict(primary="", secondary=[]),
               domain_new="", signals=[], priority=False, review={}, note="")
    cur = None
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        heading = line.startswith("#") or re.fullmatch(r"\[[^\]]{1,30}\]", line)   # [이렇게 일합니다] 같은 소제목은 절을 끝낸다
        short = len(line) < 40 and not re.match(r"^[•·\-*▪◦・●○]|^\d+[.)]", line)
        hit = next((k for k, pat in SECTIONS if re.search(pat, line, re.I)), None) if (heading or short) else None
        if hit or heading:
            cur = hit
            continue
        if cur:
            item = re.sub(r"^([•·\-*▪◦・●○]|\d+[.)])\s*", "", line)
            if len(item) > 3:
                out[cur].append({"line": item, **({"fit": ""} if cur == "work" else {"met": ""}), **({"key": False} if cur == "preferred" else {})})
    return out


PENDING, WAIT = "## 새로 수집 (선별 전)", "## 대기"


def _sections(md: str):
    """[(제목, [줄])] — 제목 없는 머리말은 ("", 줄)."""
    out = [("", [])]
    for line in md.split("\n"):
        if line.startswith("## "):
            out.append((line, []))
        else:
            out[-1][1].append(line)
    return out


def apply(files) -> str:
    """판정 결과를 pipeline.md 에 반영한다. 선별 전·대기에 있던 줄과 아직 없는 공고만 바꾸고, 다른 섹션(지원 완료·마감·처리 완료)은 건드리지 않는다."""
    cfg, today = config(), K.TODAY
    secs = _sections(K.read_text(K.P["pipeline"]) or "# 공고 대기함\n")
    elsewhere = {u for h, ls in secs if h and not h.startswith((PENDING, WAIT)) for l in ls for u in K.URL_RE.findall(l)}
    old = {}
    for h, ls in secs:
        if h.startswith((PENDING, WAIT)):
            for l in ls:
                m = K.URL_RE.search(l)
                if m and l.lstrip().startswith("- ["):
                    old[m.group(0)] = l
    targets = K.load_yaml(K.P["targets"]) or {}
    cool = K.cooldown_companies(int(targets.get("reapply_days", 183)))
    new_wait, new_fail, n = [], {}, 0
    touched = set()
    for f in files:
        j = K.load_yaml(f)
        url = j.get("url")
        if not url or url in elsewhere:
            continue
        r = score(j, cfg)
        prev = re.search(r"triage: (PASS|MARGINAL|FAIL) ?([\d.]+)?", old.get(url, ""))
        was = f", 이전 {prev.group(1)} {prev.group(2) or ''}".rstrip() if prev else ""
        kind = "재채점" if prev else "선별"        # 대기에 있던 줄을 다시 매기면 재채점, 선별 전이거나 처음이면 선별
        src = K.read_text(os.path.join(K.ROOT, j.get("source", ""))) if j.get("source") else ""
        loc = (re.search(r"^- 근무지: (.*)$", src, re.M) or [None, "?"])[1].strip() or "?"
        rel = os.path.relpath(f, K.ROOT)
        hit = K.company_in(j.get("company", ""), cool, exact=True)
        if hit:                                   # 지원한 회사는 쿨다운 동안 대기에 두지 않는다
            r = dict(r, triage="FAIL")
            j = dict(j, gate_note=f"재지원 쿨다운 ~{cool[hit]} (점수 {r['total']})")
        if r["triage"] == "FAIL":
            why = j.get("gate_note") or j.get("note") or ""
            new_fail.setdefault(kind, []).append(f"- [x] {url} | {j.get('company')} | {j.get('title')} | FAIL {r['total'] or ''} ({kind} {today}{was}) | {why}".replace("FAIL  (", "FAIL ("))
        else:
            sc = f"{r['total']}/5" if r["total"] is not None else "?/5 본문 확인 필요"
            new_wait.append((r["total"] or 0, f"- [ ] {url} | {j.get('company')} | {j.get('title')} | {loc} | triage: {r['triage']} {sc} "
                                              f"({kind} {today}{was}) | {j.get('note', '')} | 판정: {rel}"))
        touched.add(url)
        n += 1
    out = []
    for h, ls in secs:
        if h.startswith((PENDING, WAIT)):
            rest = [l for l in ls if not any(u in touched for u in K.URL_RE.findall(l))]
            if h.startswith(WAIT):
                items = [(float((re.search(r"triage: \w+ ([\d.]+)/5", l) or [0, 0])[1]), l) for l in rest if l.lstrip().startswith("- [")]
                others = [l for l in rest if not l.lstrip().startswith("- [")]
                items = sorted(items + new_wait, key=lambda x: -x[0])
                ls = [""] + [l for _, l in items] + [""] + [l for l in others if l.strip()] + [""]
            else:
                ls = rest
        out.append((h, ls))
    md = "\n".join((h + "\n" if h else "") + "\n".join(ls) for h, ls in out)
    md = re.sub(r"\n{3,}", "\n\n", md)
    if not any(h.startswith(WAIT) for h, _ in secs) and new_wait:
        md = K.insert_under(md, WAIT, [l for _, l in sorted(new_wait, key=lambda x: -x[0])])
    for kind, lines in new_fail.items():
        md = K.insert_under(md, f"## 제외 ({kind} {today})", lines, before="## 지원 완료")
    K.write_text(K.P["pipeline"], md)
    n_fail = sum(len(v) for v in new_fail.values())
    return f"pipeline.md 반영 {n}건 (대기 {len(new_wait)} · 제외 {n_fail}, 다른 섹션에 있어 건너뜀 {len([f for f in files]) - n})"


def _row(j, r):
    if r["total"] is None:
        why = f"조건: {', '.join(r['gate'])}" if r["gate"] else "분류할 줄 없음"
        return f"| {j.get('company')} | {j.get('title')} | — | {r['verdict']} | {why} | {j.get('gate_note') or j.get('note', '')} |"
    p = r["parts"]
    detail = f"업무 {p['work']:.1f} · 필수 {p['required']:.1f} · 우대 {p['preferred']:.1f} · 방향 {p['direction']:.1f}"
    if r["bonus"]:
        detail += f" · 신호 {r['bonus']:+.1f}"
    detail += f" · 등급 {r['band']}"
    if r["caps"]:
        detail += " · " + "; ".join(r["caps"])
    return f"| {j.get('company')} | {j.get('title')} | {r['total']}/5 | {r['verdict']} | {detail} | {j.get('note', '')} |"


def main(argv=None):
    ap = argparse.ArgumentParser(description="공고 점수 계산")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("-o", "--out")
    a = ap.parse_args(argv)
    if a.files[0] == "apply":
        print(apply(a.files[1:]))
        return 0
    if a.files[0] == "init":
        import yaml
        for f in a.files[1:]:
            s = yaml.safe_dump(init(f), allow_unicode=True, sort_keys=False, width=200)
            if a.out:
                K.write_text(a.out, s)
            else:
                print(s)
        return 0
    cfg = config()
    if not a.json:
        print("| 회사 | 포지션 | 점수 | 판정 | 항목별 | 근거 |\n|---|---|---|---|---|---|")
    for f in a.files:
        j = K.load_yaml(f)
        r = score(j, cfg)
        print(json.dumps(dict(file=f, url=j.get("url"), **r), ensure_ascii=False) if a.json else _row(j, r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
