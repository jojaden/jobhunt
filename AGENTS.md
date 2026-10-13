# AGENTS.md

Guidance for any AI coding agent working in this repository — Codex, Claude Code, Grok, Gemini, Cursor, or another. This file is the single source; `CLAUDE.md` only imports it. Nothing here depends on one vendor. The human-facing contributor guide is `CONTRIBUTING.md` (Korean); keep its procedures consistent with this file.

## What this repository is

Two things in one folder:

- **An agent skill** (`jobhunt`, the open `SKILL.md` format): `SKILL.md` is a router: a mode argument or the request picks a mode file in `modes/` (onboard · scan · evaluate · tailor · cover · deep · interview · track · outcome). Users install it as a tool (`uv tool install`, via `install.sh`): `jobhunt setup` links the installed package folder (which carries `SKILL.md`, `modes/`, `references/`) into the agents' skill folders, and personal data lives apart in the jobhunt home (`~/jobhunt/data`). In this repository `scripts/setup.sh` links the repo itself instead, so edits here are live immediately; agents that don't load skills run in the folder and follow `AGENTS.md` (an installed home gets a short `AGENTS.md` pointing at the installed skill).
- **LLM-free Python scripts** under `scripts/` that do everything not needing judgment: collecting Korean job postings, closing checks, the application tracker, scoring arithmetic, company discovery, and resume PDF builds.

If the user asks to find/evaluate postings, write a resume or cover letter, prepare for an interview, or log an application, that is *using* the skill: follow `SKILL.md` (read `modes/_shared.md` first). If they ask to change the tool itself, you are editing the scripts/modes below.

## Running under different agents

The workflow is plain files plus Python, so every agent follows the same steps. What differs is only how the agent is started and which optional helpers the host offers.

| Agent | How it picks this up |
|---|---|
| Codex | reads `AGENTS.md` when started in the folder; `jobhunt setup` (or `scripts/setup.sh` in the repo) also links the skill into `~/.codex/skills` |
| Claude Code | `CLAUDE.md` imports `AGENTS.md`; `jobhunt setup` (or `scripts/setup.sh`) links the skill into `~/.claude/skills` |
| Grok, Gemini, Cursor, others | start the agent in this folder and point it at `AGENTS.md` (most read it on their own); if the host loads `SKILL.md` skills, set `SKILLS_DIR` for `jobhunt setup` |

In-repo pointers `.agents/skills/`, `.grok/skills/`, `.cursor/skills/` hold a thin `SKILL.md` that sends the agent to the root `SKILL.md`, so those agents find the skill without `setup.sh`. Keep their frontmatter (`name`, `description`, `argument-hint`) identical to the root `SKILL.md` when it changes. The Claude Code and Codex plugin works the same way: `.claude-plugin/marketplace.json` lists `plugin/`, whose only skill (`plugin/skills/jobhunt/SKILL.md`) sends the agent to the installed skill folder from `jobhunt where` (Codex reads the same Claude-format marketplace). It carries no instructions of its own, so they never drift from the installed scripts, and `setup.sh` makes no skill link for an agent that has the plugin (a test keeps its frontmatter equal to the root `SKILL.md` and its version equal to `pyproject.toml`).

Host features are optional add-ons, never requirements:
- **Publishing HTML** (e.g. Claude Artifacts): the posting report is one HTML file; publish the `--fragment` version where the host can, otherwise open the file or give its path (`SKILL.md` "Showing the posting report").
- **Web fetching / search** (Firecrawl MCP, a browser tool): used only for channels the scripts can't reach (`references/judgment.md` §2). Without them, report those channels as unscanned.
- **Question / choice UI:** ask in plain text when the host has none.

Write instructions for the agent in neutral terms ("the agent", "the host"); name a vendor only as an example of an optional feature.

## Commands

