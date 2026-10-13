# 기여 안내

jobhunt를 고치거나 넓히려는 사람을 위한 안내입니다. 구조와 각 스크립트의 역할은 [`AGENTS.md`](AGENTS.md)에 있습니다. AI 에이전트에게 작업을 맡길 때도 그 파일을 읽힙니다.

## 1. 준비

```bash
git clone https://github.com/jojaden/jobhunt.git && cd jobhunt
bash scripts/setup.sh --no-skill        # Python 패키지, Chromium, 글꼴, poppler
git config core.hooksPath .githooks     # 커밋 전 검사: 개인 자료, ruff(설치돼 있으면)
python3 -m pip install "ruff>=0.16,<0.17"   # 선택: 린트
```

Python 3.10 이상, macOS · Debian/Ubuntu · Windows WSL2.

## 2. 고친 뒤 확인

```bash
python3 -m unittest discover -s tests   # 네트워크 없이, data/ 를 건드리지 않음
ruff check .
python3 scripts/<고친 스크립트>.py ...     # 실제로 한 번 돌려 본다 (scan.py 는 --dry-run)
```

PR을 올리면 CI가 같은 테스트(Ubuntu·macOS × Python 3.10·3.12), ruff, 개인 자료 검사, Ubuntu 설치·예시 이력서 빌드, uv 로 설치한 `jobhunt` 명령 검사를 돌립니다.
`main` 에는 PR 로만 들어갑니다. CI 를 모두 통과하고 관리자(코드 소유자, [`.github/CODEOWNERS`](.github/CODEOWNERS))의 승인을 받아야 병합됩니다.

## 3. 저장소 규칙

- **개인 자료는 올리지 않습니다.** `data/` 아래에는 폴더 README · `.gitkeep` · `*.example.*` 만 올라갑니다. 예시·테스트·정답 세트에는 가상 인물과 가상 회사만 씁니다. 실제 공고 원문도 싣지 않습니다.
- **언어:** 에이전트 지침(`SKILL.md`, `modes/`, `references/*.md`, `AGENTS.md`)은 영어, 사용자가 보는 것(스크립트 출력·주석, `data/`, 이 문서)은 한국어. 지침 안의 한국어 상태값·제목은 스크립트가 글자 그대로 찾으므로 바꾸지 않습니다.
- **README:** `README.md`(한국어)와 `README.en.md`는 같은 내용으로 함께 고칩니다.
- **에이전트 중립:** 지침은 특정 AI 제품에 기대지 않습니다. 원본은 `AGENTS.md`, `CLAUDE.md` 는 그 파일을 불러올 뿐입니다.
- **의존성:** 공고 수집 스크립트는 표준 라이브러리 + PyYAML 만 씁니다. 브라우저(Playwright)는 회사 찾기 탐색과 이력서 빌드에만 씁니다.
- **수집 예절:** 같은 사이트에는 요청 간격을 두고, 봇 차단(403·429, 대기열)은 우회하지 않습니다. robots.txt 로 모든 수집을 막은 사이트는 쓰지 않습니다. [`LEGAL_DISCLAIMER.md`](LEGAL_DISCLAIMER.md)

## 4. 자주 하는 변경

**새 수집기 (채용 사이트·채용 시스템)**
1. `scripts/providers/<이름>.py` 에 `collect` · `detail` · `alive` · `handles` (계약은 `providers/__init__.py`). 응답 형식이 예상과 다르면 `ShapeError` — 조용히 0건으로 넘기지 않습니다. 공고가 정말 없을 때(빈 목록)와 형식이 바뀐 것(목록 키가 없음)을 구별합니다.
2. `providers/__init__.py` 의 `ALL` 과 `BOARDS` · `BY_ATS` · `for_company` 중 맞는 곳에 등록합니다.
3. `tests/fixtures/providers/<이름>.json` 고정 응답: 실제 응답 구조에 가상 회사·공고. 목록·본문·마감 판정과 형식 변경 사례 (형식은 `tests/test_providers.py` 맨 위). 고정 응답이 없으면 테스트가 실패합니다.
4. `references/sources.md` 에 주소와 실측 날짜를 적습니다.

**사이트 응답 형식이 바뀜** — `scan.py` 가 "응답 형식 변경"을 보고하면 수집기를 고치고, 그 고정 응답에도 새 형식을 반영합니다. 고칠 시간이 없으면 [이슈 양식](https://github.com/jojaden/jobhunt/issues/new/choose)으로 알려 주세요.

**공고 줄 분류 규칙** (`references/scoring.md`, `references/judgment.md`, `modes/evaluate.md`) — 에이전트에게 정답 세트(`examples/golden/`)를 정답을 보지 않고 분류하게 한 뒤 `python3 scripts/eval_golden.py <폴더>` 로 비교합니다. 절차는 `references/scoring.md` "Golden set". 점수 계산 규칙은 `scripts/score.py` 와 `references/scoring.md` 를 함께 고칩니다.

**이력서 형식** — `scripts/render.py`, `references/resume.schema.json`, `references/yaml_schema.md` 를 함께 고칩니다. 문서의 키가 스키마에 없으면 테스트가 실패합니다.

**`data/` 파일 형식** (제목, 표 머리, 키) — 스크립트와 모드 문서 양쪽을 고치고, 기존 사용자 자료를 옮기는 방법을 CHANGELOG 의 "data/ 이전" 줄에 적습니다 (또는 이전 스크립트).

## 5. 이슈 · 브랜치 · 커밋 · PR

- 이슈를 먼저 만들고, 브랜치는 `feat/<이슈 번호>-<짧은 이름>` (예: `feat/13-resume-schema`)
- 커밋 메시지는 한국어. 제목은 `무엇 — 어떻게 (#이슈)`, 본문에 바꾼 파일과 이유
- 사용자가 알아챌 변경은 [`CHANGELOG.md`](CHANGELOG.md) "다음 버전"에 한 줄 (이슈 번호를 끝에)
- PR 본문은 양식(요약 · 확인한 것 · `Closes #번호`)을 채웁니다. 확인하지 못한 것은 못 했다고 적습니다
- 릴리스는 관리자가 합니다: "다음 버전" → `vX.Y.Z — 날짜`, 태그, Releases (절차는 `AGENTS.md`)

## 6. 버그 신고

[새 이슈](https://github.com/jojaden/jobhunt/issues/new/choose)에서 양식을 고릅니다. 로그나 파일을 붙일 때는 이름·연락처·실제 지원 기록 같은 개인 자료를 지워 주세요.
