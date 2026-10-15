# -*- coding: utf-8 -*-
"""추적 중인 공고가 아직 열려 있는지 확인 (LLM 호출 없음).

대상: pipeline.md 의 "대기"·"새로 수집 (선별 전)" 항목 + tracker.md 의 평가함 행.
판정은 공급원 상세 API·HTTP 상태로 한다. "공개 목록에 없다"를 마감으로 보지 않는다 (references/sources.md).

  python3 scripts/alive.py            결과만 출력
  python3 scripts/alive.py --write    마감된 대기 공고를 "마감 확인 (날짜)"로 옮기고, 평가함 행을 포기로 바꾼다
  python3 scripts/alive.py --json     tracker.py report 가 읽는 형식
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import jobkit as K  # noqa: E402
import providers  # noqa: E402

OPEN_SECTIONS = ("## 새로 수집 (선별 전)", "## 대기")


def pipeline_targets():
    return [dict(url=r.url, company=r.company, title=r.title, where="pipeline")
            for r in K.read_pipeline() if r.section in OPEN_SECTIONS and r.mark == " " and r.url]


def eval_url(link: str) -> str:
    m = re.search(r"\]\(([^)]+)\)", link or "")
    if not m:
        return ""
    path = os.path.normpath(os.path.join(os.path.dirname(K.P["tracker"]), m.group(1)))
    head = K.read_text(path)[:3000]
    u = re.search(r"URL:?\**\s*(https?://\S+)", head)
    return u.group(1).rstrip("*") if u else ""


def tracker_targets():
    out = []
    for r in K.read_tracker():
        if r["state"] != "평가함":
            continue
        url = eval_url(r["eval"]) or (K.URL_RE.search(r["memo"]).group(0) if K.URL_RE.search(r["memo"]) else "")
        if url:
            out.append(dict(url=url, company=r["company"], title=r["role"], where="tracker", num=r["num"]))
    return out


def check(url: str):
    mod = providers.for_url(url)
    if not mod:
        return None, "판정 방법 없음"
    try:
        return mod.alive(url), mod.__name__.split(".")[-1]
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def _lane(urls):
    return [(u, check(u)) for u in urls]


def run(targets):
    """주소마다 한 번. 사이트마다 줄 하나로 차례로 확인하고 사이트끼리는 동시에 한다 (요청 간격은 jobkit.http_get 이 지킨다)."""
    first = {}
    for t in targets:
        first.setdefault(t["url"], t)
    lanes = {}
    for u in first:
        lanes.setdefault(K.site(urlsplit(u).netloc), []).append(u)
    pool = ThreadPoolExecutor(max(len(lanes), 1))
    try:
        got = dict(p for lane in pool.map(_lane, lanes.values()) for p in lane)
    except KeyboardInterrupt:
        # 파일은 확인이 다 끝난 뒤에 쓰므로 남는 것이 없다. 도는 스레드를 기다리지 않고 바로 끝낸다
        print("\n중단 — 쓴 파일 없음", file=sys.stderr, flush=True)
        os._exit(130)
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    return [dict(t, alive=got[u][0], how=got[u][1]) for u, t in first.items()]


def main(argv=None):
    ap = argparse.ArgumentParser(description="공고 마감 확인")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    res = run(tracker_targets() + pipeline_targets())
    if a.json:
        print(json.dumps({r["url"]: r["alive"] for r in res}, ensure_ascii=False))
        return 0

    closed = [r for r in res if r["alive"] is False]
    if a.write and closed:
        md = K.read_text(K.P["pipeline"])
        for r in closed:
            if r["where"] == "pipeline":
                md = K.move_line(md, r["url"], f"## 마감 확인 ({K.TODAY})", f"마감 확인 {K.TODAY} ({r['how']})", before="## 처리 완료")
        K.write_text(K.P["pipeline"], md)
        lines = K.read_text(K.P["tracker"]).split("\n")
        nums = {r.get("num") for r in closed if r["where"] == "tracker"}
        for i, line in enumerate(lines):
            m = re.match(r"\|\s*(\d+)\s*\|", line)
            if m and int(m.group(1)) in nums:
                row = next(x for x in K.read_tracker() if x["num"] == int(m.group(1)))
                row["state"] = "포기"
                row["memo"] += f"; 공고 마감 확인 ({K.TODAY}, alive.py)"
                lines[i] = K.tracker_line(row)
        K.write_text(K.P["tracker"], "\n".join(lines))

    mark = {True: "열림", False: "마감", None: "확인 불가"}
    print(f"── 마감 확인 {K.TODAY}: 열림 {sum(r['alive'] is True for r in res)} · 마감 {len(closed)} · "
          f"확인 불가 {sum(r['alive'] is None for r in res)}{' (파일 반영)' if a.write else ''}")
    for r in sorted(res, key=lambda x: (x["alive"] is not False, x["alive"] is None)):
        if r["alive"] is not True:
            print(f"  {mark[r['alive']]:<5} {r['company']} — {r['title']} ({r['where']}) {r['url']} [{r['how']}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
