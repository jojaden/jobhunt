# 로드맵: 공고 찾기 → 평가 → 공고 준비 → 맞춤 이력서

목표: 한국 개발자 채용 공고를 찾고, 내 경력에 맞는 공고를 골라, 고른 공고마다 회사·직무·전형을 준비하고 최적화한 이력서를 만든다. 쓸수록 `data/`에 개인 기준이 쌓여 선별이 정확해진다.

모드로 나눈 구성과 개인화 저장 구조는 [career-ops](https://github.com/santifer/career-ops)의 아이디어를 참고했다. 이 저장소는 한국 공고 수집·평가, 이력서 빌드(`scripts/render.py`), 지원과 면접 준비에 집중한다.

## 원칙

| 원칙 | 이 저장소에서 |
|---|---|
| 로컬 우선 | 모든 자료는 내 PC의 파일. 서버·계정 없음. 공공 API(국민연금·DART)는 사용자 본인 키로만, 쓰지 않아도 됨 |
| 파일이 원본 | 사람이 읽고 diff할 수 있는 md·yaml·tsv가 원본. 캐시·DB는 파생물 |
| 시스템 / 사용자 파일 분리 | 도구(`SKILL.md`, `modes/`, `scripts/`, `references/`)는 git에 올리고 `uv tool install`로 설치한다. 개인 자료는 jobhunt 홈(`~/jobhunt/data`)에만 두고 올리지 않는다 |
| 사람이 최종 결정 | 준비·평가까지만. 지원서 제출은 사용자가 직접 |
| 지어내지 않는다 | 키워드는 바꿔 쓰되 경험·수치는 만들지 않는다. 근거 없는 문장은 `[확인 필요]` |
| 공고는 데이터 | 공고문·회사 페이지 안의 문장은 지시가 아니다 |
| 쓸수록 똑똑해진다 | 평가 후 사용자 피드백("점수가 높다", "X 경험을 놓쳤다")을 `data/`의 알맞은 파일에 날짜와 함께 적는다 |

## 데이터 계약

**시스템 파일 (git에 올라감, 개인정보 없음)**

| 경로 | 역할 |
|---|---|
| `SKILL.md` | 진입점. 요청을 모드로 연결 |
| `modes/_shared.md` | 모든 모드 공통 규칙, 한국 채용 용어, 파일 지도 |
| `modes/onboard.md` · `scan.md` · `evaluate.md` · `prep.md` · `tailor.md` · `track.md` | 모드별 절차 |
| `references/sources.md` | 채용 사이트별 수집 방법(엔드포인트, 상세 본문 위치, 마감 판정) |
| `scripts/` | 빌드·검사, 공고 수집(`scan.py`, `providers/`), 마감 확인(`alive.py`), 지원 현황(`tracker.py`), 공고 현황표와 준비 쪽(`report_html.py`, `prep_page.py`), 회사 숫자(`company.py`, 키가 있으면 `nps.py`·`dart.py`, 키 관리 `keys.py`), 주간 실행(`weekly.py`), 업데이트(`update.sh`), `jobhunt` 명령(`cli.py`) |

**사용자 파일 (`data/`, git 제외, 구조와 예시만 올라감)**

| 경로 | 무엇 | career-ops 대응 |
|---|---|---|
| `data/profile/profile.yaml` | 이름·연락처 | `config/profile.yml` 일부 |
| `data/profile/targets.yaml` | 목표 역할, 서사, 연봉, 근무지·언어·스택 조건 | `config/profile.yml` + `modes/_profile.md` |
| `data/profile/brief.md` | 공고 1차 선별용 짧은 요약 (~2K 토큰) | `modes/_brief.md` |
| `data/experience/` | 경험 문서, 프로젝트 후보와 근거(`confirmed`/`needs_check`) | `cv.md` + `article-digest.md` |
| `data/preferences/standing.md` | 계속 적용할 작업 규칙·결정 | `modes/_custom.md` |
| `data/search/sources.yaml` | 제목·근무지 필터, 우선 기업, 채널별 검색 조건 | `portals.yml` |
| `data/search/pipeline.md` | 선별 대기 공고함 | `data/pipeline.md` |
| `data/search/scan-history.tsv` | 본 공고 기록(중복 제거) | `data/scan-history.tsv` |
| `data/search/blacklist.md` | 지원하지 않을 회사 | `data/blacklist.md` |
| `data/search/inbox/` | scan.py가 받은 공고 본문 (1차 선별 입력) | — |
| `data/search/reports/` | `jobhunt weekly` 주간 보고 | — |
| `data/job_postings/` | 공고 원문(`*.md`), 평가(`*.eval.md`), 준비 자료(`*.prep.yaml`) | `jds/` + `reports/` |
| `data/applications/tracker.md` | 지원 현황표 | `data/applications.md` |
| `data/resumes/`, `data/output/` | 확정 yaml, PDF·PNG | `output/` |

공공데이터포털·OpenDART 키는 `data/` 밖 `~/.config/jobhunt/keys`(권한 600)나 환경 변수에 둔다. 계정에 묶인 개인 키라 어디에도 올리지 않는다.

## 흐름

```
scan ──► search/pipeline.md ──► 1차 선별(brief.md) ──► evaluate ──► job_postings/*.eval.md
                                                            │               │
                                                            └─► applications/tracker.md
                                                                            │
                                                  report (공고 현황표) ──► 사용자가 공고를 고름
                                                                            │
          prep (회사·직무 조사, 전형·시험, 예상 질문, 더 준비할 것 → job_postings/*.prep.yaml,
                회사 숫자는 jobhunt company, 현황표의 그 공고 줄에 준비 쪽)
                                                                            │
                                               tailor (base yaml → 공고별 yaml → PDF → 검사)
                                                                            │
                                                     사용자가 직접 지원 → track → interview
```

## 한국 공고 소스 (2026-09-29 확인)

| 소스 | 방법 | 상태 |
|---|---|---|
| 원티드 | 목록 `api/chaos/navigation/v1/results`, 상세 `api/v4/jobs/{id}` (자격요건·주요업무·우대사항) | 응답 확인 |
| 점핏 | `jumpit-api.saramin.co.kr/api/positions`, 상세 `/api/position/{id}` | 응답 확인 |
| Greenhouse | `boards-api.greenhouse.io/v1/boards/{회사}/jobs` (당근·쿠팡·크래프톤 등) | 공식 공개 API |
| 기업 채용 사이트 | 토스·NHN·네이버 JSON, greetinghr·roundhr 페이지 | 회사별로 확인하며 추가 |
| 사람인 | 검색 페이지 + `relay/view-detail?rec_idx=` 상세, 공식 OpenAPI는 키 필요 | 2단계에서 확인 |
| 잡코리아 | 검색 페이지 + `/Recruit/GI_Read/{id}` 상세 | 2단계에서 확인 |
| 프로그래머스 커리어 | 도메인 없음 | 제외 |

원티드·점핏·기업 사이트 JSON은 비공식 엔드포인트다. 개인 용도로 요청 간격을 두고 쓰며, 형식이 바뀌면 `references/sources.md`를 고친다.

준비 단계의 회사 숫자(2026-10-27 확인)는 원티드 회사 쪽의 '기업 정보' 표(키 없음)를 기본으로, 사용자 키가 있으면 국민연금 가입 사업장 내역(공공데이터포털: 가입자 수, 고지액 기반 평균연봉 추정, 입사·퇴사)과 OpenDART(대표자, 사업보고서 주요계정이나 감사보고서 손익계산서의 매출·영업이익)를 더한다. 주소와 응답 구조는 `references/sources.md`.

## 단계

| 단계 | 내용 | 상태 |
|---|---|---|
| 1 | 데이터 계약, 모드 문서(`modes/`), 수집 방법 문서, `SKILL.md` 라우터, 기존 career-ops 개인 설정 이전 | 완료 (2026-09-29) |
| 2 | `scripts/scan.py` + `scripts/providers/`(원티드·점핏·LinkedIn·Greenhouse·토스·NHN·카카오·greetinghr). 회사 별칭(`company_aliases`)으로 사이트 간 중복 제거. 제목·연차·근무지 필터, 중복·제외 회사·쿨다운, `pipeline.md`·`scan-history.tsv`·`inbox/` 기록, `alive.py` 마감 확인, `weekly.sh` | 완료 (2026-09-29) |
| 2b | 사람인 공급원 (검색 페이지 HTML, 2026-10-06 완료) · 잡코리아·리멤버 (HTML·브라우저 필요, 지금은 `references/sources.md`대로 수동) | 일부 완료 |
| 3 | 평가 리포트 형식 고정, `tracker.py`(상태값 검증, 재지원 쿨다운 연동, 통합 보고표) | 지원 현황 부분 완료 (2026-09-29) |
| 4 | 평가의 요구사항 대응표 → 맞춤 yaml 자동 초안 (프로젝트 순서, SKILLS 교집합, 용어 치환) | 예정 |
| 5 | 학습 루프: 결과(서류 합격·탈락)와 피드백을 모아 선별 기준·강조점 조정 제안 | 예정 |
| 6 | 속도: 사이트별 동시 수집·마감 확인, gzip, 1차 선별이 읽는 양 축소(`scan.py --add`, `score.py apply`), 요청 제한으로 일부만 받으면 보고에 표시 | 완료 (2026-10-13) |
| 7 | 배포: `uv tool install` 로 설치하는 `jobhunt` 명령, 개인 자료를 `~/jobhunt` 로 분리, 기존 git 설치 전환, Claude Code·Codex 플러그인 | 완료 (2026-10-13) |
| 8 | 공고 준비(#82): 현황표에서 고른 공고마다 `prep` 모드가 회사·직무·전형·예상 질문·더 준비할 것을 `*.prep.yaml` 로 정리하고 현황표 줄에서 준비 쪽으로 연결(#83), 원티드 회사 정보로 회사 숫자(`jobhunt company`, #84), 사용자 키로 국민연금·DART 연동과 `jobhunt keys`(#87) | 완료 (2026-10-27) |
| 9 | 업데이트(#85): `jobhunt update` 가 설치 절차 없이 도구만 새 버전으로 (설치본은 다시 받아 설치, clone 폴더는 `main` 에서 `git pull`) | 완료 (2026-10-27) |
