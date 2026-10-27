#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""공고 준비 자료(data/job_postings/*.prep.yaml, modes/prep.md)를 HTML 한 쪽으로 그린다.

공고 현황표(report_html.py)가 준비 자료가 있는 공고마다 이 쪽을 prep/<열쇠>.html 로 쓰고 그 줄에서 잇는다.
디자인은 현황표와 같은 서식(DESIGN.md)이고, 숫자 계산(영업이익률, 전년 대비)은 여기서 한다.
"""
import glob
import hashlib
import html
import os
from typing import Any, Dict, List, Optional

import yaml

import jobkit as K

PRIORITY = ("높음", "보통", "낮음")


def load(path: str) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        d = yaml.safe_load(f) or {}
    if not isinstance(d, dict) or not (d.get("posting") or {}).get("url"):
        raise ValueError(f"준비 자료에 posting.url 이 없음: {path}")
    d["_path"] = path
    return d


def problems(d: Dict[str, Any]) -> List[str]:
    """그리기 전에 알려 줄 것: 비어 버린 값(흐름 표기 { } 안의 따옴표 없는 쉼표가 흔한 원인), 없는 출처 번호."""
    out: List[str] = []
    ids = {s.get("id") for s in d.get("sources") or [] if isinstance(s, dict)}

    def walk(o: Any, at: str) -> None:
        if isinstance(o, dict):
            for k, v in o.items():
                if v is None:
                    out.append(f"{at}.{k} 값이 비었음 (쉼표가 든 값은 따옴표로 감싸기)")
                elif k == "source":
                    for n in v if isinstance(v, list) else [v]:
                        if n not in ids:
                            out.append(f"{at}.source {n} 이 sources 에 없음")
                else:
                    walk(v, f"{at}.{k}")
        elif isinstance(o, list):
            for i, x in enumerate(o):
                walk(x, f"{at}[{i}]")

    walk({k: v for k, v in d.items() if not k.startswith("_")}, "")
    return [p.lstrip(".") for p in out]


def slug(url: str) -> str:
    """공고 주소 → 쪽 파일 이름. 같은 공고는 다시 그려도 같은 이름이라 링크가 유지된다."""
    return hashlib.sha1(K.url_key(url).encode("utf-8")).hexdigest()[:10]


def index(folder: str) -> Dict[str, Dict[str, Any]]:
    """폴더의 *.prep.yaml → {주소 열쇠: 준비 자료}. 읽지 못한 파일은 이유를 알리고 건너뛴다."""
    out: Dict[str, Dict[str, Any]] = {}
    for p in sorted(glob.glob(os.path.join(folder, "*.prep.yaml"))):
        try:
            d = load(p)
        except (OSError, ValueError, yaml.YAMLError) as e:
            print(f"준비 자료를 읽지 못함: {p} — {str(e).splitlines()[0]}")
            continue
        out[K.url_key(d["posting"]["url"])] = d
    return out


def remaining(d: Dict[str, Any]) -> int:
    return sum(1 for x in d.get("prepare") or [] if isinstance(x, dict) and not x.get("done"))


# ── 그리기 ────────────────────────────────────────────────────────────────

def _e(s: Any) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def _src(v: Any) -> str:
    """출처 번호 → 위첨자 링크."""
    if v in (None, ""):
        return ""
    ns = v if isinstance(v, list) else [v]
    return "".join(f'<sup class="src"><a href="#src-{_e(n)}">[{_e(n)}]</a></sup>' for n in ns)


def _list(items: Any) -> str:
    items = [x for x in items or [] if x not in (None, "")]
    return "<ul class='plain'>" + "".join(f"<li>{_e(x)}</li>" for x in items) + "</ul>" if items else '<p class="none">확인 못 함</p>'


def _table(head: List[str], rows: List[List[str]], cls: str = "") -> str:
    th = "".join(f"<th>{h}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="wrap"><table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'


def _section(sid: str, title: str, inner: str, note: str = "") -> str:
    rng = f'<span class="range">{note}</span>' if note else ""
    return f'<section class="band" id="{sid}"><h2>{title}{rng}</h2>{inner}</section>'


def _money(v: Any) -> str:
    return f"{v:,.0f}" if isinstance(v, (int, float)) else _e(v or "—")


def finance_rows(fin: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """연도별 매출·영업이익 → 영업이익률, 매출 전년 대비 (계산은 스크립트가 한다)."""
    fin = sorted((f for f in fin or [] if isinstance(f, dict) and f.get("year")), key=lambda f: f["year"])
    out: List[Dict[str, Any]] = []
    prev: Optional[float] = None
    for f in fin:
        rev, op = f.get("revenue"), f.get("operating_profit")
        rev = float(rev) if isinstance(rev, (int, float)) and rev > 0 else None     # 매출이 없거나 0 이하면 비율을 내지 않는다
        margin = round(op / rev * 100, 1) if rev and isinstance(op, (int, float)) else None
        yoy = round((rev - prev) / prev * 100, 1) if rev and prev else None
        out.append(dict(f, margin=margin, yoy=yoy))
        prev = rev
    return out


def body(d: Dict[str, Any], back: str = "../postings.html") -> str:
    p, co, pr = d["posting"], d.get("company") or {}, d.get("process") or {}
    prep = [x for x in d.get("prepare") or [] if isinstance(x, dict)]
    prep.sort(key=lambda x: (bool(x.get("done")), PRIORITY.index(x["priority"]) if x.get("priority") in PRIORITY else len(PRIORITY)))
    qs = [q for q in d.get("questions") or [] if isinstance(q, dict)]
    flags = [x for x in d.get("red_flags") or [] if x]
    tests = [t for t in pr.get("tests") or [] if isinstance(t, dict)]
    left = remaining(d)
    out = ['<main class="sheet prep">']
    out.append(f'<p class="back"><a href="{_e(back)}">← 공고 현황</a></p>')
    out.append(f'<header class="head"><div><h1>{_e(p.get("company"))} 준비 자료</h1>'
               f'<p class="sub"><a href="{_e(p["url"])}" target="_blank" rel="noopener">{_e(p.get("title"))}</a></p></div>'
               f'<dl class="issue"><dt>작성일</dt><dd>{_e(d.get("updated"))}</dd>'
               f'<dt>파일</dt><dd><code>{_e(os.path.basename(d.get("_path", "")))}</code></dd></dl></header>')
    cells = [("#todo", "더 준비할 것", "남은 것 / 전체", f'{left}<small>/ {len(prep)}건</small>', left > 0),
             ("#questions", "예상 질문", "꼬리질문 포함", f'{len(qs)}<small>문항</small>', False),
             ("#process", "시험", "예상 형식", _e(" · ".join(t.get("kind", "") for t in tests if t.get("guess") != "없음으로 보임")) or "—", False),
             ("#flags", "경고 신호", "확인할 것", f'{len(flags)}<small>건</small>', False)]
    out.append('<nav class="ledger" aria-label="준비 현황"><div class="lg-title" aria-hidden="true">준비</div><div class="lg-cells">'
               + "".join(f'<a class="{"is-seal" if hot else ""}" href="{h}"><span class="k">{k}<small>{s}</small></span>'
                         f'<span class="v">{v}</span></a>' for h, k, s, v, hot in cells) + "</div></nav>")
    if d.get("summary"):
        out.append(f'<p class="lede">{_e(d["summary"])}</p>')
    if d.get("fit"):
        out.append(_section("fit", "이 회사여야 하는 이유", _list(d["fit"]), "내 경험과 맞닿는 점"))

    rows = [[f'<span class="pri pri-{_e(x.get("priority"))}">{_e(x.get("priority") or "—")}</span>',
             f'<span class="{"done" if x.get("done") else ""}">{_e(x.get("item"))}</span>', _e(x.get("why")),
             "완료" if x.get("done") else "남음"] for x in prep]
    out.append(_section("todo", "더 준비할 것", _table(["우선", "할 일", "이유", "상태"], rows, "t-todo") if rows else '<p class="none">아직 없음</p>',
                        "높음부터, 끝낸 것은 아래로"))

    inner = ""
    if pr.get("stages"):
        inner += _table(["전형", "보는 것", "준비"], [[_e(s.get("name")), _e(s.get("what")), _e(s.get("prep"))]
                                                  for s in pr["stages"] if isinstance(s, dict)])
    if tests:
        inner += '<h3>시험 예상</h3>' + _table(["형식", "예상", "근거"], [[_e(t.get("kind")), _e(t.get("guess")), _e(t.get("basis")) + _src(t.get("source"))]
                                                                   for t in tests])
    if pr.get("reports"):
        inner += '<h3>면접 후기</h3>' + _table(["전형", "내용"], [[_e(r.get("stage")), _e(r.get("text")) + _src(r.get("source"))]
                                                           for r in pr["reports"] if isinstance(r, dict)])
    out.append(_section("process", "전형과 시험", inner or '<p class="none">확인 못 함</p>'))

    rows = []
    for n, q in enumerate(qs, 1):
        follow = "".join(f"<li>{_e(f)}</li>" for f in q.get("follow") or [])
        rows.append([str(n), f'<b>{_e(q.get("q"))}</b><span class="why">{_e(q.get("why"))}</span>', _e(q.get("from")),
                     f'<ol class="follow">{follow}</ol>' if follow else "—", _e(q.get("answer") or "—")])
    out.append(_section("questions", "예상 질문", _table(["번호", "질문", "출처", "꼬리질문", "답의 뼈대 (근거)"], rows, "t-q") if rows
                        else '<p class="none">아직 없음</p>', "이력서 · 공고 · 면접 후기에서"))

    wants = [w for w in (d.get("role") or {}).get("wants") or [] if isinstance(w, dict)]
    if wants:
        rows = [[_e(w.get("skill")), _e(w.get("kind")), f'<span class="mine mine-{_e(w.get("mine"))}">{_e(w.get("mine"))}</span>',
                 _e(w.get("evidence") or "—"), _e(w.get("prep") or "—")] for w in wants]
        out.append(_section("role", "직무가 원하는 것", _table(["기술·경험", "구분", "내 상태", "근거", "준비"], rows)))

    team = d.get("team") or {}
    if team:
        out.append(_section("team", "이 팀이 하는 일",
                            "".join(f"<h3>{t}</h3>{_list(team.get(k))}" for k, t in (("does", "하는 일"), ("stack", "기술"), ("scale", "규모")))))

    inner = ""
    if co.get("numbers"):
        inner += _table(["항목", "값", "기준", "비고"], [[_e(n.get("label")), f'<b>{_e(n.get("value"))}</b>{_src(n.get("source"))}',
                                                    _e(n.get("as_of") or "—"), _e(n.get("note") or "")]
                                                   for n in co["numbers"] if isinstance(n, dict)], "t-num")
    fin = finance_rows(co.get("finance") or [])
    if fin:
        top = max([abs(f["revenue"]) for f in fin if isinstance(f.get("revenue"), (int, float))] or [1]) or 1
        rows = []
        for f in fin:
            rev = f.get("revenue")
            bar = (f'<i class="bar" style="--w:{abs(rev) / top * 100:.0f}%"></i>' if isinstance(rev, (int, float)) else "")
            op = f.get("operating_profit")
            rows.append([_e(f["year"]), f'{bar}<b>{_money(rev)}</b>{_src(f.get("source"))}',
                         f'<span class="{"neg" if isinstance(op, (int, float)) and op < 0 else ""}">{_money(op)}</span>',
                         "—" if f["margin"] is None else f'{f["margin"]:+.1f}%', "—" if f["yoy"] is None else f'{f["yoy"]:+.1f}%'])
        inner += '<h3>매출과 영업이익 <small>단위 억 원</small></h3>' + _table(["연도", "매출", "영업이익", "영업이익률", "매출 전년 대비"], rows, "t-fin")
    if co.get("leaders"):
        inner += '<h3>경영진</h3>' + _table(["이름", "직책", "메모"], [[_e(x.get("name")), _e(x.get("role")), _e(x.get("note")) + _src(x.get("source"))]
                                                               for x in co["leaders"] if isinstance(x, dict)])
    if co.get("reviews"):
        inner += '<h3>회사 평가</h3>' + _table(["곳", "평점", "내용"], [[_e(r.get("site")), f'{_e(r.get("rating"))} <small>({_e(r.get("count"))}건)</small>',
                                                              _e(r.get("text")) + _src(r.get("source"))]
                                                             for r in co["reviews"] if isinstance(r, dict)])
    if co.get("issues"):
        inner += '<h3>최근 이슈</h3>' + _table(["시기", "내용"], [[_e(x.get("date")), _e(x.get("text")) + _src(x.get("source"))]
                                                          for x in co["issues"] if isinstance(x, dict)])
    for k, t in (("product", "제품과 사용자"), ("culture", "문화"), ("talent", "인재상")):
        if co.get(k):
            inner += f"<h3>{t}</h3>{_list(co[k])}"
    out.append(_section("company", "회사", inner or '<p class="none">아직 조사 안 함</p>', "숫자마다 출처와 기준 시점"))

    if flags:
        out.append(_section("flags", "경고 신호", _list(flags)))
    if d.get("reverse_questions"):
        out.append(_section("reverse", "역질문", "<ol class='plain'>" + "".join(f"<li>{_e(x)}</li>" for x in d["reverse_questions"]) + "</ol>"))
    srcs = [s for s in d.get("sources") or [] if isinstance(s, dict)]
    if srcs:
        items = "".join(f'<li id="src-{_e(s.get("id"))}"><span class="n">[{_e(s.get("id"))}]</span> '
                        + (f'<a href="{_e(s["url"])}" target="_blank" rel="noopener">{_e(s.get("title"))}</a>' if s.get("url") else _e(s.get("title")))
                        + (f' <small>{_e(s.get("read"))} 읽음</small>' if s.get("read") else "") + "</li>" for s in srcs)
        out.append(_section("sources", "출처", f'<ol class="sources">{items}</ol>'))
    out.append('<footer class="foot"><p>사실마다 출처 번호가 붙고, 확인하지 못한 것은 "확인 못 함"으로 둡니다. '
               '영업이익률과 전년 대비는 <code>scripts/prep_page.py</code>가 계산합니다.</p></footer>')   # 로컬 경로는 싣지 않는다 (올린 쪽에 드러남)
    out.append("</main>")
    return "\n".join(out)


CSS = r"""
.prep .back { margin: 0 0 var(--s-3); font-size: .9rem; }
.prep .lede { margin: var(--s-5) 0 0; font: 700 1.05rem/1.7 var(--f-title); letter-spacing: .02em; max-width: 72ch; }
.prep h3 { margin: var(--s-5) 0 var(--s-2); font: 800 1rem/1.3 var(--f-title); letter-spacing: .04em; }
.prep h3 small { font: 400 .8rem var(--f-body); color: var(--ink-2); margin-left: .4em; }
.prep .band > .wrap + h3 { margin-top: var(--s-5); }
.prep .plain { margin: 0; padding-left: 1.3em; display: grid; gap: var(--s-1); max-width: 80ch; }
.prep .none { margin: 0; color: var(--ink-3); }
.prep td small { color: var(--ink-3); }
.prep .src { margin-left: .15em; font-size: .7em; }
.prep .src a { text-decoration: none; }
.prep .why { display: block; margin-top: 2px; color: var(--ink-2); font-size: .85rem; }
.prep .follow { margin: 0; padding-left: 1.2em; color: var(--ink-2); font-size: .9rem; }
.prep .t-q td:first-child, .prep .t-todo td:first-child { width: 3.6rem; text-align: center; }
.prep .t-todo td:last-child { width: 4.6rem; white-space: nowrap; color: var(--ink-2); }
.prep .done { color: var(--ink-3); text-decoration: line-through; }
.prep .pri { display: inline-block; padding: 0 .3em; font-size: .8rem; letter-spacing: .06em; }
.prep .pri-높음 { border: 1.5px solid var(--seal); color: var(--seal); font-weight: 700; }
.prep .pri-보통 { border: 1px solid var(--ink-2); color: var(--ink-2); }
.prep .pri-낮음 { color: var(--ink-3); }
.prep .mine { font-weight: 600; }
.prep .mine-충족 { color: var(--blue); }
.prep .mine-없음 { color: var(--seal); }
.prep .t-fin td:not(:first-child), .prep .t-fin th:not(:first-child) { text-align: right; }
.prep .t-fin td:nth-child(2) { position: relative; min-width: 9rem; }
.prep .bar { position: absolute; inset: 20% auto 20% 0; width: var(--w); background: var(--blue-soft); z-index: 0; }
.prep .t-fin b, .prep .t-fin sup { position: relative; }
.prep .neg { color: var(--seal); }
.prep .sources { margin: 0; padding: 0; list-style: none; display: grid; gap: var(--s-1); font-size: .9rem; }
.prep .sources .n { font-family: var(--f-num); color: var(--ink-3); }
.prep .sources :target { background: var(--blue-soft); }
@media (max-width: 720px) {
  .prep table, .prep tbody, .prep tr, .prep td { display: block; }
  .prep thead { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
  .prep tr { padding: var(--s-2) var(--s-3); border-bottom: 1px solid var(--rule-2); }
  .prep td { border: 0; padding: 2px 0; width: auto !important; text-align: left !important; }
}
"""


def document(d: Dict[str, Any], back: str = "../postings.html") -> str:
    import report_html as R   # 현황표와 같은 서식 (색·글꼴·괘선)
    title = f'{d["posting"].get("company", "")} 준비 자료'
    return ('<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f'<title>{_e(title)}</title>\n{R.FONT}\n<style>{R.CSS}{CSS}</style>\n</head>\n<body>\n{body(d, back)}\n</body>\n</html>\n')


def write_pages(preps: List[Dict[str, Any]], folder: str, back: str) -> List[str]:
    """준비 자료마다 folder/prep/<열쇠>.html 을 쓴다. back 은 현황표 파일 이름(같은 폴더, 비우면 그 폴더 자체). 쓴 파일 경로 목록."""
    out = []
    os.makedirs(os.path.join(folder, "prep"), exist_ok=True)
    for d in preps:
        path = os.path.join(folder, "prep", slug(d["posting"]["url"]) + ".html")
        K.write_text(path, document(d, "../" + back))
        out.append(path)
    return out


def example() -> Dict[str, Any]:
    """견본 현황표(--demo)에 붙일 가상 회사 준비 자료."""
    return load(os.path.join(K.RES, "examples", "prep.example.yaml"))

