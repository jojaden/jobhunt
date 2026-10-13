# Sentence rules

What a machine can catch, `jobhunt check` checks by reading `style_rules.yaml`. The rest is checked by reading after writing.

## Tone

| Where | Tone | Example |
|---|---|---|
| SUMMARY first paragraph | `~합니다` style | "Kotlin 백엔드 개발자 4년차입니다. … 주문·정산 서버 개발을 담당하고 있습니다." |
| SUMMARY bullets, project text, OTHER | clipped style (noun endings, `~함`) | "주문 API p99 820ms → 240ms. 재고 조회 N+1 제거" |

Before: "Kotlin 백엔드 개발자 4년차. … 주문·정산 서버 개발을 담당."
After: "Kotlin 백엔드 개발자 4년차입니다. … 주문·정산 서버 개발을 담당하고 있습니다."

## Symbols (auto-checked)

- `—`, `·`, `→` at most once each per bullet.
- `→` only for before/after numbers (`820ms → 240ms`); describe flow and sequence in words.
- SKILLS lists and tech chips are exempt.

## Banned words (auto-checked, error)

고도화, 극대화, 체계적, 효율적, 원활한, 다양한, 핵심, 혁신, 견고한, 선제적, 확보, ~을 통해, ~기반으로, 단순히 ~가 아니라

## Translationese and English concept words (auto-checked, warning)

Where plain Korean exists, switch to it: fence, durable claim, 성립, 봉인, 격리, 일원 관리 …
Keep precise technical terms: CAS, gRPC, context, goroutine, lease …
Add to the list under `translationese` in `style_rules.yaml`.

## Writing for readers outside the company (auto-checked, warning)

A resume is read by people who don't know the user's company. Rewrite names that only mean something in-house as what the thing does.

- function · type · field names: `WatchOrderProgress`, `PublishWithAck`, `SessionKeeper`, `LastSyncedAt`
- in-house service and module names: orderd, hub, relay
- in-house-only numbers: a count thrown in without context ("검사 지점 17곳") comes out of the summary. Use it only in the body where it says what is being counted.

| Before | After |
|---|---|
| gRPC 서버 스트림 `WatchOrderProgress` 하나로 통합 | gRPC 서버 스트림 함수 하나로 통합 |
| orderd가 상태 변경을 발행하고 hub가 메모리에 유지 | 주문 서비스가 상태 변경을 발행하고 조회 서비스가 메모리에 유지 |
| 전용 SessionKeeper로 모아 | 전용 세션 관리자로 모아 |

Public library and standard names (`jackson-databind`, `kotlinx.coroutines`, WebSocket, GitHub) stay as they are. The auto-check warns on CamelCase names and single-word names in backticks; add public names to `internal_names.allow` in `style_rules.yaml`. Lowercase service names are checked by reading.

## Parentheses (auto-checked, warning)

Use parentheses only when they add meaning. Drop parentheses that append the same meaning in English after Korean. If one developer term carries it, English alone is fine.

| Before | After |
|---|---|
| 정해진 점검 시간(maintenance window) 안에 | 정해진 점검 시간 안에 |
| 공통 설정(configuration) 파일 | 공통 설정 파일 |

Keep: `결제 모듈(PG사 SDK)과 호출부(주문 서비스)를 분리` — the parentheses say what each part actually is.

## Checked by reading

- One modifier per phrase, not a chain of them.
- Vary list lengths instead of a steady rhythm of three ("A, B, C로 D, E, F를").
- Vary bullet length and shape.
- Test: is it a word the user would actually say when explaining this aloud in an interview?

## Showing check results

Show the user every flagged sentence before and after, side by side, and get confirmation.

```
[projects[0].rows[3].bullets[1]] 상투어 '확보'
  전: 분산 락 없이 여러 서버 간 재고 정합성 확보
  후: 분산 락 없이 여러 서버의 재고 수량을 맞춤
```

## Fact rules

- No number or fact that isn't in the material.
- Prefix sentences filled by inference with `[확인 필요]`. When the user confirms, remove the tag; if wrong, fix or drop the sentence.
- Any remaining `[확인 필요]` is an error in the check, so the resume can't be finalized.
