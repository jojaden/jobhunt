# -*- coding: utf-8 -*-
"""resume.yaml → HTML → A4 PDF + 페이지별 PNG.

사용법
  python3 scripts/render.py data/resumes/base_service.yaml
  python3 scripts/render.py examples/example.yaml --profile examples/profile.example.yaml
옵션
  --profile PATH   개인정보 yaml (기본: data/profile/profile.yaml)
  --design A|B|C   디자인 (기본: yaml meta.design, 없으면 B)
  --out DIR        산출물 폴더 (기본: data/output)
  --no-png         PNG 미리보기 생략
  --no-check       빌드 후 검사 생략
  --offline        링크 접속 검사 생략

개인정보(이름·연락처)는 코드에 적지 않는다. 모두 profile yaml에서 읽는다.
"""
import argparse
import glob
import html
import os
import re
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jobkit import ROOT  # noqa: E402  (개인 자료 폴더: data/profile · data/output 기본값)


# ══════════════════════════════ 인라인 마크업 ══════════════════════════════
# yaml 문장에는 HTML 대신 가벼운 표기를 쓴다.
#   **굵게**   `코드`   [글자](https://주소)   [확인 필요] ← 확정 전 표시(노란 형광)
_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_CODE = re.compile(r"`([^`]+)`")
CONFIRM_TAG = "[확인 필요]"


