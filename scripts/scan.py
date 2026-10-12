# -*- coding: utf-8 -*-
"""공고 수집 (LLM 호출 없음). modes/scan.md 의 1~3단계와 5단계 기록을 자동으로 한다.

  python3 scripts/scan.py                 켜진 채널 전부
  python3 scripts/scan.py --only wanted,linkedin,toss
  python3 scripts/scan.py --dry-run       파일을 쓰지 않고 결과만 출력
  python3 scripts/scan.py --no-detail     본문을 받지 않음 (빠름, 1차 선별 불가)
  python3 scripts/scan.py --seed          지금 열린 공고를 "본 것"으로만 기록 (대기함에 넣지 않음, 다음 실행부터 새 공고만)
  python3 scripts/scan.py --add 찾은공고.yaml   손으로 찾은 공고를 중복 확인·필터(제목 필터 빼고)에 넣고 기록 (채널 수집은 안 함)

결과
  data/search/pipeline.md   "## 새로 수집 (선별 전)" 섹션에 추가 → AI 에이전트가 brief.md 로 1차 선별
  data/search/inbox/*.md    공고별 본문 (자격요건·우대·주요업무) + 언어 요건 힌트
  data/search/scan-history.tsv  본 공고 전부 (중복 제거용)

스택 조건으로는 거르지 않는다(판정 단계에서만, standing.md). 언어 힌트는 참고용이다.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from types import SimpleNamespace
from urllib.parse import urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import jobkit as K  # noqa: E402
import providers  # noqa: E402

NEW_HEADER = "## 새로 수집 (선별 전)"


def plan(sources: dict, only):
    """(이름, 모듈, cfg) 목록과 스크립트가 못 도는 (이름, cfg) 목록."""
    runs, manual = [], []
    for name, cfg in (sources.get("boards") or {}).items():
        if not cfg.get("enabled"):
            continue
        mod = providers.BOARDS.get(name)
        (runs.append((name, mod, cfg)) if mod else manual.append((name, cfg)))
    for c in sources.get("companies") or []:
        mod = providers.for_company(c)
        (runs.append((c["name"], mod, c)) if mod else manual.append((c["name"], c)))
    if only:
        keep = set(only)
        runs = [r for r in runs if r[0] in keep or r[1].__name__.split(".")[-1] in keep]
    return runs, manual


def added(path: str):
    """--add 파일 → 출처 하나처럼 도는 (이름, 모듈, cfg). 항목: url · company · title · source 필수,
    location · career [최소, 최대] · posted_at · closes_at · text(본문) 선택. 본문은 받지 않고 적힌 그대로 쓴다.
    제목 필터는 걸지 않는다: 에이전트가 읽고 고른 공고라, 필터에 없는 제목(예: "웹 애플리케이션 엔지니어")도 넣을 수 있어야 한다."""
    if not os.path.exists(path):
        sys.exit(f"{path} 이 없습니다.")
    jobs = []
    for it in K.load_yaml(path) or []:
        jobs.append(K.Job(source=it["source"], id=hashlib.sha1(it["url"].encode()).hexdigest()[:10], url=it["url"],
                          company=it["company"], title=it["title"], location=it.get("location") or "",
                          posted_at=str(it.get("posted_at") or ""), closes_at=str(it.get("closes_at") or ""),
                          text=it.get("text") or "", extra=dict(career=it.get("career"))))
    mod = SimpleNamespace(__name__="added", collect=lambda cfg: jobs, detail=lambda j: j.text)
    return [("직접 찾음", mod, {})]


def _collect(run, seen_urls):
    """(공고 목록, 오류). 한 채널이 깨져도 나머지는 돈다. seen_urls 는 상세를 공고마다 받는 공급원이 본 공고를 건너뛰는 데 쓴다."""
    try:
        return run[1].collect(dict(run[2], seen_urls=seen_urls)), None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def _detail(mod, j):
    try:
        j.text = mod.detail(j)
    except Exception as e:
        j.text = f"[본문 받기 실패: {type(e).__name__}: {e}]"


def main(argv=None):
    ap = argparse.ArgumentParser(description="공고 수집")
    ap.add_argument("--only", help="쉼표로 구분한 채널·회사·공급원 이름")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-detail", action="store_true")
    ap.add_argument("--seed", action="store_true")
    ap.add_argument("--add", metavar="YAML", help="손으로 찾은 공고 목록 (형식은 added() 설명)")
    a = ap.parse_args(argv)
    if a.seed:
        a.no_detail = True

    sources = K.load_yaml(K.P["sources"])
    if not sources:
        sys.exit("data/search/sources.yaml 이 없습니다. sources.example.yaml 을 복사해 만드세요 (modes/onboard.md).")
    targets = K.load_yaml(K.P["targets"])
    tf, lf = sources.get("title_filter") or {}, sources.get("location_filter") or {}
    cf = sources.get("career_filter") or {}

    seen = {r["url"] for r in K.read_history()} | K.pipeline_urls()
    tracked = {k for r in K.read_tracker() for k in K.dup_keys(r["company"], r["role"])} | K.pipeline_keys()
    cool = K.cooldown_companies(int(targets.get("reapply_days", 183)))
    black = K.blacklist_companies()

    runs, manual = (added(a.add), []) if a.add else plan(sources, a.only.split(",") if a.only else None)
    stats, errors, fresh, hist = {}, {}, [], []
    reasons = Counter()
    batch_keys = set()
    # 출처마다 스레드 하나. 같은 사이트 요청은 jobkit.http_get 이 한 번에 하나씩, 간격을 두고 보낸다
    pool = ThreadPoolExecutor(max(len(runs), 1))
    known = frozenset(seen)
    futures = [pool.submit(_collect, r, known) for r in runs]
    # 본문은 사이트마다 줄 하나(스레드 하나)로 받는다. 앞 출처가 끝나는 대로 시작해 다른 출처 수집과 겹친다
    lanes, pending = {}, []
    try:
        # 결과는 출처 순서대로 처리한다 (중복 판정이 앞 출처 우선이라, 차례로 돌 때와 결과가 같다)
        for (name, mod, _), fut in zip(runs, futures):
            jobs, err = fut.result()
            if err:
                errors[name] = err
                continue
            n_new = 0
            for j in jobs:
                status = None
                keys = K.dup_keys(j.company, j.title)
                url_seen = j.url in seen
                if url_seen or keys & tracked or keys & batch_keys:
                    status = "skipped_dup"      # 다른 사이트에 올라온 같은 공고도 URL은 기록해 둔다 (다음 실행에서 다시 안 나오게)
                elif not a.add and K.title_ok(j.title, tf):
                    status = "skipped_title"
                elif K.career_check(j.extra.get("career"), cf):
                    status = "skipped_career"
                elif K.location_check(j.location, lf) == "block":
                    status = "skipped_location"
                elif K.company_in(j.company, black):
                    status = "skipped_blacklist"
                elif K.company_in(j.company, cool, exact=True):
                    status = "skipped_cooldown"
                elif a.seed:
                    status = "seeded"
                batch_keys |= keys
                if not url_seen:
                    seen.add(j.url)
                    hist.append(dict(url=j.url, first_seen=K.TODAY, portal=j.source, title=j.title, company=j.company,
                                     status=status or "added", location=j.location, posted_at=j.posted_at,
                                     normalized_company=K.norm_company(j.company)))
                if status:
                    reasons[status] += 1
                    continue
                n_new += 1
                fresh.append((mod, j))
                if not a.no_detail:
                    key = K.site(urlsplit(j.url).netloc)
                    if key not in lanes:
                        lanes[key] = ThreadPoolExecutor(1)
                    pending.append(lanes[key].submit(_detail, mod, j))
            stats[name] = (len(jobs), n_new)

        for i, _ in enumerate(as_completed(pending), 1):
            if i % 25 == 0:
                print(f"  … 본문 {i}/{len(pending)}", file=sys.stderr)
    except KeyboardInterrupt:
        # 파일은 수집이 다 끝난 뒤에 쓰므로 남는 것이 없다. 도는 수집 스레드를 기다리지 않고 바로 끝낸다
        print("\n중단 — 쓴 파일 없음", file=sys.stderr, flush=True)
        os._exit(130)
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
        for lane in lanes.values():
            lane.shutdown(wait=False, cancel_futures=True)

    if not a.no_detail:
        for _, j in fresh:
            # 본문을 받은 뒤 근무지가 구체화되면 다시 본다. 공급원이 본문을 보고 뺄 수도 있다 (예: LinkedIn 영어 전용 JD)
            if not j.extra.get("skip") and K.location_check(j.location, lf) == "block":
                j.extra["skip"] = "skipped_location"

    fresh_ok = [(m, j) for m, j in fresh if not j.extra.get("skip")]
    late = {j.url: j.extra["skip"] for _, j in fresh if j.extra.get("skip")}
    for why in late.values():
        reasons[why] += 1
    for h in hist:
        if h["url"] in late:
            h["status"] = late[h["url"]]

    lines = []
    for _, j in fresh_ok:
        loc = j.location or "?"
        tag = " [근무지 확인 필요]" if K.location_check(j.location, lf) == "unknown" else ""
        hint = K.stack_hint(j.text) if j.text else "본문 없음"
        raw = ""
        if not a.dry_run and not a.no_detail:
            os.makedirs(K.P["inbox"], exist_ok=True)
            fn = f"{K.TODAY}_{j.source.replace(':', '-')}_{j.id}.md"
            with open(os.path.join(K.P["inbox"], fn), "w", encoding="utf-8") as f:
                f.write(f"# {j.company} — {j.title}\n\n- URL: {j.url}\n- 출처: {j.source}\n- 근무지: {loc}\n"
                        f"- 게시: {j.posted_at or '?'} · 마감: {j.closes_at or '?'}\n- 수집: {K.TODAY} (scripts/scan.py)\n"
                        f"- 언어 요건 힌트: {hint}\n\n{j.text}\n")
            raw = f" | 본문: data/search/inbox/{fn}"
        lines.append(f"- [ ] {j.url} | {j.company} | {j.title} | {loc}{tag} | 선별 전 | {j.source} · {K.TODAY}"
                     f" · 마감 {j.closes_at or '?'} | 언어: {hint}{raw}")

    if not a.dry_run:
        if lines and not a.seed:
            md = K.read_text(K.P["pipeline"]) or "# 공고 대기함\n"
            K.write_text(K.P["pipeline"], K.insert_under(md, NEW_HEADER, lines, before="## 대기"))
        if hist:
            K.append_history(hist)

    # 보고
    print(f"── 공고 수집 {K.TODAY} {'(dry-run: 파일 안 씀)' if a.dry_run else ''}")
    for name, (n, new) in stats.items():
        print(f"  {name:<22} 받음 {n:>4} · 새 공고 {new}")
    for name, err in errors.items():
        print(f"  {name:<22} ✗ {err}")
    if manual:
        checks = K.load_yaml(K.P["checks"])
        print("  스크립트 미지원 — 아래 읽는 법(sources.yaml browse)대로 확인하고 결과는 manual-checks.yaml 에 (references/judgment.md §2):")
        for name, cfg in manual:
            b, last = cfg.get("browse") or {}, checks.get(name) or {}
            print(f"    {name:<20} {b.get('how') or '읽는 법 없음'} {b.get('url') or cfg.get('careers_url') or ''}"
                  + (f" · 지난 확인 {last.get('checked')} {last.get('result')}" if last else ""))
    print("  제외: " + (", ".join(f"{k} {v}" for k, v in sorted(reasons.items())) or "없음"))
    print(f"  새로 추가: {len(lines)}건 → {'pipeline.md ' + NEW_HEADER if not a.dry_run else '(dry-run)'}")
    for l in lines[:40]:
        print("   " + re.sub(r" \| 본문: .*$", "", l)[6:])
    if len(lines) > 40:
        print(f"   … 외 {len(lines) - 40}건")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
