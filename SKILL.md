---
name: jobhunt
description: Korean developer job search, end to end — finds postings (Wanted, Jumpit, LinkedIn, Saramin, JobKorea, company career sites), scores them against the user's experience, builds a tailored resume A4 PDF, writes cover-letter answers, researches the company, prepares and drills interviews, and logs results. Use for finding or evaluating postings, a company-specific resume or cover letter, interview prep or mock interviews, and application status.
argument-hint: "[menu | onboard | scan | report | prep | evaluate <url> | tailor | cover | interview [plan|practice|debrief] | track | outcome]"
---

# Find postings → evaluate → apply → interview — router

Resume content lives in yaml; layout and build are `jobhunt render`. All personal data lives in `data/` of the jobhunt home folder and never goes to git.
Save every fact, requirement, or judgment correction the user gives into the matching file under `data/` right away, so the next run reuses it. Screening and tailoring get sharper with use.
Full design: `docs/ROADMAP.md`.

**Language.** These instruction files are English for the agent only. Everything the user sees is Korean: replies, questions, reports, tables and their headings, files written under `data/`, and resume text. Korean strings quoted in these files (state values, section headings, templates, example sentences) are used verbatim.

## Where things are

Two folders, never mixed:

- **Skill folder**: the folder holding this SKILL.md, with `modes/`, `references/`, `examples/` and `docs/`. It is installed with the tool (`uv tool install`) and replaced on every update, so never write into it. `modes/…` and `references/…` paths are relative to it.
- **jobhunt home**: the user's folder (default `~/jobhunt`, picked at install or set with `JOBHUNT_HOME`; `jobhunt where` prints it). Personal data lives in its `data/`, and every `data/…` path is relative to it.

