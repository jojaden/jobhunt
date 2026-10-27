# Cover letter and application questions

Korean applications often ask 2–5 written questions with a character limit (자기소개서, 지원서 문항). The resume rules (`references/resume_guide.md`, `references/writing_rules.md`) still apply; this file adds what differs.

## When to write one

- Only when the company asks (a form question, "자유 양식 자기소개서"). Do not attach a motivation statement to the resume by default.
- If the posting has "이력서 작성 추천사항" or form questions, answer those exactly; do not reuse a generic letter.

## Structure of one answer

Pick the order that fits the question; never a chronology of life events.

| Question type | Order |
|---|---|
| 지원 동기 / 입사 후 포부 | what in my work connects to this team's problem (one fact with a number) → why this company, from company research (the prep file, `modes/prep.md`) → what I would do first |
| 경험 / 문제 해결 / 성장 | situation → my role and actions → how the problem was solved (cause, options, choice) → result with a number → what I changed afterwards |
| 협업 / 갈등 | situation → each side's position → what I did → outcome → what I do differently now |
| 실패 | what I decided → what went wrong → how I found out → what I changed in the system or my habit |

- Open with the answer, not with background.
- One answer, one story. Two weak stories lose to one concrete story.
- Separate my part from the team's.
- Unshipped or failed work is fine when told honestly: why it was started, what was learned, what was kept.

## Never write

- Upbringing or family stories, slogans, self-deprecation ("부족하지만"), jokes, politics or religion.
- Thoughts without actions ("많이 고민했습니다" with nothing done).
- Claims beyond `data/experience/` facts. Inferred sentences carry `[확인 필요]` until the user confirms.
- Personal data the company did not ask for (age, family, address detail, photo).

## Length

- Aim for 80–100% of the limit; below 70% reads as low effort. Check whether the limit counts spaces (공백 포함) or not (공백 제외).
- Short paragraphs, 2–4 sentences each. `~습니다` style throughout.

## File and check

- File: `data/applications/covers/<회사>_<포지션>.yaml` (format in `data/applications/cover.example.yaml`).
- Check: `jobhunt cover-check <file>` — character counts per question against the limit, plus the same banned-word, translationese, in-house-name, and placeholder rules as the resume (`style_rules.yaml`).
