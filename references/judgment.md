# Agent judgment beyond the scripts

The scripts give a reproducible baseline: `scan.py` collects, `score.py` computes. They only see what was written into files. This guide is what the agent (Claude, Codex, Grok, any) adds on top: reading the whole posting and the market like a person would, then **writing the judgment down** so another agent or the user can repeat or dispute it. Nothing here needs a specific AI vendor; Firecrawl and browsers are optional helpers.

Order of authority: the user's words → `data/profile/calibration.md` → common rules (`references/scoring.md`) → this guide. A review never undoes a recorded user decision.

## 1. Reviewing a score

Run `score.py` first, then read the full body (team intro, main tasks, required, preferred, stack, process) against the user's proof (`data/profile/brief.md`, `data/experience/`). Ask:

| Question | Typical evidence | Action |
|---|---|---|
| Is the seat above the user's level? | Sr./Staff/Principal/Lead title, "주도", "company-wide", "조직 전체", years well above the user's, ownership of a whole platform | `review.delta` −0.3 … −0.5, or mark the matching required line `gap: core` if it is a stated requirement |
| What does the hiring side weigh most? | a skill named in both required and preferred, or in the team intro and most main tasks | mark that preferred line `key: true` |
| Does the daily work sit in a domain the user never touched? | the product is built around a specialised technology (LLM serving, game engine, blockchain node, codecs) | `domain_new` (scoring.md) |
| Are there conditions the gates missed? | 상주, 납품 조직, 포괄임금+야근, the same posting reposted for months | a signal if one exists, otherwise `review.delta` −0.2 … −0.5 |
| Is there a concrete upside the rules cannot see? | the posting explicitly welcomes other stacks and offers ramp-up; the team is small but the scope matches the user's proof exactly | `review.delta` +0.1 … +0.3 |

Rules:
- Write `review: { delta: <number>, why: "<공고 문장 or fact>" }` in the judgment file. `why` quotes or names the posting sentence or the user fact; "느낌상" is not a reason.
- The script limits the delta to −1.0 … +0.3 and never lets it rise above the band ceiling. Personal preferences (B2C, IaC, Go, …) already live in `signals`; do not count them again in a review.
- Prefer fixing the classification (`met`, `gap`, `key`, `fit`) over a review delta when the problem is a specific line. Use the delta for what no single line captures (level, scope, team situation).
- If a review moves a posting across 4.0 / 3.5 / 3.0, say so in the report so the user can check it.
- When the user corrects a verdict, record it in `data/profile/calibration.md` and decide whether the lesson is personal (`targets.yaml`) or common (`scoring.md` + `score.py`).

## 2. Searching beyond the scripts

`scan.py` covers the configured boards and companies. The agent widens the net where the scripts cannot reach, guided by the user's preferences in `brief.md` (for example: look harder at B2C services and at infra teams that work with IaC).

