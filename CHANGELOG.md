# 변경 기록

버전은 git 태그(`v1.0.1`)로 붙이고, 같은 내용을 [Releases](https://github.com/jojaden/jobhunt/releases)에 올립니다.
`install.sh` 로 갱신하면 그 사이에 추가된 항목을 보여 줍니다.

버전마다 **data/ 이전** 항목이 있습니다. 스크립트가 `data/` 파일의 제목·표 머리를 글자 그대로 찾기 때문에, 형식이 바뀌면 기존 자료를 옮기는 방법을 여기에 적습니다. 필요 없으면 "없음".

## 다음 버전

## v1.2.0 — 2026-10-13

- 공고 수집 속도: 약 520초 → 120초 (출처 136곳 실측). 사이트별로 동시에 받고(같은 사이트는 지금처럼 한 번에 하나, 앞 요청이 끝난 뒤 1초), 본문은 앞 출처가 끝나는 대로 받기 시작. greetinghr 홈페이지 링크 방식은 이미 본 공고의 상세를 다시 받지 않음 (#30)
- 선별 모드가 읽는 양: 약 1.7MB → 약 70KB (지침 포함, 현재 자료로 실측). `scan-history.tsv`·`pipeline.md`·`tracker.md` 를 통째로 읽지 않고, 손으로 찾은 공고는 `scan.py --add` 로 중복 확인과 필터(제목 필터는 빼고, 에이전트가 읽고 고른 공고이므로)를 거쳐 기록, 선별 결과는 `score.py apply` 로 옮김. 첫 선별은 "재채점" 대신 "선별"로 적음 (#32)
- 마감 확인: 약 170초 → 88초 (공고 214건 실측), 사이트끼리는 동시에 확인(같은 사이트는 지금처럼 하나씩). 사람인 공고도 마감을 판정해 "확인 불가"가 47건 → 5건, 목록의 마감일보다 일찍 마감된 공고도 잡음 (#34)
- 응답을 gzip 으로 받음: 받는 양이 수집 66MB → 12MB, 마감 확인 24.5MB → 6MB (실측). 걸리는 시간은 그대로 (대부분 사이트별 요청 간격) (#36)
- 수집 보고: LinkedIn 이 요청 제한(429)으로 일부만 받았으면 출처 줄에 "⚠ 일부만 — 못 받은 키워드 (다음 실행에 다시 받음)"으로 표시. 지금까지는 정상과 똑같이 보였음 (#38)
- `jobhunt` 명령: `uv tool install` 로 설치할 수 있는 패키지(`pyproject.toml`). `jobhunt scan` · `alive` · `weekly` · `score` · `tracker` · `report` · `render` … 는 `python3 scripts/…py` 와 같고, `jobhunt where` 가 개인 자료 폴더를 알려 줌 (`JOBHUNT_HOME` > 저장소에서 돌면 저장소 > `~/jobhunt`). 주간 실행은 `weekly.py` 로 옮김(`bash scripts/weekly.sh` 도 그대로 동작) (#40)
- Python 3.10 이상이 필요함 (3.9 지원 끝, Playwright 최신판이 3.10+) (#40)
- 설치가 uv 방식으로 바뀜: 한 줄 설치가 uv(없으면 설치) → `jobhunt` 명령 → `jobhunt setup`(개인 자료 폴더 준비 · 스킬 연결 · Chromium·폰트·poppler). 도구는 uv 가 관리하는 폴더에, 개인 자료는 `~/jobhunt/data` 에 따로 있음. 지침(SKILL.md · modes/ · references/)과 README 의 명령은 `jobhunt …` 으로. `jobhunt --version`(커밋 포함) · `jobhunt changes <버전>` · `jobhunt git-log` 추가 (#42)
- Claude Code · Codex 플러그인: `claude plugin install jobhunt --marketplace jojaden/jobhunt`, `codex plugin marketplace add jojaden/jobhunt` → `codex plugin add jobhunt@jobhunt`. 플러그인은 설치된 jobhunt 의 지침으로 안내만 해서 버전이 어긋나지 않고, 플러그인이 있는 에이전트에는 `jobhunt setup` 이 스킬 링크를 만들지 않음 (#44)
- 1차 선별: `score init` 이 자격요건 줄에서 쓰지 않는 언어를 꼭 요구하는 공고에 언어(stack) 관문 초안(`fail` + 근거 줄)을 채움. 에이전트는 그 줄만 확인. 기존 판정 719건과 대조해 통과시킨 공고를 잘못 떨어뜨린 경우 0건, 언어 관문 탈락의 59%를 초안으로 잡음. 또 "Preferred Qualifications"·"이런 분이면 더 좋아요" 아래 우대 줄이 자격요건으로 들어가던 것을 고침 (#46)
- **data/ 이전:**
  - 예전에 git clone 으로 설치했다면 같은 설치 명령을 다시 실행하세요. `~/jobhunt/data` 는 그대로 두고, git 이 관리하던 코드·지침 파일과 `.git` 을 `~/jobhunt/.old-repo/` 로 옮깁니다(지우지 않음, 고친 파일도 그대로). cron·launchd 가 `~/jobhunt/scripts/weekly.sh` 를 부르면 그 경로가 `jobhunt weekly` 를 부르도록 이어 둡니다 (#42)
  - 언어 관문 초안을 쓰려면 `data/profile/targets.yaml` 의 `gates` 에 `stack_languages: [실무로 쓴 언어, …]` 를 넣으세요(넣지 않으면 지금과 같음) (#46)

## v1.1.0 — 2026-10-08

- 이력서 yaml 형식 검사: 모르는 키(오타)·타입·쓸 수 없는 값을 빌드 전에 위치와 함께 멈춤, 편집기 자동완성용 스키마 `references/resume.schema.json` (#13)
- 판정 정답 세트 `examples/golden/` 와 `scripts/eval_golden.py`: 분류 규칙을 바꿨을 때 에이전트 판정의 줄·결론 일치율 (#14)
- 이 변경 기록, `install.sh` 갱신 때 바뀐 점 안내 (#15)
- ruff 린트(`ruff.toml`: 쓰지 않는 import·변수, 정의 안 된 이름 같은 실수만): CI 작업, 커밋 전 훅은 ruff 가 설치돼 있을 때만. 쓰지 않던 변수 정리 (#16)
- 기여 안내 `CONTRIBUTING.md`, 이슈 양식(수집기 응답 형식 변경 · 버그 · 기능 제안)과 PR 양식 (#17)
- 고침: 커밋 전 훅이 PyYAML 없는 가상환경의 python3 로 돌 때 traceback 으로 멈추던 것 — profile.yaml 을 직접 읽어 같은 검사 (#23)
- 분류 규칙 문구 (`references/scoring.md`): 같은 기술로 대상·쓰는 사람만 다른 업무는 adjacent(업종만 다른 같은 종류의 시스템은 done), 업종 경험 우대는 key 아님, 'A·B' 우대는 하나를 채우면 yes, 업종 이름만으로는 domain_new 아님, 숫자 없는 규모 표현은 partial, 연봉 미기재는 comp: unclear(점수 반영 없음). 기존 판정은 다시 분류하면 adjacent·key 가 바뀔 수 있다 (#25)
- **data/ 이전:**
  - `data/resumes/*.yaml` 이 형식 검사에 걸리면 표시된 위치를 고친다 (예: 기본값이 없는 칸을 비워 둔 것, 키 오타). 첫 줄에 `# yaml-language-server: $schema=../../references/resume.schema.json` 을 넣으면 편집기가 미리 알려 준다
  - `data/search/judgments/` 의 판정은 예전 분류 문구로 쓰였다. 새 문구(#25)로 갈리는 줄(어드민·운영 API 의 done, 업종 경험 우대의 key, 'A·B' 우대, 숫자 없는 규모 표현, 업종 이름의 domain_new)만 다시 보고 `score.py` 로 다시 계산한다

## v1.0.1 — 2026-10-08

- 한 줄 설치 `install.sh`: 받기·갱신부터 스킬 연결·빌드 환경까지, `JOBHUNT_REF` 로 버전 고정 (#1)
- 네트워크 없이 도는 단위 테스트: 수집기 17개 고정 응답, 공급원 고르기, 현황표·pipeline.md 읽기·쓰기, 점수 계산 (#3)
- 고침: 네이버·우아한형제들·나인하이어 수집기가 응답 형식이 바뀌어도 0건으로 넘어가던 것을 "응답 형식 변경"으로 보고. 나인하이어 마감 판정이 형식 변경을 "모두 마감"으로 읽을 수 있던 것 (#3)
- CI: PR·main 마다 Ubuntu·macOS × Python 3.9·3.12 테스트, Ubuntu 설치와 예시 이력서 빌드 (#4)
- 개인 자료 커밋 방지: CI 의 `data/` 검사, 커밋 전 훅 (`git config core.hooksPath .githooks`) (#5)
- 사용 범위·면책 고지 `LEGAL_DISCLAIMER.md` (#6)
- **data/ 이전:** 없음

## v1.0.0 — 2026-10-08

첫 정식 버전.

- 공고 찾기: 원티드·점핏·LinkedIn·사람인, Greenhouse·Lever·greetinghr·나인하이어·Workday·Workable·Ashby·잡플렉스·라운드HR·SK Careers 기업, 자체 채용 사이트, 첫 화면에 목록이 없는 사이트
- 회사 넓히기 `discover.py`, 맞춤도 평가 `score.py`, 맞춤 이력서 A4 PDF, 자기소개서 답변, 면접 준비, 지원 관리
- 설치: `git clone` + `scripts/setup.sh` (macOS · Debian/Ubuntu · Windows WSL2)
