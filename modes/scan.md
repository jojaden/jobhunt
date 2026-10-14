# Mode: scan — finding postings

Collect postings from job sites, screen them once, and queue them in `data/search/pipeline.md`. Read `modes/_shared.md` first.

## Files to read

- `data/profile/brief.md`: first-pass screening criteria (if missing or still the template, build it via `modes/onboard.md` first)
- `references/scoring.md`: scoring (classification and calculation); `data/profile/calibration.md`: judgment cases the user corrected
- `references/judgment.md`: what the agent judges on top of the scripts (score review, searching where the scripts don't reach)

Only when needed: `data/search/sources.yaml` (filters, `priority: true` companies, `browse` recipes) and `references/sources.md` (per-site endpoints, body location, closing check; when a channel breaks or a company is added).

Never read `data/search/scan-history.tsv` (over 1MB), `data/search/pipeline.md` or `data/applications/tracker.md` whole. The scripts do duplicates, cooldown and exclusions (`scan.py`, also `--add`) and move lines (`score.py apply`, `tracker.py`). For a single lookup, search the file for the url or company name.

## Steps

0. **Widen companies (once a month, or when the user says "회사 더 찾아줘").** Run `jobhunt discover collect → probe → promote --dry-run` per "Company discovery" in `references/sources.md`, show the user the table of companies to add, then `promote`. New companies are collected from the next `scan.py` run (ask about `--seed` the first time).

1. **Collect.** Run `jobhunt scan` first. It fetches Wanted · Jumpit · LinkedIn · Saramin · Greenhouse · Lever · Toss · NHN · Kakao · greetinghr · ninehire and plain-HTML career pages, finishes steps 2–3 and the logging, puts new postings under "새로 수집 (선별 전)" in `pipeline.md`, and puts bodies in `data/search/inbox/`.
   - Collect only the channels the output lists as "스크립트 미지원" (JobKorea, Remember, browser-only companies) by hand. Each line already shows its reading recipe (`browse` in `sources.yaml`) and last check; follow it, or for a company without one use the per-type table in `references/judgment.md` §2 and save the recipe. Write what you found to a yaml list (e.g. `data/search/found.yaml`) and run `jobhunt scan --add <file>`: each item has `url`, `company`, `title`, `source` (`jobkorea`, `firecrawl:<company>`, …) and optionally `location`, `career: [min, max]`, `posted_at`, `closes_at`, `text` (the body: qualifications, preferred, main tasks). It runs step 2 on them except the title filter (you chose them by reading), logs them in `scan-history.tsv`, writes the bodies to `inbox/` and adds the survivors under "새로 수집 (선별 전)". Write each channel's result to `data/search/manual-checks.yaml`. When a free path turns up, switch the company to automatic collection (`api` / `ats` / `links`) instead.
   - Then widen the search by hand per `references/judgment.md` §2 (browser-only companies, new companies, titles the filter missed), leaning toward the user's preferences in `brief.md`.
   - A channel marked `✗` means its response shape changed. Report it instead of passing it off as 0 results; once confirmed, offer to file it with the "수집기 응답 형식 변경" issue template (in a repository clone, fix `scripts/providers/` and `references/sources.md`).
   - A channel marked `⚠ 일부만` stopped on a rate limit (e.g. LinkedIn 429) after part of its results. Report it as partly scanned with the reason. Don't retry or work around it; what was missed isn't logged, so the next run fetches it.
   - If a first run piles up too many postings, ask the user about `--seed` (record current postings as seen only).
   - Priority companies (`priority: true`) are always scanned in full.
2. **First filter** (`scan.py` does this, also for postings given with `--add` except the title rule; listed so you can explain why a posting was dropped):
   - Title: must contain one of `title_filter.positive`; contains a `negative` → exclude.
   - Location: `location_filter.block` → exclude. If unclear, pass it and mark `[근무지 확인 필요]`.
   - Duplicates: skip if the url is in `scan-history.tsv`, `pipeline.md`, or `tracker.md`. The same company + same position title also counts as a duplicate (`jobkit.dup_keys`: company matched by any of its spellings — inside/outside parentheses, `A - B`, never a legal-form marker like `(주)`; title compared without symbols, spaces, 채용·모집·영입, or a leading `[company]` tag, with 개발자 read as 개발. Team names in parentheses are kept so different openings don't merge).
   - Possible duplicates are kept, not dropped (`jobkit.near_dup`, postings on different sites only: same company with a near-identical title, or the same title at a company whose name starts the same, like an affiliate or a renamed company). The line gets `[같은 공고일 수 있음]` and the body's header names the other posting. When a company was renamed or a site shows the parent company's name for the same posting, add the other spelling to `company_aliases` in `sources.yaml`; don't alias affiliates to each other, since they post different openings.
   - Excluded companies (`blacklist.md`); reapply cooldown (a company within `reapply_days` of `targets.yaml` after a `지원함` in `tracker.md`).
   - Years: if the posting states a number of years, apply `career_filter` from `sources.yaml`.
3. **Fetch bodies.** Fetch the full detail (qualifications, preferred, main tasks) of the remaining postings. Expand umbrella postings down to their sub-positions (for Toss the script gathers sub-links at the end of the body).
4. **First-pass screening.** For each posting under "새로 수집 (선별 전)", follow `references/scoring.md` in order. Never estimate a score. Read only that section (top of `pipeline.md`, up to the next `## ` heading); each line ends with its body file in `inbox/`.
   - Scaffold with `jobhunt score init <inbox body> -o data/search/judgments/<source>_<id>.yaml`, then fill every line's classification (fit · met · gap) plus `key: true` on preferred lines that are core skills of the position, direction, gates, signals, and `domain_new` (a specialised technical domain the team's product is built around that the user has never worked in, e.g. LLM serving). The `언어:` hint at the end of a line is only a hint; judge conditions from the qualification sentences.
   - If an exclusion gate hits, write only `fail` and the evidence sentence under `gates` and skip line classification.
   - `init` pre-fills `gates.stack: fail` (with `gate_note` and a `draft` key) only when a qualification line demands a language outside `gates.stack_languages` in `targets.yaml` with no open list or substitute clause. Check that line in the body: if it really is a hard requirement, keep it, delete `draft` and skip line classification; if not (a team-stack listing, a misplaced preferred line), clear `stack` and `gate_note`, delete `draft` and classify as usual. Postings without a draft still get every gate judged.
   - If the body's header has `같은 공고일 수 있음`, compare it with that posting's body. If it is the same opening, copy that posting's judgment file (keep this posting's `url` and `source`) instead of judging it again, so the two never get different scores.
   - If a posting resembles a case in `calibration.md`, classify it the same way.
   - Score with `jobhunt score data/search/judgments/<file>.yaml`, then review it with `references/judgment.md` §1; record any adjustment as `review` in the judgment file and re-run. Use the resulting score and verdict as is. 3.5+ `PASS`, 3.0–3.4 `MARGINAL`, below `FAIL`.
   - Priority companies (`priority: true` in `sources.yaml`) get `priority: true` in the judgment file (bonus only, no automatic PASS).
   - Write a one-line reason in `note` (for a gate fail, in `gate_note`); step 5 copies it into `pipeline.md`.
