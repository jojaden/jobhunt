# Mode: tailor — resume tailored to a posting

Write a resume yaml tailored to one posting and build it into a PDF. Read `modes/_shared.md` first.
If the posting went through evaluation (`modes/evaluate.md`), use the requirement map and emphasis in `data/job_postings/<posting>.eval.md` as is. If it was prepared (`modes/prep.md`), also read `<posting>.prep.yaml`: `role.wants` (what the team asks for and the user's gaps) sets emphasis and terms, `questions` shows which resume lines will be probed (only claim what the user can defend two follow-ups deep), and `fit` and `company` shape the SUMMARY lead.

## Steps

Ask each step 1–4 questions at a time (the host's choice UI if it has one, otherwise plain text). If `data/` already holds an answer, show that value first as the recommendation.

### 0. Direction

- Target position: one of `roles` in `data/profile/targets.yaml` / enter manually.
- Job title under the name (`header.role`): recommend the title from the evaluation's "지원 전략", or else the posting's position name or the chosen target role, and let the user settle the wording. Once they pick a usual wording, write it to `role` in `data/profile/profile.yaml`.
- Whether there is a posting link or body.
  - If `data/job_postings/<posting>.eval.md` exists, show its requirement map, projects to emphasize, and gap handling as the recommendation. Reuse them as they are.
  - With no evaluation, extract 3–5 key requirements from the posting and show them. Use that list to set project order, SKILLS (overlap with the posting), and terms.
  - Save the posting to `data/job_postings/<YYYY-MM-DD>_<회사>_<포지션>.md` with the link, full text, requirements, and term map.
- If base versions (`data/resumes/base_*.yaml`) exist, copy the closest one to start. `cp base_service.yaml 회사_service.yaml`

### 1. Material collection (multiple choice)

- A document summarizing experience / a local git repository (author-filtered commit log) / GitLab / an existing resume (pdf, py, docx).
  - git: `jobhunt git-log <repo> "<email|name>" [since] [until]` → `data/experience/git_<repo>.md`. Revert, downgrade, and abandoned commits (marked ⟲) are trial-and-error story candidates.
  - GitLab: if a GitLab tool is connected, read MRs and commits by author. Otherwise ask the user for an exported list.
  - Existing resume: move its wording into yaml. For a py build script, pull wording from function arguments and constants.
- If there is nothing, take it as direct input, asking in this order:
  1. Company, period, role (most recent first if several companies)
  2. Per project: problem → cause (how it was found) → options (alternatives considered and why they were dropped) → execution → result numbers (before/after)
- When collection is done, build a list of project candidates, each with a one-line evidence note (document location, commit or MR, source of the number). Save to `data/experience/project_index.yaml`.
- At most 5 projects go in. Show a recommendation first (with order) based on overlap with the posting's requirements, then let the user pick (multiSelect). Keep dropped candidates worth one line as OTHER candidates.

### 2. Extra requirements

- Strengths to emphasize, content to leave out, target page count (default 2–3), sections to add or remove, how to show years (e.g. "N년차", "N년 M개월", none).
- Write what applies only to this posting to `data/preferences/<posting>_requests.md`, and what applies from now on to `data/preferences/standing.md`, with the date. When it's unclear which, ask.

### 3. Personal portfolio

- Ask whether there is a GitHub, blog, etc.
- If so, put it in `portfolio.items` (goes into the header contact line and the PORTFOLIO box).
- Read the post list, propose 1–2 related posts per project, and put only the user-confirmed ones in `links`.
- Check that every link actually opens ("Link check" below).
- If none, leave `portfolio` empty → the PORTFOLIO box is dropped.
- Save the result to `data/portfolio/portfolio.yaml` (post list, chosen posts, check date).

### 4. Write and build

1. Write the yaml following "Structure and design" and "Sentence rules" below. File: `data/resumes/<회사>_<포지션>.yaml`. First line: `# yaml-language-server: $schema=../../references/resume.schema.json`.
2. Prefix every sentence filled by inference with `[확인 필요]`.
3. Build:
   ```
   jobhunt render data/resumes/<file>.yaml
   ```
   `--design A|C` for the other designs, `--offline` to skip link reachability checks.
   Output: `data/output/이름_직무_버전.pdf`, `_p1.png …`, `.html`. The filename is profile `name`, yaml `meta.job` (if empty, the header job title), `meta.version`.
4. Without a build environment, start with `jobhunt setup`. If building fails in the user's local shell, upload only `scripts/`, `references/`, the yaml, and the profile to a cloud workspace, build there, and bring the PDF and PNGs back into `data/output/`.

### 5. Review and revise

1. Summarize and show the post-build check results ("Post-build checks" below).
2. Show the style self-check results. Show every flagged sentence before and after, side by side, and get confirmation.
3. Collect the `[확인 필요]` sentences and confirm them one by one. Once confirmed, remove the tag and write the fact to `data/experience/facts.md`.
4. Show the PNG previews page by page and take revision requests. Repeat steps 4–5 until final.
5. When final:
   - Put the final PDF in the connected folder (default `data/output/`).
   - Put the final yaml in `data/resumes/`, and if the host has a connected project space (e.g. a Claude project), save it there too.
   - Write the yaml name used into the posting file in `data/job_postings/`.
   - Update the PDF cell and memo of the row in `data/applications/tracker.md`. The user submits; when they say they did, change the state per `modes/track.md`.

## Structure and design

- Default design is B (Swiss grid, cobalt). A (editorial, serif + green) and C (dark masthead, copper) on request. yaml `meta.design`.
- Section order: header → PORTFOLIO → SUMMARY → SKILLS → EXPERIENCE → PROJECTS → OTHER. User-added sections go in `extra_sections`.
- No EDUCATION section. Education stays in profile for reference only.
- Header: one job-title line under the name, no subtitle after it. `header.role` for this resume, else profile `role`; with neither, the line is dropped.
- Project block: number and title / period · role · tech chips / summary bar / problem / root cause / options (adopted marked) / execution / result KPIs / related posts. Format in `references/yaml_schema.md`.
- At most 5 projects. Page 1 should show SUMMARY, SKILLS, and the start of the lead project.

## Sentence rules

- SUMMARY first paragraph in `~합니다` style.
  - Before: "Kotlin 백엔드 개발자 4년차. … 주문·정산 서버 개발을 담당."
  - After: "Kotlin 백엔드 개발자 4년차입니다. … 주문·정산 서버 개발을 담당하고 있습니다."
- SUMMARY bullets and project text in clipped style (noun endings, `~함`).
- Write like a person, not like AI.
  - `—`, `·`, `→` at most once each per bullet. `→` only for before/after numbers.
  - Where plain Korean exists, use it over English concept words and translationese: fence, durable claim, 성립, 봉인, 격리, 일원 관리 …
  - Keep precise technical terms: CAS, gRPC, context …
  - Banned clichés: 고도화, 극대화, 체계적, 효율적, 원활한, 다양한, 핵심, 혁신, 견고한, 선제적, 확보, ~을 통해, ~기반으로, 단순히 ~가 아니라
  - One modifier per phrase; vary list lengths instead of always three; vary bullet length and structure.
  - Test: is it a word the user would actually say when explaining this aloud in an interview?
- Action verb + method + result. End on what was done, not on "참여/담당/노력/기여" (except "담당하고 있습니다" in the SUMMARY first paragraph).
- After writing, self-check against the list above. Items the automatic check (`check.py`) cannot catch (stacked modifiers, lists of three, repeated structure) need a direct read and judgment. Show flagged sentences before and after.
- Fact rules
  - No number or fact that isn't in the material.
  - Mark sentences filled by inference with `[확인 필요]` and finalize only after the user confirms.

## General resume rules (summary; details in references/resume_guide.md)

- At most 5 projects. Ones far from the posting become a single OTHER line.
- Write numbers as before/after with the cause. Leave out unconfirmed numbers.
- Options: acknowledge the rejected option's strength before rejecting it on its weakness; for the adopted one, give the reasoning and how its weakness is controlled.
- Tech stack: 8–12 items overlapping with the posting, no proficiency markers, only technologies actually used.
- 1–2 links per project.
- No motivation statement. Write a separate 5–7 lines only when asked.
- Ship with every placeholder resolved.
- When this file and a references document conflict, follow this file.

## Post-build checks

`render.py` calls `check.py` at the end. To run it alone: `jobhunt check <yaml> <pdf>`

| Item | Criterion | Level |
|---|---|---|
| Page count | `meta.target_pages` (default 2–3) | error |
| Orphaned heading | fewer than 3 body lines after a section, project, or subheading on the same page (last page excepted) | error |
| Links | every link in the PDF reachable | unreachable = error, uncheckable = warning |
| Placeholders | 【 】, TODO, TBD, N건, `[확인 필요]` … | error |
| Banned words · symbols | `references/style_rules.yaml` | error |
| Translationese · concept words | `translationese` in the same file | warning |
| SUMMARY tone | every sentence of the first paragraph ends in `~니다` | error |

- Fix until errors are 0. Show warnings to the user and let them decide.
- Resolve orphaned headings and page overflow by cutting content (merge bullets, demote a project to OTHER) or reordering. Keep the CSS as is.
- Link check: cloud environments may block outbound access and report "확인 불가". Then run `jobhunt check-links --pdf <pdf>` on the user's machine or open the links in a browser. Record the result in `last_link_check` of `data/portfolio/portfolio.yaml`.
