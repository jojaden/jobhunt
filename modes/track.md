# Mode: track — application status

Manage the application tracker `data/applications/tracker.md`. Read `modes/_shared.md` first.

## How to record

Change the table only through `jobhunt tracker` (it validates format and state values and syncs pipeline.md).

```bash
jobhunt tracker add --company 회사 --role 포지션 --score 4.2/5 --eval data/job_postings/<공고>.eval.md --memo "서울 강남 · 원티드 · <url>"
jobhunt tracker set <번호|회사> 지원함 [--note "메모"] [--pdf]
jobhunt tracker report [--alive] [--since YYYY-MM-DD]
```

## Format

```markdown
| # | 날짜 | 회사 | 포지션 | 점수 | 상태 | PDF | 평가 | 메모 |
|---|------|------|--------|------|------|-----|------|------|
| 1 | 2026-10-01 | 가나다 | 백엔드 개발자 | 4.2/5 | 평가함 | ❌ | [평가](../job_postings/2026-10-01_가나다_백엔드.eval.md) | 서울 강남 · 원티드 |
```

- Numbers continue from the last row. The date is when the row was first recorded.
- The memo always includes location and source (원티드 · 사람인 · 자체 사이트 …). On every state change, append `; {내용} (YYYY-MM-DD)`.

## State values

Scripts validate these; use them verbatim.

| State | When |
|---|---|
| `평가함` | evaluated, application undecided |
| `지원함` | the user says they submitted |
| `서류합격` | notified of passing document screening → offer `modes/interview.md` plan (and `modes/deep.md` if no company note yet) |
| `면접` | interviews in progress (round in the memo); after each round run the `modes/interview.md` debrief |
| `최종합격` | received an offer |
| `입사` | accepted the offer |
| `불합격` | the company rejected |
| `포기` | the user dropped it, or the posting closed |
| `제외` | not a fit, not applying |

The state cell holds the state value alone (no bold, date, or explanation). Explanations go in the memo.

## Rules

- When the user says they applied, run `tracker.py set <번호> 지원함` immediately. The script moves that posting in pipeline.md to "지원 완료 — 재지원 쿨다운".
- Reapply cooldown: within `reapply_days` of `targets.yaml` (default 183 days) after `지원함`, the same company's postings are dropped from scan (`scan.py` does it automatically). If the user was rejected for one role and doesn't yet know whether the company accepts applications to a different role, write `쿨다운 제외` in that row's memo — the company's other postings stay in the queue — and add "재지원 가능 여부 확인 필요" to those postings' judgment notes.
- When a result (`서류합격`, `불합격`, …) comes in, compare it with that posting's `.eval.md` score. Once mismatches pile up (high score but rejected, low score but passed; 3+ cases), propose adjusting the screening criteria (`modes/outcome.md`), and if accepted write it into `targets.yaml` and `brief.md`.
- Rows are permanent. A row added by mistake gets state `제외` with the reason in the memo.
