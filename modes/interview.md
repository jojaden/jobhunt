# Mode: interview — plan · practice · debrief

From a document pass to an offer: prepare each hiring stage, rehearse the questions the resume invites the way real interviewers ask them, and learn from every interview. Read `modes/_shared.md` and `references/interview_questions.md` (question styles, follow-up patterns, answer shapes) first.

| Sub-mode | When | Output |
|---|---|---|
| `plan` | an interview is scheduled, "면접 준비", "prep {회사}" | practice sheet `data/interview/<회사>_<포지션>.md` |
| `practice` | "예상 질문", "모의 면접", "꼬리질문 연습" | a live drill, then the sheet updated |
| `debrief` | after any interview, "면접 봤어" | one entry in `data/interview/log.md` |
| `redflag` | the user describes how the process went | warning signs in the tracker memo / blacklist candidate |

## Sources

- Facts: only primary files (`_shared.md` "Facts and evidence"). An answer never claims more than `data/experience/` supports.
- The user's study notes, if any: path under "면접 공부 노트" in `data/preferences/standing.md`. Read the parts that match the posting's stack and the resume. They hold the user's own answers and follow-ups — use that wording as the baseline, quiz from it, and point out anything that looks wrong or outdated instead of silently replacing it.
- Method: `references/interview_questions.md`.
- Stories: `data/interview/stories.md` — behavioral stories (incident, deadline cut, unknown technology, disagreement, a reverted decision, why leaving), one `## ` heading each, told as situation → my actions in time order → result → follow-up. Build it once from `data/experience/`, reuse it for every company.

## plan

1. Read the posting, its `.eval.md`, the submitted resume yaml, and its prep file (`modes/prep.md`; offer `prep` first when there is none). The prep file already holds the company research, stages, tests and first questions: start from them, check the questions against the resume that was actually submitted, and add what the next stage needs.
2. List the hiring stages from the posting (전형 절차 / 합류 여정). Missing → ask the recruiter or check the career page.
3. Write the practice sheet (Korean) in this order:
   - **전형별 준비** — per stage, what they check and how to prepare:

     | Stage | What they check | Preparation |
     |---|---|---|
     | 리쿠르터 / 문화적합성 / 인성 | motivation, reason for leaving, fit, salary, communication | 2-minute self-introduction; why this company (`fit` in the prep file); why leaving in one positive sentence, no blame; salary range from `targets.yaml`; one collaboration story |
     | 코딩테스트 / 라이브코테 | problem solving while watched | confirm input range, nulls, allowed libraries first; think aloud; test edge cases; practise in the posting's language |
     | 과제 | code quality, judgment | README with decisions and trade-offs, tests, commits that read as steps |
     | 직무 / 기술 인터뷰 | depth behind every resume line | the questions below, two follow-ups deep |
     | 임원 / 대표 | ownership, direction | impact in business terms, first 3 months |
     | 처우 협의 | — | `targets.yaml` floor and target; total-package terms (`_shared.md` "Reading Korean postings") |

   - **이력서에서 나올 질문** — for every project: the hardest part and how the cause was narrowed; why the adopted option and why the rejected one lost; how each number was measured and what produced it; my part vs the team's and team size; what I would change, and the monitoring or prevention afterwards. For every technology on the resume: why this one, how it differs from the alternative. Phrase them in the styles of `interview_questions.md` ("Resume check", "Number check"), each with two likely follow-ups.
   - **기술 질문** — from the posting's stack and the resume, pick questions across the styles (concept + design reason, internals, compare and choose, symptom → diagnosis, failure/extreme, integrated). Take them from the user's notes where they exist; add what the notes lack. Mark the ones most likely ("단골") first.
   - **행동·협업 질문** — map each to a story in `stories.md`; list missing stories to write.
   - **역질문** — 2–3 the company's public material does not already answer (success criteria of the role, deploy and incident practice, team make-up and onboarding), at least one from the prep file's company research.
4. Any resume line the user cannot defend two follow-ups deep: flag it and offer to cut or soften it (`modes/tailor.md`).
5. Show the user the next stage in full and a one-line plan for the rest. Add new preparation tasks to the prep file's `prepare` list and run `jobhunt report` so the page stays current.

## practice

A drill is a conversation, not a document.

1. Ask one question at a time, in the interviewer's voice and style. Start broad, then follow up on what the user actually said, using the follow-up patterns (trap, extreme, why-not-alternative, other tool, lived experience, worse situation, challenge a claim). Go at least two levels deep on resume items.
2. Do not answer for the user. After each answer give a short critique: structure (conclusion first? three lines?), missing number or cause, missing "my own experience" step, overclaiming, length (about one minute spoken). Then show the stronger answer shape in one or two lines, using the user's notes wording when it exists.
3. Mix in one pressure question and one design or incident scenario per session.
4. When the user doesn't know: coach the "where my knowledge stops" answer, and add the concept to the to-study list in the sheet.
5. At the end: update the sheet (answers that worked, gaps to study, lines to cut from the resume).

## debrief

Right after an interview, append to `data/interview/log.md`:

```markdown
## YYYY-MM-DD {회사} {포지션} — {전형} ({결과: 대기/합격/불합격})
- 받은 질문: …
- 막힌 답: … (왜 막혔나: 사실 부족 / 개념 부족 / 구조 부족)
- 잘 된 답: …
- 다음에 바꿀 것: …
- 면접 분위기·특이 사항: …
```

Then update the tracker state (`modes/track.md`); tell the user which concepts to add to their study notes; add an improvised story to `stories.md`. When three or more debriefs point the same way, raise it in `modes/outcome.md`.

## redflag

Note in the tracker memo, and with the user's agreement in `data/search/blacklist.md`: interviewer absent or late without notice; questions about family, partner, or age; insults or pressure for its own sake; a promised result date missed without word; refusal to sign a labour contract; overtime presented as culture; pay built mostly from conditional bonuses; loyalty demands ("가족 같은 회사").
