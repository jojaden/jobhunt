# Mode: cover — cover letter and application questions

Write answers to a company's application questions (자기소개서, 지원서 문항) for one posting. Read `modes/_shared.md` and `references/cover_letter.md` first.

## Steps

1. Collect the questions with their character limits and whether spaces count. Ask the user to paste them when the posting page doesn't show them.
2. Read the posting, its `.eval.md` ("요건과 내 경험" table, "지원 전략"), the tailored resume yaml, and the prep file (`modes/prep.md`: `fit`, company research) if there is one. The letter must agree with the resume: same projects, same numbers.
3. For each question pick the structure in `references/cover_letter.md`, choose one story from `data/experience/` (or `data/interview/stories.md`), and draft in `~습니다` style. Mark inferred sentences `[확인 필요]`.
4. Save to `data/applications/covers/<회사>_<포지션>.yaml` (format: `data/applications/cover.example.yaml`).
5. Check: `jobhunt cover-check <file>`. Fix every error (over the limit, banned words, placeholders); aim for 80–100% of each limit.
6. Show each answer with its count, get confirmation on every `[확인 필요]`, write confirmed facts to `data/experience/facts.md`.
7. Note in the tracker memo that the cover answers are ready, and the file path.