No build step. Lint with ruff (`ruff.toml`: mistakes only, pyflakes · syntax · bugbear, no formatting rules; a dev tool, not a dependency of the scripts). Run the offline tests (`tests/`, stdlib `unittest`) after any change to `scripts/`, then the affected script itself. CI (`.github/workflows/test.yml`) runs them on every PR and push to main (Ubuntu and macOS × Python 3.10 and 3.12, plus shell syntax and ruff), on Ubuntu installs through `setup.sh --no-skill` and builds `examples/example.yaml` in designs A, B, C, and builds the wheel, installs it with `uv tool install` and runs `jobhunt` outside the repo. Python 3.10+, deps in `requirements.txt` and `pyproject.toml` (keep both lists the same) (PyYAML, playwright, pdf2image, pdfplumber); `bash scripts/setup.sh --no-skill` installs them plus Chromium, Korean fonts (Pretendard, Noto CJK KR), and poppler. `install.sh` at the repo root is the one-line installer users run with `curl … | bash`: it installs uv if missing, runs `uv tool install git+…` (Python 3.12), moves an old git install out of the way (tracked files and `.git` into `~/jobhunt/.old-repo/`, `data/` stays, a schedule calling the old `scripts/weekly.sh` keeps working through a small forwarding file), then runs `jobhunt setup` and prints the CHANGELOG lines since the previous version (`jobhunt changes`); releases are git tags (`v1.0.0`). `pyproject.toml` packages `scripts/` as the `jobhunt` package (with `references/`, `modes/`, `examples/`, `SKILL.md` and the tracked `data/` skeleton; ignored personal files never go in) and gives the `jobhunt <command>` entry point (`scripts/cli.py`, which runs the same scripts: `jobhunt scan` = `python3 scripts/scan.py`). Supported hosts: macOS (Homebrew), Debian/Ubuntu (apt), and Windows through WSL2 Ubuntu — on Windows the repo, the scripts, and the agent all run inside WSL (clone under `~`, not `/mnt/c`).

```bash
# lint (pip install "ruff>=0.16,<0.17"; the pre-commit hook also runs it on staged .py files when ruff is installed)
ruff check .

# tests: no network, never touch data/ (tests/support.py points jobkit.P at a temp dir)
python3 -m unittest discover -s tests
python3 -m unittest discover -s tests -k wanted    # one provider

# resume build (yaml → HTML → A4 PDF + per-page PNG, then runs check.py)
python3 scripts/render.py examples/example.yaml --profile data/profile/profile.example.yaml --offline
python3 scripts/render.py <yaml> --design A|B|C --out DIR --no-png --no-check
python3 scripts/check.py <resume.yaml> [pdf] [--offline]      # page count, orphan headings, links, placeholders, style
python3 scripts/check_links.py <url>... | --pdf <pdf>

# the same scripts as one command (installed with uv tool, or `python3 scripts/cli.py` in the repo)
jobhunt --help;  jobhunt where    # where it reads personal data: JOBHUNT_HOME > the repo root when run from a checkout > ~/jobhunt

# posting collection
python3 scripts/scan.py --dry-run                 # no file writes
python3 scripts/scan.py --only toss,wanted        # filter by provider module name or sources.yaml board/company name
python3 scripts/scan.py --no-detail | --seed
python3 scripts/scan.py --add <found.yaml>             # postings found by hand: dedup, filters except title, logging as collected ones
python3 scripts/alive.py [--write] [--json]
bash scripts/weekly.sh [--since YYYY-MM-DD]       # scan → alive --write → tracker report → data/search/reports/

# scoring / tracking / discovery
python3 scripts/score.py init <body.md> -o <judgment.yaml>;  python3 scripts/score.py <judgment.yaml>...;  ... apply <judgment.yaml>...
python3 scripts/eval_golden.py <folder>             # classification drift vs examples/golden (procedure: references/scoring.md "Golden set")
python3 scripts/tracker.py add|set|report [--alive]
python3 scripts/cover_check.py <cover.yaml>          # cover-letter answers: character counts vs limit + style rules
python3 scripts/discover.py collect|probe|report|missing|set <file.tsv>|promote [--min S] [--dry-run]

python3 assets/src/render.py                      # regenerate README preview PNGs
```

Most scripts read and write real files under `data/`; use `--dry-run` where offered when experimenting.

## Architecture

**`scripts/jobkit.py` is the shared core** used by scan/alive/tracker/score/discover: repo-relative paths (`P` dict, all under `data/`), `http_get`/`get_json` (browser UA, per site one request at a time with a 1s gap after the previous response, safe to call from threads, gzip, 308 redirect handling), the `Job` dataclass, title/career/location filters, company alias normalization for cross-site dedup, `scan-history.tsv` I/O, the tracker table format, and `STATES` (Korean status values). Scripts import it via `sys.path` insertion as `import jobkit as K`, not as a package.