Commands are `jobhunt <command>` (`jobhunt --help`). In a clone of the repository (working on the tool itself) use `python3 scripts/cli.py <command>` instead, so the clone's own code runs: the skill folder is the repository root, and so is the home unless `JOBHUNT_HOME` is set (`python3 scripts/cli.py where` shows which).
Changing the tool itself (`scripts/`, `modes/`, `references/`, `style_rules.yaml`) happens only in such a clone and goes upstream as a pull request (`CONTRIBUTING.md`). On an installed tool, tell the user what should change and offer to file an issue (https://github.com/jojaden/jobhunt/issues/new/choose) instead of editing the skill folder.

```
SKILL.md                    this file (routes to modes)
modes/_shared.md            shared rules, sources of truth, data/ file map, Korean hiring terms (always read first)
modes/onboard.md            first-time setup, personalization file check
modes/scan.md               finding postings and first-pass screening
modes/evaluate.md           evaluating a posting (gates, requirement map, tailoring plan)
modes/tailor.md             writing, building, and reviewing a tailored resume
modes/cover.md              cover letter and application-form answers
modes/prep.md               preparing a chosen posting: company and role research, stages and tests, likely questions, what to prepare → page linked from the report
modes/interview.md          interview plan · practice drill · debrief · red flags
modes/track.md              application tracker
modes/outcome.md            patterns across results and debriefs → rule changes
jobhunt render              yaml → HTML → PDF + PNG, designs A/B/C, runs post-build checks
jobhunt check               page count · orphaned headings · links · placeholders · style checks
jobhunt check-links         link reachability
jobhunt git-log             author-filtered commit log from a local git repository
jobhunt setup               skill link into installed agents (~/.claude/skills, ~/.codex/skills, or SKILLS_DIR) + Playwright Chromium, fonts (Pretendard, Noto Sans/Serif CJK KR), poppler; on an installed tool it also prepares the home folder
jobhunt scan                posting collection (Wanted · Jumpit · LinkedIn · Saramin · Remember · Greenhouse · Lever · Toss · NHN · Kakao · Naver · Baemin · LINE · greetinghr · ninehire · plain-HTML career pages) → filters → pipeline.md; `--add` for postings found by hand
jobhunt alive               closing check for tracked postings
jobhunt tracker             application log (add/set) and combined report table (report)
jobhunt score               posting score (line-level judgment file → per-item scores)
jobhunt cover-check         cover-letter answers: character counts per limit + style rules
jobhunt report              posting report as one HTML file, plus a page per prepared posting
jobhunt company             company numbers as YAML lines for a prep file: the Wanted company page without a key; with the user's keys also 국민연금 (headcount, salary estimate, hires and leavers) and DART (CEO, yearly revenue and operating profit from 사업보고서 or 감사보고서)
jobhunt keys                the user's own API keys (공공데이터포털, OpenDART): status, how to get them, `set <name>` to store one
jobhunt discover            company discovery (tech blogs · GitHub · Wanted · known companies → career site and ATS detection → sources.yaml)
jobhunt weekly              the LLM-free part of the weekly scan (scan → alive → report)
jobhunt update              update the tool to the new version (installed: fetch and install again; a clone on main: git pull); data and skill links stay
jobhunt where               where the jobhunt home and the skill folder are
references/sources.md       per-site collection method (endpoints, body location, closing check)
references/scoring.md       posting scoring (classification, calculation, calibration)
references/judgment.md      what the agent judges beyond the scripts (score review, searching where scripts can't reach)
references/company_seed.yaml default candidates for company discovery (well-known Korean dev companies)
references/yaml_schema.md   resume yaml format
references/writing_rules.md sentence rules and how to check them
references/style_rules.yaml banned words · translationese · symbol limits (read by check.py)
references/resume_guide.md  general resume rules (project count, numbers, links …)
references/cover_letter.md  cover-letter structure, banned content, length
references/interview_questions.md how interviewers ask: question styles, follow-up patterns, answer shapes, topic map
examples/example.yaml       fictional example person
docs/ROADMAP.md             design and stages
data/                       user data, in the jobhunt home (never in git; only the structure is published)
  profile/ experience/ preferences/ portfolio/ search/ job_postings/ applications/ resumes/ output/ interview/
```

## On start

1. Run `jobhunt where` (in a repository clone, `python3 scripts/cli.py where`) and work from the jobhunt home it prints. If `jobhunt` is missing, ask the user to install it with the one-line installer in the README ("설치"). If this environment cannot reach the user's machine (a cloud workspace, say), ask the user to connect the home folder.
2. Read `modes/_shared.md`.
3. Run the session-start check in `modes/onboard.md`. Tell the user about any missing personalization file.
4. Read `data/preferences/standing.md`. Anything already decided there is settled; use it without asking again.
5. If the host attaches project files to this session (e.g. a Claude project, a Codex workspace), also check the finalized yaml and guide documents there.

## Modes

This skill is one router over several modes; they share `data/`, so one entry point keeps the steps connected. Pick the mode from the argument when the host passes one (`/jobhunt interview practice`), otherwise from the request. Hosts without slash commands get the same result from "jobhunt 의 interview 모드로 …".

| Argument | Example request | Mode |
|---|---|---|
| (none), `menu` | "뭐 할 수 있어?", "메뉴" | show the menu below |
| `onboard` | "처음 설정", "내 조건 바꿀래", "목표 역할 추가" | `modes/onboard.md` |
| `scan` | "공고 찾아줘", "새 공고 있어?", "주간 스캔" | `modes/scan.md` (run `jobhunt weekly` first) |
| `scan discover` | "회사 더 찾아줘", "수집 회사 넓혀줘" | `modes/scan.md` step 0 (`jobhunt discover`) |
| `scan triage` | "새로 수집한 공고 선별해줘" | `modes/scan.md` from step 4 |
| `report` | "공고 현황 보여줘", "표로 보여줘" | `jobhunt report`, then "Showing the posting report" below |
| `prep` | "A사, B사 준비해줘", "이 공고 준비하자", "면접 대비 자료 만들어줘" | `modes/prep.md` |
| `evaluate` | a posting URL or body, "이 공고 어때?" | `modes/evaluate.md`, then the auto flow below |
| `tailor` | "이 공고용 이력서 만들어줘", "이력서 고쳐줘", "다시 빌드" | `modes/tailor.md` (no evaluation yet → offer evaluate first) |
| `cover` | "자소서 써줘", "지원서 문항 답 써줘" | `modes/cover.md` |
| `deep` | "이 회사 조사해줘", "어떤 회사야?" | `modes/prep.md` step 2 only (company part of the prep file) |
| `interview plan` | "면접 준비", "prep {회사}" | `modes/interview.md` plan |
| `interview practice` | "모의 면접", "예상 질문으로 연습", "꼬리질문 해줘" | `modes/interview.md` practice |
| `interview debrief` | "면접 봤어", "면접에서 이런 질문 받았어" | `modes/interview.md` debrief |
| `track` | "지원했어", "서류 붙었어", "떨어졌어", "지원 현황" | `modes/track.md` (`jobhunt tracker`) |
| `outcome` | "결과 분석해줘", "왜 자꾸 떨어지지" | `modes/outcome.md` |

### Menu

Shown in Korean when no mode is given: one line per mode with its argument and an example request, grouped as 공고 찾기 (`scan`, `report`) · 지원 준비 (`prep`, `evaluate`, `tailor`, `cover`) · 면접 (`interview plan|practice|debrief`) · 기록·학습 (`track`, `outcome`, `onboard`). End with the next step that fits the user's current state (e.g. new postings waiting to be screened, an interview scheduled in the tracker memo).

### The flow

scan → report → **the user picks postings** → prep for each (evaluate first if needed; the report gets a "준비 자료" page per posting) → ask "이 공고에 맞춰 이력서를 준비할까요?" → on request tailor, then cover if the form has questions → track `지원함` → (document pass) interview plan from the prep file → interview practice → debrief after each stage.

After showing the report, end with this next step: ask which postings to prepare. Given a single posting URL or body with no other instruction, start at evaluate and continue with prep. Confirm with the user between steps; never submit anything on the user's behalf.

### Showing the posting report

The report is one self-contained HTML file so any agent (Claude Code, Codex, Grok, …) and any browser can open it. How to put it in front of the user depends on the host, never the other way round:

- Host that can publish HTML pages (e.g. Claude Artifacts): also write the skeleton-less version with `--fragment <path>` and publish that file; keep publishing to the same page so the link stays. Prepared postings add one full page each: the report prints them as `함께 올릴 쪽: prep/<name>.html ← <file>`; publish each alongside the report at that `prep/<name>.html` path so the row's "준비 자료" link opens it.
- Any other host: open `data/search/reports/postings.html` in the user's browser (`open` on macOS) or give the path.
- Text-only fallback: `jobhunt tracker report --alive` prints the same rows as a Markdown table.

Do not hand-write report HTML or restyle it per session; change `scripts/report_html.py` and `DESIGN.md` together when the design changes.