- **Browser-only companies.** `scan.py` lists every company it cannot collect, each with its reading recipe (`browse` in `sources.yaml`) and the last check. Follow the recipe directly; when a company has none, find its type in the table below, read it, and write the recipe down. Never leave these as "unscanned" when a web tool is available. Exploration may be expensive once per company (browser, Firecrawl); weekly collection must not be: whenever what was found replays with a plain request, write it as `ats`/`links`/`jsonapi` so `scan.py` collects it from then on, and keep `browse` only with the reason it cannot.

  | Page type | How to tell | How to read | Write into `sources.yaml` |
  |---|---|---|---|
  | ATS with a public API | URL, HTML, `iframe`/`script` source or page data names greenhouse, lever, ninehire, greetinghr (`__NEXT_DATA__`), hiworks, workday (`myworkdayjobs`), workable, ashby, recruiter.co.kr, roundhr, skcareers | the provider does it (`discover.py set` identifies and verifies it) | `api:` (greenhouse/lever) or `ats:` (+ `company_id` for ninehire, `code` for roundhr on a company domain) — automatic from then on |
  | Company page linking to greetinghr postings | `…career.greetinghr.com/ko/o/{id}` links in the page's plain HTML | the greetinghr provider gathers the links | `ats: greetinghr`, `careers_url` = that page |
  | Server-rendered posting links | plain `http_get` of the list page already contains each posting's link (e.g. `/detail/{n}`); `discover.py` leaves `hint: links: '…'` | the `htmllinks` provider | `links: '<posting URL regex>'` |
  | Script-rendered list, posting pages server-rendered | plain list HTML has no postings, but `robots.txt`/`sitemap.xml` lists each posting URL and a posting page has the title in `<title>` | the `htmllinks` provider | `links:` + `sitemap: '<sitemap or index URL>'` |
  | List appears only after script runs, a tab or a button (own API) | plain HTML has no postings; in a browser the page fetches a JSON list (often only after clicking "채용 공고 · 전체 · 더보기"). `discover.py probe`/`set` records it as `hint: GET/POST … → path N건 · 브라우저 없이 재현됨`; by hand, watch the network panel or the page's JS for `job · recruit · posting · notice · position` paths. A list inside the page's `__NEXT_DATA__` counts too | replay the request with `jobkit.http_get`/`http_post` (no browser) and compare the count with the site; find the detail request the same way by opening one posting | `jsonapi:` (keys in `scripts/providers/jsonapi.py`) — automatic from then on |
  | Plain fetch blocked, or the list API refuses replay | 403/429 from a WAF (also on the API), empty page even in a headless browser, a token baked into the site's script, a waiting-room ticket | do not work around it. `firecrawl_scrape` markdown with `excludeTags: [img, header, footer, nav]` on the list or keyword-search URL; `formats: ["links"]` when markdown shows titles without posting URLs; then each posting body in markdown. Use any free piece that does work (a sitemap for URLs, a guest detail API for bodies) | `browse: {url, how: firecrawl-markdown \| firecrawl-links, note: <why it stays manual>}` |
  | Company posts only on job boards | the career page says to apply through job platforms, and `scan-history.tsv` shows its postings arriving from Wanted · Jumpit · Saramin | nothing extra; check its page once a month | `browse: {url: <its board page>, how: jobboard, note}` |
  | Career URL broken or only an intro page | 404, redirect to an unrelated page, migration notice, no list | `firecrawl_search "{회사} 경력 채용"` (or a plain web search), then re-probe the found URL from the top of this table | fix `careers_url`; until then `browse: {how: search, note}` |

  Firecrawl budget: markdown and links cost 1 credit per page; `json`, `query` and `summary` cost about 5 and invent posting ids or return nothing, so do not use them for listings. The service allows roughly 10 requests a minute, so send 5 at a time. Before spending credits, try the free rows of the table.
- **Record each sweep.** Write the result per channel into `data/search/manual-checks.yaml` (format: `data/search/manual-checks.example.yaml`): `checked`, one `result` from 새 공고 · 대기함에 있음 · 맞는 공고 없음 · 일부만 확인 · 주소 깨짐 · 못 봄, a one-line `memo`, and `leads` for postings seen but not judged (no URL, no body). The posting report shows this file as its "직접 확인한 곳" and "판정 못 한 공고" sections, and a check older than 7 days counts as due again.
- **New companies.** Tech blogs, funding news, conference sponsors, and the user's targets in `brief.md`. Add them with `discover.py set` and `promote`, never by hand-editing `sources.yaml` alone.
- **Titles the filter missed.** Now and then skim `skipped_title` rows in `scan-history.tsv` (filter them out with a search; the file is over 1MB) for unusual titles that are really backend or platform roles; add the wording to `title_filter.positive` instead of rescuing rows one by one.
- **Duplicates and liveness.** Add postings found by hand through `scan.py --add` (`modes/scan.md` step 1), which checks them against `scan-history.tsv`, `pipeline.md` and `tracker.md` with the company's other spellings (`jobkit.dup_keys`). Confirm each is still open on the company's own page first.
- **Write down what was searched.** Channels checked by hand, what was found and what could not be read go into `manual-checks.yaml` (above), so the next run neither repeats nor skips them; the scan report summarises it.

## 3. Where each judgment is stored

| Judgment | File |
|---|---|
| line classification, `key`, `domain_new`, `review` | `data/search/judgments/<id>.yaml` |
| one-line reason shown in the report | `note` in the same file → `pipeline.md` |
| user corrections and their lesson | `data/profile/calibration.md` |
| personal preferences and weights | `data/profile/targets.yaml` `scoring`, summary in `brief.md` |
| new companies and channels | `data/search/companies.yaml` → `sources.yaml` via `discover.py` |
| how to read a browser-only company | `browse` (or `links` / `ats` / `api` once automatic) in `data/search/sources.yaml` |
| result of each hand check, postings seen but not judged | `data/search/manual-checks.yaml` |