**Providers (`scripts/providers/*.py`)** each implement the same module-level contract: `collect(cfg) -> List[Job]`, `detail(job) -> str`, `alive(url) -> Optional[bool]` (None = can't tell), `handles(url) -> bool`. On an unexpected response shape they raise `jobkit.ShapeError`, which is reported as "응답 형식 변경" rather than crashing the run. A new provider must be registered in `providers/__init__.py`: `ALL` (for `for_url`, used by alive), and either `BOARDS` (job boards), `BY_ATS` (generic ATS keyed by `ats:` in sources.yaml), or a URL rule in `for_company`. Document its endpoints and a measurement date in `references/sources.md`, and add `tests/fixtures/providers/<module>.json` (format in `tests/test_providers.py`): responses with the real structure but fictional companies and text, the expected `Job`s, `detail`/`alive` cases, and a changed-shape case that must raise `ShapeError` (a real empty list is not a shape change, a missing list key is). The suite fails for a module in `ALL` without a fixture.

**Company pipeline:** `discover.py` gathers candidate companies (tech blogs, GitHub orgs, Wanted company info, `references/company_seed.yaml`), scores notability, probes career sites and detects the ATS, stores everything in `data/search/companies.yaml` (preserving user-written `status`/`memo`), and `promote` copies qualifying ones into `data/search/sources.yaml` `companies`, which `scan.py` then collects via `providers.for_company`. Exploration may be expensive once per company, collection never is: `probe` falls back to common career URLs and then a headless browser (Playwright, imported lazily, discovery only) to find the list API, and whatever replays with a plain request is written as `ats:`, `links:` or `jsonapi:` (`providers/jsonapi.py`, a config-driven JSON collector) so the weekly scan stays stdlib + PyYAML.

**Judgment vs arithmetic split:** the agent classifies each posting line into a judgment yaml (`data/search/judgments/`); `score.py` computes the score deterministically from it: common rules (bands by required/preferred coverage, caps) are constants in the script; personal preferences come from `data/profile/targets.yaml` `scoring` (falls back to `targets.example.yaml`). Rules: `references/scoring.md`. Keep scoring logic in the script, not in mode prose. `score.py init` also drafts the stack gate (`stack_draft`: a qualification line that demands a language outside `gates.stack_languages`, with no open list or substitute clause) for the agent to confirm; change its patterns only after re-checking against the existing judgments that no posting the agent passed on every gate would be drafted as `fail`. When a change alters how posting lines are classified, run the golden set (`examples/golden/`, procedure in `references/scoring.md` "Golden set") and report the disagreements. The agent's own review on top (recorded as `review` in the judgment file) and searching beyond the scripts follow `references/judgment.md`.

**Resume build:** `render.py` turns a resume yaml (schema: `references/yaml_schema.md`) plus personal info from `data/profile/profile.yaml` into HTML, prints A4 PDF with Playwright Chromium, renders PNGs, then runs `check.py`. `check.py` banned words, translationese, and symbol limits come from `references/style_rules.yaml`, so edit that file, not the code.

**Data flow:** `scan.py` → `data/search/pipeline.md` ("## 새로 수집 (선별 전)") + `inbox/*.md` bodies + `scan-history.tsv` → the agent screens → `evaluate` writes `data/job_postings/*.eval.md` → `tracker.py` manages `data/applications/tracker.md` (setting 지원함 moves the pipeline entry to the re-apply cooldown). Markdown/TSV files are the source of truth, and scripts parse their section headings and table headers literally, so changing a heading in a mode file or script means changing the other side too.

## Conventions

- **Public repo, private `data/`.** `.gitignore` ignores `data/*/*` except `README.md`, `.gitkeep`, `*.example.*`. Personal data must never land in `SKILL.md`, `modes/`, `references/`, `scripts/`, `docs/`, and new data files go inside a `data/` subfolder, never directly under `data/`. Examples use fictional people/companies (`examples/example.yaml`). `scripts/privacy_check.py` enforces this: CI fails on tracked `data/` files outside that allowlist, and the pre-commit hook in `.githooks/` (enabled per clone with `git config core.hooksPath .githooks`) also blocks added lines containing the name, email, phone or school from `data/profile/profile.yaml`. Never bypass it with `--no-verify` on the user's behalf.
- **Changelog and releases.** Every change a user would notice adds a line under "## 다음 버전" in `CHANGELOG.md` (Korean, issue number at the end). A change to a `data/` file format (a heading, table header or key a script matches) must also say how to move existing files on the "**data/ 이전:**" line, or ship a migration script; otherwise that line reads "없음". To release: rename "다음 버전" to "vX.Y.Z — YYYY-MM-DD", add an empty "다음 버전" above it, set `version` in `pyproject.toml` and `plugin/.claude-plugin/plugin.json` to X.Y.Z, merge, then `git tag -a vX.Y.Z` on main, push the tag, and publish a GitHub release with the same lines. `install.sh` shows users the CHANGELOG lines added since their version.
- **Language split:** agent instruction files (`SKILL.md`, `modes/`, `references/*.md`) are English; everything user-facing is Korean: CLI output, script docstrings/comments, `data/` files, resume text, and Korean strings quoted in the instruction files (state values, headings), which must stay verbatim because scripts match them. `README.md` (ko) and `README.en.md` are kept in sync.
- Scripts are stdlib + PyYAML only for collection (`check_links.py` is stdlib-only by design); keep it that way.
- Collection endpoints are unofficial: keep the request delay and treat "missing from the public list" as not closed; closing is decided by per-site detail API/HTTP status.