def md(s):
    if s is None:
        return ""
    s = str(s)
    codes = []

    def keep_code(m):
        codes.append(m.group(1))
        return f"\x00{len(codes) - 1}\x00"

    s = _CODE.sub(keep_code, s)
    s = html.escape(s, quote=False)
    s = s.replace(html.escape(CONFIRM_TAG, quote=False), '<mark class="confirm">확인 필요</mark>')
    s = _LINK.sub(lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', s)
    s = _BOLD.sub(r"<b>\1</b>", s)
    s = re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{html.escape(codes[int(m.group(1))], quote=False)}</code>", s)
    return s


def esc(s):
    return html.escape(str(s), quote=False)


# ══════════════════════════════ CSS ══════════════════════════════
# 본문은 Pretendard(한글 문서용, 영문·숫자가 또렷함). 없으면 Noto Sans CJK KR로 대체.
SANS = '"Circled","Pretendard","Pretendard Variable","Noto Sans CJK KR","Noto Sans KR",sans-serif'
SERIF = '"Noto Serif CJK KR","Noto Serif KR",serif'
MONO = '"Noto Sans Mono CJK KR",Menlo,monospace'

BREAKS = """
/* Pretendard의 ①② 원문자는 본문보다 작다. 이 범위만 Noto Sans CJK로 그린다. */
@font-face { font-family:"Circled"; font-weight:400; unicode-range:U+2460-24FF;
  src:local("NotoSansCJKkr-Regular"), local("Noto Sans CJK KR"); }
@font-face { font-family:"Circled"; font-weight:700; unicode-range:U+2460-24FF;
  src:local("NotoSansCJKkr-Bold"), local("Noto Sans CJK KR Bold"); }
body { word-break:keep-all; overflow-wrap:break-word; letter-spacing:-0.01em; }   /* 한글은 어절 단위로 줄바꿈 */
p, li, .opt, .summary { text-wrap:pretty; }
h2, h3, .sub-title { text-wrap:balance; }
.period, .meta, .kpi .v, .timeline b, .contact { font-variant-numeric:tabular-nums; }
.phead { page-break-inside:avoid; }
.pstart { page-break-inside:avoid; }   /* 제목·메타·요약 바 + 첫 행을 한 덩어리로: 제목만 페이지 끝에 남지 않게 */
.row .label, .sub-title { page-break-after:avoid; }
.options, .result, li, .summary, .kpi { page-break-inside:avoid; }
.stitle { page-break-after:avoid; page-break-inside:avoid; }
.section { page-break-before:auto; }
ul { margin:0; padding-left:16px; }
* { box-sizing:border-box; }
.stitle + .project { border-top:none !important; margin-top:2px !important; padding-top:0 !important; }
mark.confirm { background:#fff1a8; color:#6b5200; font-size:7.4pt; font-weight:700; padding:0 4px; margin-right:4px; }
"""

# ── A안 · 에디토리얼 (세리프 + 파인그린) ──
A = dict(ink="#20241f", body="#33382f", mut="#7a7f72", hair="#e3e5dc", acc="#2e6e51", accd="#1f5038")
CSS_A = BREAKS + f"""
@page {{ size:A4; margin:16mm 18mm 16mm 18mm; }}
body {{ margin:0; background:#fff; color:{A['body']}; font:9.3pt/1.65 {SANS}; }}
a {{ color:{A['accd']}; text-decoration:none; }}
b {{ color:{A['ink']}; }}
code {{ font-family:{MONO}; font-size:8.7pt; color:{A['accd']}; background:#f1f4ee; padding:0 3px; border-radius:2px; }}
.hd {{ border-bottom:1px solid {A['ink']}; padding-bottom:14px; }}
.hd .name {{ font-family:{SERIF}; font-weight:600; font-size:24pt; color:{A['ink']}; letter-spacing:-0.02em; line-height:1.2; }}
.hd .role {{ font-size:10pt; color:{A['body']}; margin-top:4px; }}
.hd .contact {{ margin-top:8px; font-size:8.6pt; color:{A['mut']}; display:flex; gap:14px; flex-wrap:wrap; }}
.pf {{ margin-top:10px; font-size:8.8pt; color:{A['body']}; }}
.pf .tag {{ font-size:7.4pt; font-weight:700; letter-spacing:1.5px; color:{A['acc']}; border:1px solid {A['acc']}; padding:1px 7px; margin-right:8px; vertical-align:1px; }}
.pf a {{ font-weight:700; }}
.section {{ margin-top:22px; }}
.stitle {{ font-family:{SERIF}; font-weight:600; font-size:12.5pt; color:{A['ink']}; letter-spacing:0.06em; padding-bottom:6px; border-bottom:1px solid {A['hair']}; margin-bottom:12px; }}
.summary-lead {{ margin:0 0 7px; font-size:9.6pt; }}
li {{ margin:4px 0; }}
.skills .line {{ margin:5px 0; display:flex; gap:12px; }}
.skills .line b {{ min-width:74px; font-weight:700; }}
.exp + .exp {{ margin-top:14px; }}
.exp h3 {{ font-size:11pt; margin:0; color:{A['ink']}; }}
.exp .period {{ font-size:8.6pt; color:{A['mut']}; margin:2px 0 7px; }}
.exp p {{ margin:0 0 7px; }}
.timeline li b {{ color:{A['accd']}; font-weight:700; }}
.project {{ border-top:1px solid {A['hair']}; margin-top:18px; padding-top:16px; }}
.section > .project:first-of-type {{ border-top:none; margin-top:4px; padding-top:0; }}
.project h2 {{ font-family:{SERIF}; font-weight:600; font-size:12pt; margin:0 0 4px; color:{A['ink']}; letter-spacing:-0.2px; display:flex; align-items:baseline; gap:10px; }}
.project h2 .num {{ font-weight:600; font-size:11pt; color:{A['acc']}; flex-shrink:0; }}
.meta {{ font-size:8.4pt; color:{A['mut']}; margin-bottom:10px; display:flex; gap:7px; flex-wrap:wrap; align-items:baseline; }}
.meta .role {{ font-weight:700; color:{A['body']}; }}
.chip {{ font-size:8.2pt; color:{A['mut']}; }}
.chip + .chip::before {{ content:"· "; }}
.summary {{ font-family:{SERIF}; font-size:9.9pt; line-height:1.6; color:{A['ink']}; padding:0; margin:8px 0 12px; background:none; }}
.row {{ margin:10px 0; }}
.row .label {{ display:block; font-size:8.4pt; font-weight:700; color:{A['acc']}; letter-spacing:0; margin-bottom:3px; page-break-after:avoid; }}
.row .body p {{ margin:0 0 5px; }}
.options {{ display:block; margin:1px 0; }}
.opt {{ border:none; background:none; padding:3px 0 3px 15px; position:relative; font-size:8.9pt; color:#5c6154; line-height:1.55; }}
.opt::before {{ content:""; position:absolute; left:1px; top:9px; width:6px; height:6px; border:1.3px solid #a9ad9f; border-radius:50%; }}
.opt.adopted::before {{ background:{A['acc']}; border-color:{A['acc']}; }}
.opt .t {{ display:inline; font-weight:700; color:{A['body']}; margin-right:5px; }}
.opt.adopted {{ color:{A['body']}; }}
.opt.adopted .t {{ color:{A['accd']}; }}
.opt.adopted .t::after {{ content:"채택"; font-size:7pt; font-weight:700; color:{A['accd']}; border:1px solid {A['acc']}; padding:0 5px; margin-left:7px; letter-spacing:0; vertical-align:1px; white-space:nowrap; display:inline-block; }}
.result {{ display:flex; margin-top:8px; }}
.kpi {{ border:none; border-left:1px solid {A['hair']}; padding:2px 18px; min-width:0; flex:initial; }}
.kpi:first-child {{ border-left:none; padding-left:0; }}
.kpi .v {{ font-family:{SERIF}; font-weight:600; font-size:13pt; color:{A['accd']}; line-height:1.25; letter-spacing:-0.3px; }}
.kpi .k {{ font-size:7.9pt; color:{A['mut']}; margin-top:2px; }}
.related {{ font-size:8.4pt; color:{A['mut']}; margin-top:9px; }}
.related a {{ color:{A['accd']}; }}
.sub-block {{ margin-top:14px; padding-top:10px; border-top:1px dashed {A['hair']}; }}
.sub-title {{ font-size:10pt; font-weight:700; margin:0 0 4px; color:{A['ink']}; }}
.sub-title span {{ color:{A['acc']}; margin-right:5px; }}
.other li {{ margin:7px 0; }}
"""

# ── B안 · 스위스 그리드 (코발트) — 기본 ──
B = dict(ink="#15181c", body="#2b3138", mut="#566069", hair="#e1e5ea", acc="#1e4fc2", tint="#eef2fb")
CSS_B = BREAKS + f"""
@page {{ size:A4; margin:15mm 16mm 15mm 16mm; }}
body {{ margin:0; background:#fff; color:{B['body']}; font:9.3pt/1.62 {SANS}; }}
a {{ color:{B['acc']}; text-decoration:none; }}
b {{ color:{B['ink']}; }}
code {{ font-family:{MONO}; font-size:8.6pt; color:{B['ink']}; background:#f2f4f7; padding:0 3px; }}
.hd {{ display:flex; justify-content:space-between; align-items:flex-end; border-bottom:3px solid {B['ink']}; padding-bottom:12px; }}
.hd .name {{ font-weight:800; font-size:24pt; color:{B['ink']}; letter-spacing:-0.03em; line-height:1.15; }}
.hd .role {{ font-size:9.6pt; color:{B['mut']}; margin-top:3px; font-weight:500; }}
.hd .contact {{ text-align:right; font-size:8.5pt; color:{B['mut']}; line-height:1.8; }}
.pf {{ margin-top:10px; font-size:8.7pt; color:{B['body']}; }}
.pf .tag {{ font-size:7.3pt; font-weight:800; letter-spacing:1.2px; color:#fff; background:{B['acc']}; padding:2px 7px; margin-right:8px; white-space:nowrap; }}
.pf a {{ white-space:nowrap; font-weight:800; }}
.section {{ margin-top:24px; }}
.stitle {{ font-weight:800; font-size:11pt; color:{B['ink']}; letter-spacing:0.12em; margin-bottom:0; }}
.stitle::after {{ content:""; display:block; width:28px; height:3.5px; background:{B['acc']}; margin:5px 0 13px; }}
.summary-lead {{ margin:0 0 7px; font-size:9.5pt; }}
li {{ margin:4px 0; }}
.skills .line {{ margin:5px 0; display:flex; gap:12px; }}
.skills .line b {{ min-width:74px; }}
.exp + .exp {{ margin-top:14px; }}
.exp h3 {{ font-size:11pt; margin:0; color:{B['ink']}; font-weight:800; }}
.exp .period {{ font-size:8.5pt; color:{B['mut']}; margin:2px 0 7px; }}
.exp p {{ margin:0 0 7px; }}
.timeline li b {{ color:{B['acc']}; }}
.project {{ border-top:1px solid {B['hair']}; margin-top:19px; padding-top:15px; }}
.section > .project:first-of-type {{ border-top:none; margin-top:2px; padding-top:0; }}
.project h2 {{ font-size:12pt; margin:0 0 5px; font-weight:700; color:{B['ink']}; letter-spacing:-0.02em; display:flex; align-items:baseline; gap:9px; }}
.project h2 .num {{ font-weight:800; font-size:12pt; font-variant-numeric:tabular-nums; color:{B['acc']}; flex-shrink:0; letter-spacing:0; }}
.meta {{ font-size:8.3pt; color:{B['mut']}; margin-bottom:9px; display:flex; gap:6px; flex-wrap:wrap; align-items:center; }}
.meta .role {{ font-weight:700; color:{B['ink']}; }}
.chip {{ font-size:7.8pt; font-weight:500; border:1px solid {B['hair']}; padding:0 6px; color:{B['body']}; background:#fff; }}
.summary {{ background:{B['tint']}; padding:8px 12px; margin:7px 0 11px; font-size:9.4pt; font-weight:500; color:{B['ink']}; }}
.row {{ margin:9px 0; }}
.row .label {{ display:block; font-size:8.6pt; font-weight:700; color:{B['ink']}; letter-spacing:0; margin-bottom:3px; page-break-after:avoid; }}
.row .label::before {{ content:""; display:inline-block; width:6px; height:6px; background:{B['acc']}; margin-right:6px; vertical-align:1px; }}
.row .body p {{ margin:0 0 5px; }}
.options {{ display:block; margin:1px 0; }}
.opt {{ border:none; border-left:1px solid {B['hair']}; background:none; padding:2px 0 2px 11px; margin:5px 0; font-size:8.8pt; color:#59616b; line-height:1.5; }}
.opt .t {{ display:inline; font-weight:700; color:{B['body']}; margin-right:5px; }}
.opt.adopted {{ border-left-color:{B['acc']}; background:{B['tint']}; padding:6px 12px 6px 11px; color:{B['body']}; }}
.opt.adopted .t {{ color:{B['acc']}; }}
.opt.adopted .t::after {{ content:"채택"; font-size:7pt; font-weight:800; background:{B['acc']}; color:#fff; padding:1px 5px; margin-left:7px; letter-spacing:0; vertical-align:1px; white-space:nowrap; display:inline-block; }}
.result {{ display:flex; gap:0; margin-top:8px; background:{B['tint']}; padding:8px 4px; }}
.kpi {{ border:none; border-left:1px solid #d5ddf0; padding:1px 16px; min-width:0; flex:1; }}
.kpi:first-child {{ border-left:none; }}
.kpi .v {{ font-size:13pt; font-weight:800; color:{B['acc']}; line-height:1.25; letter-spacing:-0.02em; }}
.kpi .k {{ font-size:7.8pt; color:{B['mut']}; margin-top:2px; }}
.related {{ font-size:8.3pt; color:{B['mut']}; margin-top:9px; }}
.sub-block {{ margin-top:13px; padding-top:10px; border-top:1px dashed {B['hair']}; }}
.sub-title {{ font-size:10pt; font-weight:800; margin:0 0 4px; color:{B['ink']}; }}
.sub-title span {{ color:{B['acc']}; margin-right:5px; }}
.other li {{ margin:7px 0; }}
"""

# ── C안 · 다크 마스트헤드 (카퍼) ──
C = dict(ink="#17191c", body="#26292d", mut="#6e675f", hair="#e6e2dc", acc="#b3611e", accd="#8f4d16", tint="#faf5ee")
CSS_C = BREAKS + f"""
@page {{ size:A4; margin:14mm 16mm 15mm 16mm; }}
body {{ margin:0; background:#fff; color:{C['body']}; font:9.3pt/1.62 {SANS}; }}
a {{ color:{C['accd']}; text-decoration:none; }}
b {{ color:{C['ink']}; }}
code {{ font-family:{MONO}; font-size:8.7pt; color:{C['accd']}; background:{C['tint']}; padding:0 3px; border-radius:2px; }}
.mast {{ background:{C['ink']}; color:#fff; padding:15px 18px 14px; margin-bottom:4px; }}
.mast .name {{ font-weight:800; font-size:23pt; letter-spacing:-0.02em; line-height:1.2; color:#fff; }}
.mast .role {{ font-size:9.6pt; color:#c9c3ba; margin-top:3px; }}
.mast .contact {{ margin-top:9px; font-size:8.5pt; color:#b3ada4; letter-spacing:0; display:flex; gap:14px; flex-wrap:wrap; }}
.mast .contact a {{ color:#e8c49a; }}
.pf {{ background:{C['tint']}; padding:7px 18px; margin-top:0; font-size:8.7pt; color:{C['body']}; }}
.pf .tag {{ font-size:7.3pt; font-weight:800; letter-spacing:1.2px; color:#fff; background:{C['acc']}; padding:1px 6px; margin-right:8px; white-space:nowrap; }}
.pf a {{ font-weight:700; }}
.section {{ margin-top:22px; }}
.stitle {{ display:flex; align-items:center; gap:9px; font-size:11.5pt; font-weight:700; color:{C['ink']}; margin-bottom:12px; }}
.stitle::after {{ content:""; flex:1; height:1px; background:{C['hair']}; }}
.stitle .ov {{ font-size:7.2pt; font-weight:700; color:#fff; background:{C['acc']}; letter-spacing:0.14em; padding:2px 6px 2px 7px; }}
.summary-lead {{ margin:0 0 7px; font-size:9.5pt; }}
li {{ margin:4px 0; }}
.skills .line {{ margin:5px 0; display:flex; gap:12px; }}
.skills .line b {{ min-width:74px; }}
.exp + .exp {{ margin-top:14px; }}
.exp h3 {{ font-size:11pt; margin:0; color:{C['ink']}; font-weight:800; }}
.exp .period {{ font-size:8.5pt; color:{C['mut']}; margin:2px 0 7px; }}
.exp p {{ margin:0 0 7px; }}
.timeline li b {{ color:{C['accd']}; }}
.project {{ border-top:1px solid {C['hair']}; margin-top:18px; padding-top:15px; }}
.section > .project:first-of-type {{ border-top:none; margin-top:2px; padding-top:0; }}
.project h2 {{ font-size:12pt; margin:0 0 5px; font-weight:700; color:{C['ink']}; letter-spacing:-0.02em; display:flex; align-items:baseline; gap:9px; }}
.project h2 .num {{ font-weight:700; font-size:9pt; font-variant-numeric:tabular-nums; color:#fff; background:{C['ink']}; padding:1px 7px; flex-shrink:0; letter-spacing:0.5px; }}
.meta {{ font-size:8.3pt; color:{C['mut']}; margin-bottom:9px; display:flex; gap:6px; flex-wrap:wrap; align-items:center; }}
.meta .role {{ font-weight:700; color:{C['ink']}; }}
.chip {{ font-size:7.8pt; font-weight:500; background:#f6f3ef; border:1px solid {C['hair']}; padding:0 6px; color:{C['body']}; }}
.summary {{ background:{C['tint']}; padding:8px 12px; margin:7px 0 11px; font-size:9.4pt; font-weight:500; color:{C['ink']}; }}
.row {{ margin:9px 0; }}
.row .label {{ display:block; font-size:8.6pt; font-weight:700; color:{C['accd']}; letter-spacing:0; margin-bottom:3px; page-break-after:avoid; }}
.row .body p {{ margin:0 0 5px; }}
.options {{ display:block; margin:1px 0; }}
.opt {{ border:none; background:none; padding:3px 0 3px 15px; margin:3px 0; position:relative; font-size:8.8pt; color:#5f5a52; line-height:1.5; }}
.opt::before {{ content:""; position:absolute; left:1px; top:8px; width:7px; height:7px; border:1.3px solid #b6afa5; }}
.opt.adopted::before {{ background:{C['acc']}; border-color:{C['acc']}; }}
.opt .t {{ display:inline; font-weight:700; color:{C['body']}; margin-right:5px; }}
.opt.adopted {{ color:{C['body']}; }}
.opt.adopted .t {{ color:{C['accd']}; }}
.opt.adopted .t::after {{ content:"채택"; font-size:7pt; font-weight:800; background:{C['acc']}; color:#fff; padding:1px 5px; margin-left:7px; letter-spacing:0; vertical-align:1px; white-space:nowrap; display:inline-block; }}
.result {{ display:flex; gap:8px; margin-top:8px; flex-wrap:wrap; }}
.kpi {{ background:{C['ink']}; border:none; padding:6px 13px 7px; min-width:110px; flex:1; }}
.kpi .v {{ font-size:12pt; font-weight:700; color:#fff; line-height:1.25; letter-spacing:0; }}
.kpi .k {{ font-size:7.7pt; color:#b3ada4; margin-top:2px; }}
.related {{ font-size:8.3pt; color:{C['mut']}; margin-top:9px; }}
.sub-block {{ margin-top:13px; padding-top:10px; border-top:1px dashed {C['hair']}; }}
.sub-title {{ font-size:10pt; font-weight:800; margin:0 0 4px; color:{C['ink']}; }}
.sub-title span {{ color:{C['acc']}; margin-right:5px; }}
.other li {{ margin:7px 0; }}
"""

DESIGNS = {"A": CSS_A, "B": CSS_B, "C": CSS_C}

# 섹션 제목 (영문, C안 한글 부제). 순서는 고정: 헤더 → PORTFOLIO → 아래 순서.
TITLES = {
    "summary": ("SUMMARY", "요약"),
    "skills": ("SKILLS", "기술"),
    "experience": ("EXPERIENCE", "경력"),
    "projects": ("PROJECTS", "프로젝트"),
    "other": ("OTHER", "기타"),
}
SECTION_ORDER = ["summary", "skills", "experience", "projects", "other"]


# ══════════════════════════════ 조각 렌더러 ══════════════════════════════
def section(key_or_title, body, design):
    en, ko = TITLES.get(key_or_title, key_or_title) if isinstance(key_or_title, str) else key_or_title
    if design == "C":
        t = f'<div class="stitle"><span class="ov">{esc(en)}</span>{esc(ko)}</div>'
    else:
        t = f'<div class="stitle">{esc(en)}</div>'
    return f'<div class="section">{t}{body}</div>'


def bullets(items):
    return "<ul>" + "".join(f"<li>{md(b)}</li>" for b in items) + "</ul>"


def chips(techs):
    return "".join(f'<span class="chip">{esc(t)}</span>' for t in techs or [])


def options(items):
    out = ['<div class="options">']
    for o in items:
        cls = "opt adopted" if o.get("adopted") else "opt"
        out.append(f'<div class="{cls}"><div class="t">{md(o["title"])}</div>{md(o.get("body", ""))}</div>')
    out.append("</div>")
    return "".join(out)


def kpis(items):
    return '<div class="result">' + "".join(
        f'<div class="kpi"><div class="v">{md(k["value"])}</div><div class="k">{md(k.get("label", ""))}</div></div>'
        for k in items) + "</div>"


def related(links):
    if not links:
        return ""
    return '<div class="related">↳ 관련 글 · ' + " · ".join(
        f'<a href="{l["url"]}">{esc(l["title"])}</a>' for l in links) + "</div>"


def row(r):
    """프로젝트 본문 한 행. 키로 종류를 구분한다.
    text: 문단(문자열 또는 문단 리스트) / options: 선택지 / bullets: 불릿 / kpis: 결과 KPI
    sub: {num, title} 소제목 / group: {num, title, rows} 점선으로 나뉜 하위 블록
    """
    if "sub" in r:
        s = r["sub"]
        return f'<div class="sub-title"><span>{esc(s.get("num", ""))}</span>{md(s["title"])}</div>'
    if "group" in r:
        g = r["group"]
        inner = "".join(row(x) for x in g.get("rows", []))
        return (f'<div class="sub-block"><div class="sub-title"><span>{esc(g.get("num", ""))}</span>'
                f'{md(g["title"])}</div>{inner}</div>')
    label = esc(r.get("label", ""))
    if "text" in r:
        paras = r["text"] if isinstance(r["text"], list) else [r["text"]]
        body = "".join(f"<p>{md(p)}</p>" for p in paras)
    elif "options" in r:
        body = options(r["options"])
    elif "bullets" in r:
        body = bullets(r["bullets"])
    elif "kpis" in r:
        body = kpis(r["kpis"])
    else:
        raise ValueError(f"알 수 없는 행 형식: {r}")
    return f'<div class="row"><div class="label">{label}</div><div class="body">{body}</div></div>'


def project(num, p):
    h = [f'<div class="project"><div class="phead"><h2><span class="num">{num:02d}</span><span>{esc(p["title"])}</span></h2>',
         f'<div class="meta"><span>{esc(p.get("period", ""))}</span><span>·</span>'
         f'<span class="role">{esc(p.get("role", ""))}</span><span>·</span>{chips(p.get("techs"))}</div>',
         f'<div class="summary">{md(p.get("summary", ""))}</div></div>']
    rows = [row(r) for r in p.get("rows", [])]
    if rows:
        h[0] = '<div class="project"><div class="pstart">' + h[0][len('<div class="project">'):]
        h.append(rows[0] + "</div>")
        h += rows[1:]
    h.append(related(p.get("links")))
    h.append("</div>")
    return "".join(h)


def job_title(resume, profile):
    """이름 아래 직무명. 공고별 header.role → profile role 순서. 고정 기본값은 두지 않는다."""
    return (resume.get("header") or {}).get("role") or profile.get("role") or ""


def header(profile, resume, design):
    name = esc(profile["name"])
    role = esc(job_title(resume, profile))
    role = f'<div class="role">{role}</div>' if role else ""   # 직무명이 없으면 줄을 뺀다
    pf = resume.get("portfolio") or {}
    pf_items = pf.get("items") or []
    link_html = [f'<a href="{i["url"]}">{esc(i.get("label") or i["url"])}</a>' for i in pf_items]
    basic = [esc(x) for x in (profile.get("email"), profile.get("phone")) if x]

    pf_box = ""
    if pf_items:
        desc = f' {md(pf["desc"])}' if pf.get("desc") else ""
        pf_box = ('<div class="pf"><span class="tag">PORTFOLIO</span>'
                  + " · ".join(link_html) + desc + "</div>")

    if design == "C":
        contact = "".join(f"<span>{x}</span>" for x in basic + link_html)
        return (f'<div class="mast"><div class="name">{name}</div>{role}'
                f'<div class="contact">{contact}</div></div>{pf_box}')
    if design == "B":
        lines = " · ".join(basic)
        if link_html:
            lines += "<br>" + " · ".join(link_html)
        return (f'<div class="hd"><div><div class="name">{name}</div>{role}</div>'
                f'<div class="contact">{lines}</div></div>{pf_box}')
    contact = "".join(f"<span>{x}</span>" for x in basic + link_html)
    return (f'<div class="hd"><div class="name">{name}</div>{role}'
            f'<div class="contact">{contact}</div>{pf_box}</div>')


def body_sections(resume, design):
    omit = set(resume.get("meta", {}).get("omit_sections", []))
    extras = resume.get("extra_sections") or []
    out = []
    for key in SECTION_ORDER:
        if key in omit:
            continue
        if key == "summary" and resume.get("summary"):
            s = resume["summary"]
            out.append(section(key, f'<p class="summary-lead">{md(s.get("lead", ""))}</p>{bullets(s.get("bullets", []))}', design))
        elif key == "skills" and resume.get("skills"):
            lines = "".join(f'<div class="line"><b>{esc(s["name"])}</b><span>{md(s["items"])}</span></div>' for s in resume["skills"])
            out.append(section(key, f'<div class="skills">{lines}</div>', design))
        elif key == "experience" and resume.get("experience"):
            blocks = []
            for e in resume["experience"]:
                period = esc(e.get("period", ""))
                if e.get("tenure"):
                    period += f" ({esc(e['tenure'])})"
                tl = "".join(f"<li><b>{esc(t['period'])}</b> {md(t['desc'])}</li>" for t in e.get("timeline", []))
                intro = f"<p>{md(e['intro'])}</p>" if e.get("intro") else ""
                title = esc(e["company"]) + (f" — {esc(e['title'])}" if e.get("title") else "")
                blocks.append(f'<div class="exp"><h3>{title}</h3><div class="period">{period}</div>{intro}'
                              f'{"<ul class=timeline>" + tl + "</ul>" if tl else ""}</div>')
            out.append(section(key, "".join(blocks), design))
        elif key == "projects" and resume.get("projects"):
            out.append(section(key, "".join(project(i + 1, p) for i, p in enumerate(resume["projects"])), design))
        elif key == "other" and resume.get("other"):
            out.append(section(key, f'<ul class="other">{"".join(f"<li>{md(o)}</li>" for o in resume["other"])}</ul>', design))
        # 사용자가 추가한 섹션: after 로 위치 지정 (기본 other 뒤)
        for x in extras:
            if x.get("after", "other") == key:
                body = bullets(x["items"]) if x.get("items") else f"<p>{md(x.get('text', ''))}</p>"
                out.append(section((x["title"], x.get("title_ko", x["title"])), body, design))
    return "".join(out)


def build_html(resume, profile, design="B"):
    css = DESIGNS[design]
    return (f'<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><title>{esc(profile["name"])}</title>'
            f'<style>{css}</style></head><body>{header(profile, resume, design)}{body_sections(resume, design)}</body></html>')


# ══════════════════════════════ 빌드 ══════════════════════════════
def safe(s):
    return re.sub(r"[\\/:*?\"<>|\s]+", "_", str(s)).strip("_")


def out_name(resume, profile):
    meta = resume.get("meta", {})
    job = meta.get("job") or job_title(resume, profile)
    version = meta.get("version") or "v1"
    return "_".join(x for x in (safe(profile["name"]), safe(job), safe(version)) if x)


def render_pdf(html_path, pdf_path):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        kw = {}
        exe = os.environ.get("RESUME_CHROMIUM")
        if exe:
            kw["executable_path"] = exe
        b = p.chromium.launch(**kw)
        pg = b.new_page()
        pg.goto("file://" + os.path.abspath(html_path))
        pg.wait_for_timeout(300)
        pg.pdf(path=pdf_path, format="A4", print_background=True, prefer_css_page_size=True)
        b.close()


def render_png(pdf_path, stem, dpi=110):
    from pdf2image import convert_from_path
    imgs = convert_from_path(pdf_path, dpi=dpi)
    for old in glob.glob(f"{glob.escape(stem)}_p*.png"):     # 쪽수가 줄었을 때 이전 빌드의 뒤쪽 PNG가 남지 않게
        if re.fullmatch(r"_p\d+\.png", old[len(stem):]) and int(old[len(stem) + 2:-4]) > len(imgs):
            os.remove(old)
    paths = []
    for i, im in enumerate(imgs):
        pth = f"{stem}_p{i + 1}.png"
        im.save(pth)
        paths.append(pth)
    return paths


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def main(argv=None):
    ap = argparse.ArgumentParser(description="resume.yaml → A4 PDF")
    ap.add_argument("resume")
    ap.add_argument("--profile", default=os.path.join(ROOT, "data/profile/profile.yaml"))
    ap.add_argument("--design", choices=list(DESIGNS))
    ap.add_argument("--out", default=os.path.join(ROOT, "data/output"))
    ap.add_argument("--no-png", action="store_true")
    ap.add_argument("--no-check", action="store_true")
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args(argv)

    resume = load_yaml(a.resume)
    if not os.path.exists(a.profile):
        sys.exit(f"개인정보 파일이 없습니다: {a.profile}\n"
                 "data/profile/profile.example.yaml 을 복사해 profile.yaml 을 만들어 주세요.")
    profile = load_yaml(a.profile)
    for k in ("name",):
        if not profile.get(k):
            sys.exit(f"profile 에 {k} 값이 없습니다.")

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import check
    problems = check.schema_issues(resume)     # 키 오타는 조용히 빠지므로 빌드 전에 멈춘다
    if problems:
        check.print_report(dict(issues=problems, links=[], pages=None, errors=problems, warns=[]))
        print("형식: references/yaml_schema.md")
        return 1

    design = a.design or resume.get("meta", {}).get("design", "B")
    os.makedirs(a.out, exist_ok=True)
    stem = os.path.join(a.out, out_name(resume, profile))
    html_path, pdf_path = stem + ".html", stem + ".pdf"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(build_html(resume, profile, design))
    render_pdf(html_path, pdf_path)
    pngs = [] if a.no_png else render_png(pdf_path, stem)
    print(f"PDF  {pdf_path}")
    for p in pngs:
        print(f"PNG  {p}")

    if not a.no_check:
        report = check.run_all(resume, pdf_path, offline=a.offline)
        check.print_report(report)
        return 1 if report["errors"] else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