5. **Record.**
   - Run `jobhunt score apply data/search/judgments/<file>.yaml ...` with the files screened this time. It takes their lines out of "새로 수집 (선별 전)", puts PASS and MARGINAL in "대기" by score and FAIL in "제외 (선별 YYYY-MM-DD)", each with the reason from the judgment file. Don't move lines by hand.
   - For closing checks run `jobhunt alive --write` (closed queued postings go to "마감 확인 (날짜)", tracker rows in 평가함 become 포기). Open `확인 불가` ones in a browser.
6. **Report.** Build the HTML posting report with `jobhunt report` and show it as described in SKILL.md "Showing the posting report" (rows found since the previous report get a 신규 tag). In text-only hosts show `jobhunt tracker report --since <last scan date>` (table format below) instead, and add per-channel counts and unscanned channels. Full evaluation only for postings the user picks, via `modes/evaluate.md`.
   - Per-channel counts (including 0), exclusion counts per condition, unscanned and partly scanned (`⚠ 일부만`) channels and why. The HTML report carries the hand-checked channels and the postings not yet judged as its own sections (from `manual-checks.yaml` and "새로 수집 (선별 전)").
   - One table: postings newly found this time + postings already evaluated or screened that are still open. Keep evaluated and recommended postings in the same table.

     | 회사 | 포지션 | 근무지 | 점수 | 판정 | 지원 여부 | 새로 찾음 | 마감 | 한 줄 근거 |
     |---|---|---|---|---|---|---|---|---|

     `지원 여부` comes from `tracker.md` (지원함 / 미지원); `판정` is the evaluation score if there is one, otherwise the first-pass result.

## pipeline.md format

Scripts parse these headings and markers; keep them verbatim.

```markdown
## 새로 수집 (선별 전)
- [ ] {url} | {회사} | {포지션} | {근무지} | 선별 전 | {출처} · {수집일} · 마감 {날짜} | 언어: {힌트} | 본문: data/search/inbox/{파일}

## 대기
- [ ] {url} | {회사} | {포지션} | {근무지} | triage: {PASS|MARGINAL} {점수}/5 ({선별|재채점} {날짜}) | {한 줄 근거} | 판정: {판정 파일}

## 제외 (선별 YYYY-MM-DD)
- [x] {url} | {회사} | {포지션} | FAIL {점수} ({선별|재채점} {날짜}) | {판정 근거 문장}

## 지원 완료 — 재지원 쿨다운
## 마감 확인
## 처리 완료
```

## scan-history.tsv columns

`url  first_seen  portal  title  company  status  location  fingerprint  posted_at  trust_score  trust_flags  normalized_company` (tab-separated). Trailing columns may be empty. Read columns by name.

## Weekly scan

`jobhunt weekly` runs collect → closing check → combined report in one go and saves `data/search/reports/YYYY-MM-DD.md` (no LLM; fine to run from cron or launchd). Then continue from step 4 (first-pass screening).
If the user asks "주기적으로 찾아줘", register `jobhunt weekly` with `/loop` or cron/launchd running on this machine (cloud `/schedule` cannot reach this machine's `data/`). Write the registered interval into `data/preferences/standing.md`.
