# Mode: onboard — first-time setup and personalization

Fill a new user's `data/`, and afterwards keep the personalization files from going empty. Read `modes/_shared.md` first.

## Session-start check

Check whether each file below exists and whether it is still the example (`*.example.*`) content.

| File | If missing or still the example |
|---|---|
| `data/profile/profile.yaml` | ask for name, job title shown under the name on the resume (`role`), and contact. Required for builds |
| `data/profile/targets.yaml` | "Setting targets" below |
| `data/experience/project_index.yaml` | go to step 1 (material collection) of `modes/tailor.md` |
| `data/profile/brief.md` | build it from targets and project_index |
| `data/search/sources.yaml` | copy the example and fit `title_filter` to the target roles |
| `data/applications/tracker.md` | create an empty table (format in `modes/track.md`) |

If `targets.yaml` or `brief.md` is still the example and the user starts scan or evaluate, say so first: "선별 기준이 아직 예시라 점수가 내 기준이 아닙니다. 먼저 채울까요?"

## Setting targets (1–4 questions at a time, with the host's choice UI if it has one, otherwise plain text)

1. 2–4 target roles with priority, plus adjacent roles (worth considering if the move is feasible)
2. How to show years of experience, desired salary range and floor (pre-tax)
3. Location conditions, remote vs office preference
4. Exclusions: language (English required, etc.), stack (a required language the user has never used; also write the languages the user has used at work to `gates.stack_languages`, which lets `jobhunt score init` pre-fill the stack gate), employment type (SI · dispatch · contract), company size
5. Why they are leaving and the environment they want (take their own words verbatim into `narrative.exit_story`)
6. Bonus and penalty signals, priority-company criteria

Write the answers to `targets.yaml`, then build `brief.md` with 3–8 key achievements (only `confirmed` entries of `project_index.yaml`). Show the brief and get confirmation.

## Keep learning

- Apply the user's corrections after evaluation or screening right away, per `_shared.md` "Getting sharper".
- Once a month, or once 3+ application results have come in, offer to check whether `targets.yaml` and `brief.md` still match recent judgments.
