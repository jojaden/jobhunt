<h1 align="center">jobhunt</h1>

<p align="center">
  한국 개발자 채용 공고를 찾고, 나와 얼마나 맞는지 평가하고, 공고마다 맞춘 이력서·자기소개서를 만들고, 면접 준비와 지원 관리까지 합니다.<br/>
  Codex·Claude Code·Grok 등 어떤 AI 에이전트에서도 쓰는, 쓸수록 내 기준이 쌓여 선별과 이력서가 정확해지는 스킬입니다.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/AI_Agent-Skill-6E56CF?style=flat-square" alt="AI Agent Skill"/>
  <img src="https://img.shields.io/badge/AGENTS.md-Codex_·_Claude_·_Grok-444?style=flat-square" alt="Codex · Claude · Grok"/>
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+"/>
  <img src="https://img.shields.io/badge/Jobs-Korea-1E4FC2?style=flat-square" alt="Korean job boards"/>
  <img src="https://img.shields.io/badge/Output-A4_PDF_%2B_PNG-555?style=flat-square" alt="A4 PDF + PNG"/>
</p>

<p align="center">
  <a href="./README.md">한국어</a> | <a href="./README.en.md">English</a>
  <br/>
  <a href="#-미리보기">미리보기</a> · <a href="#-빠른-시작">빠른 시작</a> · <a href="#-1-공고-찾기">공고 찾기</a> · <a href="#-2-맞춤도-평가">맞춤도 평가</a> · <a href="#-3-맞춤-이력서">맞춤 이력서</a> · <a href="#-쓸수록-정확해지는-개인화">개인화</a> · <a href="#-폴더-구조">폴더 구조</a>
</p>

## 📖 소개

<p align="center"><img src="assets/flow.ko.png" alt="공고 찾기 → 맞춤도 평가 → 맞춤 이력서 → 기록·학습 흐름" width="820"/></p>

**jobhunt**는 AI 에이전트용 스킬(`SKILL.md`·`AGENTS.md`)과 Python 스크립트로 이루어져 있습니다. 특정 AI에 묶여 있지 않아 Codex, Claude Code, Grok, Gemini, Cursor 등 이 폴더의 파일을 읽고 명령을 실행할 수 있는 에이전트라면 같은 절차로 씁니다.

- **스크립트:** 공고 수집, 마감 확인, 지원 현황 기록처럼 판단이 필요 없는 일은 LLM 없이 처리합니다.
- **AI 에이전트:** 공고가 나와 맞는지, 이력서에 무엇을 앞세울지처럼 판단이 필요한 일을 맡고, 모드 문서(`modes/`)의 절차대로 진행합니다.
- **개인 자료:** 전부 `data/`에만 쌓이고 git에 올라가지 않습니다.

### 특징

- 🏢 **회사 넓히기:** 잡보드에 잘 안 올리고 자체 채용 사이트에만 공고를 내는 회사를 찾습니다. 기술 블로그·GitHub 조직 목록, 원티드 회사 정보(연봉 수준·인원), 알려진 회사 목록으로 인지도·규모 점수를 매기고, 홈페이지에서 채용 사이트와 채용 시스템(greetinghr·나인하이어·Greenhouse 등)을 찾아 수집 대상에 넣습니다.
- 🔎 **공고 찾기:** 원티드·점핏·LinkedIn·사람인·Greenhouse(당근·쿠팡·크래프톤 등)·토스·NHN·카카오·greetinghr·나인하이어·Workday·Workable 기업과, 첫 화면에 목록이 없는 자체 채용 사이트(탐색 때 한 번 찾아 둔 목록 API)까지 한 번에 수집합니다. 제목·연차·근무지, 사이트 간 중복(회사 별칭으로 한글·영문 표기 통일), 제외 회사, 재지원 쿨다운을 자동으로 거릅니다.
- 📊 **맞춤도 평가:** 근무지·영어·기술 스택 조건을 공고 문장 근거와 함께 판정합니다. 자격요건·우대사항 한 줄마다 내 경험을 연결해 1~5점으로 매깁니다. 필수와 우대는 "~필요해요"와 "~좋아요" 같은 문장 끝으로 구분합니다.
- 📝 **맞춤 이력서:** 평가에서 나온 계획(앞세울 프로젝트, 기술 교집합, 용어)으로 공고별 yaml을 만들고, 디자인 3종 중 하나로 A4 PDF를 빌드합니다. 빌드할 때마다 페이지 수·링크·문체를 자동으로 검사합니다.
- 📋 **지원 현황:** 평가한 공고와 선별을 통과한 공고를 표 하나에 모아 지원 여부와 마감 여부를 함께 보여 줍니다.
- 📈 **쓸수록 정확해지는 개인화:** "점수가 너무 높다", "내 X 경험을 놓쳤다" 같은 교정과 서류 결과가 `data/`의 기준 파일에 날짜와 함께 쌓입니다.
- 🛡️ **지어내지 않음:** 경험·수치는 내 자료에 있는 것만 씁니다. 추론한 문장은 `[확인 필요]`로 표시하고, 지원서 제출은 사용자가 직접 합니다.
- 🔒 **공개해도 안전:** `data/` 아래 실제 자료는 git에서 빠지고, 폴더 구조와 가상 예시만 올라갑니다.

## 🖼 미리보기

### 공고 현황표 (`jobhunt report`)

가상 회사로 만든 견본입니다(`jobhunt report --demo`). 등본 같은 괘선 서식에 판정 구간별 대장, 지원 권장 도장, 마감 D-일수, 항목별 점수 붙임이 들어갑니다. HTML 한 파일이라 어떤 브라우저·AI 에이전트에서도 열리고, HTML 페이지를 올려 주는 곳(예: Claude Artifact)에는 `--fragment` 판을 올립니다. 디자인 기준은 [`DESIGN.md`](DESIGN.md).

<p align="center"><img src="assets/report.ko.png" alt="공고 현황표 견본: 판정별 결재란, 지원 권장 대장과 인주 도장, 항목별 점수 붙임" width="720"/></p>

텍스트만 되는 환경에서는 `jobhunt tracker report --alive` 가 같은 내용을 표로 출력합니다.

### 맞춤도 평가 (`data/job_postings/*.eval.md`)

<p align="center"><img src="assets/eval.ko.png" alt="맞춤도 평가 리포트 예시: 점수·판정, 조건 판정, 요구사항 대응표, 맞춤 이력서 계획" width="720"/></p>

### 맞춤 이력서 디자인

가상 인물 예시 [`examples/example.yaml`](examples/example.yaml)로 만든 결과입니다.

| A · 에디토리얼 | B · 스위스 그리드 (기본) | C · 다크 마스트헤드 |
|:---:|:---:|:---:|
| <img src="assets/design-a-p1.png" alt="디자인 A" width="260"/> | <img src="assets/design-b-p1.png" alt="디자인 B" width="260"/> | <img src="assets/design-c-p1.png" alt="디자인 C" width="260"/> |

<details>
<summary>디자인 B, 2쪽</summary>
<p align="center"><img src="assets/design-b-p2.png" alt="디자인 B 2쪽" width="520"/></p>
</details>

📄 전체 예시 PDF: [`assets/example-design-b.pdf`](assets/example-design-b.pdf)

## 🚀 빠른 시작

### 1. 설치

다음 중 하나가 필요합니다. Python은 따로 준비하지 않아도 됩니다(설치 도구 uv가 Python 3.12를 함께 받습니다).
- **macOS** (Homebrew)
- **Linux** (Debian/Ubuntu, apt)
- **Windows** (WSL2 + Ubuntu): 아래 [Windows (WSL2)](#windows-wsl2) 참고

```bash
curl -fsSL https://raw.githubusercontent.com/jojaden/jobhunt/main/install.sh | bash
```

이 한 줄이 하는 일:
1. 파이썬 도구 관리자 [uv](https://docs.astral.sh/uv/)가 없으면 설치합니다.
2. `jobhunt` 명령을 설치합니다(`uv tool install`). 도구는 uv가 관리하는 폴더에 따로 들어갑니다.
3. `jobhunt setup`으로 개인 자료 폴더(`~/jobhunt/data`)를 만들고, AI 에이전트에 스킬을 연결하고, 이력서 빌드 환경(Chromium, 한글 폰트, poppler)을 설치합니다.

git·curl이 없으면 Ubuntu는 apt로 설치하고, macOS는 `xcode-select --install`을 안내합니다.

| 설정 | 설명 |
|---|---|
| `JOBHUNT_HOME=경로` | 개인 자료 폴더 (기본 `~/jobhunt`). 바꾸면 셸 설정에도 `export JOBHUNT_HOME=경로`를 넣습니다 |
| `JOBHUNT_REF=v1.2.0` | 버전(태그)이나 브랜치 고정 |
| `JOBHUNT_REPO=주소` | fork한 저장소에서 받을 때 |
| `… \| bash -s -- --no-skill` | 뒤 인자는 `jobhunt setup`으로 넘어갑니다 (아래 옵션) |

예: `curl -fsSL https://raw.githubusercontent.com/jojaden/jobhunt/main/install.sh | JOBHUNT_REF=v1.2.0 bash`

<details>
<summary>예전에 git clone으로 설치했다면</summary>

같은 설치 명령을 다시 실행하면 새 방식으로 바뀝니다.
- `~/jobhunt/data`의 개인 자료는 그 자리에 그대로 둡니다.
- git이 관리하던 도구 파일(코드·지침)과 `.git`은 `~/jobhunt/.old-repo/`로 옮깁니다. 지우지 않으므로 고쳐 둔 파일이 있었다면 거기서 찾을 수 있습니다.
- 그 자리에는 설치된 스킬을 가리키는 짧은 `AGENTS.md`·`CLAUDE.md`가 생기고, 에이전트 스킬 연결도 새 위치로 바뀝니다.
- cron·launchd에 `~/jobhunt/scripts/weekly.sh`를 등록해 두었다면 예약은 그대로 돕니다. 설치 명령이 찾아서 그 경로가 `jobhunt weekly`를 부르도록 이어 둡니다.

</details>

<details>
<summary>직접 설치 (스크립트를 먼저 읽어 보고 싶을 때)</summary>

```bash
uv tool install --python 3.12 git+https://github.com/jojaden/jobhunt
jobhunt setup
```

</details>

<details>
<summary>Claude Code·Codex 플러그인으로 스킬 받기</summary>

스킬을 링크 대신 에이전트의 플러그인으로 받을 수도 있습니다.

```bash
# Claude Code (2.1.275 이상. 대화창에서는 /plugin install jobhunt --marketplace jojaden/jobhunt)
claude plugin install jobhunt --marketplace jojaden/jobhunt

# Codex
codex plugin marketplace add jojaden/jobhunt
codex plugin add jobhunt@jobhunt
```

- **플러그인은 안내만 담습니다.** 지침(`SKILL.md`·`modes/`·`references/`)과 스크립트는 `jobhunt` 명령에 들어 있어서 위 한 줄 설치도 필요합니다. 없으면 플러그인이 처음 실행될 때 설치를 안내합니다. 그래서 지침과 스크립트 버전이 어긋나지 않고, 설치 명령으로 갱신하면 플러그인을 다시 받지 않아도 지침까지 새 버전이 됩니다.
- **스킬이 두 번 보이지 않게** 플러그인이 있는 에이전트에는 `jobhunt setup`이 링크를 만들지 않습니다. 설치 명령을 먼저 실행했다면 플러그인을 설치한 뒤 `jobhunt setup --skill-only`를 한 번 실행해 링크를 정리하세요.
- 슬래시 명령에는 플러그인 이름이 붙습니다: `/jobhunt:jobhunt scan`.

</details>

<a id="windows-wsl2"></a>
<details>
<summary><b>Windows (WSL2)</b></summary>

스크립트는 bash·apt 기반이라 Windows에서는 WSL2의 Ubuntu 안에서 실행합니다.

1. **PowerShell(관리자)**에서 WSL2와 Ubuntu를 설치하고 재부팅합니다.
   ```powershell
   wsl --install -d Ubuntu
   ```
2. 시작 메뉴에서 **Ubuntu**를 열고 사용자 이름·암호를 만든 뒤, 위 한 줄 설치 명령을 그대로 실행합니다. `jobhunt setup`이 Chromium 실행용 라이브러리, 한글 폰트(Noto CJK·Pretendard), poppler를 apt로 설치하므로 중간에 sudo 암호를 물을 수 있습니다.
3. **AI 에이전트도 WSL 안에서 실행합니다.** Codex·Claude Code 등을 Ubuntu 터미널에 설치해 `~/jobhunt`에서 시작해야 스킬 연결(`~/.codex/skills`, `~/.claude/skills`)과 `data/` 경로가 맞습니다. VS Code·Cursor를 쓴다면 WSL 확장으로 이 폴더를 엽니다(`code ~/jobhunt`).

알아 둘 점:
- **개인 자료 폴더는 WSL 홈(`~`) 아래에 두세요.** `/mnt/c/...`(Windows 드라이브)에 두면 파일 접근이 느리고 스킬 링크가 깨질 수 있습니다. `install.sh`는 이 경우 멈춥니다.
- **결과물 열기:** 이력서 PDF·공고 현황표 HTML은 WSL 안에 만들어집니다. `explorer.exe .`로 지금 폴더를 Windows 탐색기에서 열거나, 탐색기 주소창에 `\\wsl$\Ubuntu\home\<사용자>\jobhunt`를 넣으면 됩니다.
- **주간 수집 예약:** WSL은 Windows에 로그인해 있을 때만 돌아갑니다. 정기 실행하려면 WSL의 cron, 또는 Windows 작업 스케줄러에서 `wsl -d Ubuntu -- bash -lc "~/.local/bin/jobhunt weekly"`를 등록합니다.

</details>

`jobhunt setup`이 하는 일:
- **개인 자료 폴더 준비:** `~/jobhunt/data`에 폴더 구조와 예시 파일을 만듭니다(있는 파일은 건드리지 않음). 스킬을 읽지 않는 에이전트도 찾아가도록 `AGENTS.md`·`CLAUDE.md`를 둡니다.
- **AI 에이전트 스킬 연결:** 설치된 에이전트를 찾아 스킬 폴더(Claude Code `~/.claude/skills`, Codex `~/.codex/skills`)에 설치된 스킬을 링크합니다. 업데이트하면 스킬도 바로 새 버전이 됩니다. jobhunt 플러그인이 깔린 에이전트는 건너뜁니다.
- **빌드 환경:** Playwright Chromium, 폰트(Pretendard, Noto CJK KR), poppler를 설치합니다.

| 옵션 | 설명 |
|---|---|
| `--skill-only` | 스킬 연결만 |
| `--no-skill` | 스킬 연결 없이 빌드 환경만 |
| `SKILLS_DIR=경로[:경로…]` | 스킬 폴더를 직접 지정할 때 (다른 에이전트, 여러 곳) |

같은 이름의 다른 스킬이 이미 있으면 덮어쓰지 않고 알려 줍니다. 예전 jobhunt를 가리키던 링크는 새 위치로 바꿉니다.

> **왜 도구와 내 기록을 나눠 두나요?**
>
> - **업데이트해도 내 기록은 그대로입니다.** 도구는 uv가 관리하는 폴더에, 기록은 `~/jobhunt/data`에 따로 있어 업데이트가 기록을 건드리지 않습니다. 도구 파일을 실수로 고쳐 업데이트가 깨지는 일도 없습니다.
> - **도구를 고치지 않아도 내 것이 됩니다.** 목표 역할·연봉·제외 조건(`data/profile/`), 경험 근거(`data/experience/`), 검색 조건·우선 기업(`data/search/`), 판정을 고친 사례와 작업 규칙이 모두 `data/`에 쌓이고, 다음 실행이 그대로 씁니다.
> - **도구 자체를 바꾸고 싶다면** 저장소를 fork·clone해서 고치고 PR로 보내 주세요([`CONTRIBUTING.md`](CONTRIBUTING.md)). clone한 폴더에서는 `python3 scripts/cli.py <명령>`이 `jobhunt <명령>`과 같은 일을 하고, 그 폴더의 `data/`를 씁니다.
> - **자료가 내 PC 밖으로 나가지 않습니다.** 공고 수집과 이력서 빌드는 이 PC의 Python·Chromium으로 돌고, 개인 자료는 로컬 파일로만 남습니다.

업데이트:

```bash
curl -fsSL https://raw.githubusercontent.com/jojaden/jobhunt/main/install.sh | bash
```

버전은 `v1.2.0`처럼 태그로 붙입니다. 설치 명령으로 갱신하면 그 사이 바뀐 점을 보여 주고, 나중에도 `jobhunt changes <이전 버전>`으로 볼 수 있습니다([`CHANGELOG.md`](CHANGELOG.md), [Releases](https://github.com/jojaden/jobhunt/releases)). `data/` 형식이 바뀐 버전은 옮기는 방법을 함께 적습니다. 지금 버전은 `jobhunt --version`.

에이전트별로 시작하는 법:

| 에이전트 | 시작 |
|---|---|
| Codex | `cd ~/jobhunt && codex` — `AGENTS.md`를 읽고, 스킬(`~/.codex/skills`)로도 연결됩니다 |
| Claude Code | `cd ~/jobhunt && claude` — `CLAUDE.md`가 `AGENTS.md`를 불러오고, 스킬(`~/.claude/skills`)로도 연결됩니다 |
| Grok·Gemini·Cursor 등 | `~/jobhunt`에서 에이전트를 열고 "`AGENTS.md`를 읽고 시작해줘"라고 하면 됩니다 |

웹 검색(Firecrawl 등)이나 HTML 페이지 게시(Claude Artifact 등)처럼 에이전트마다 다른 기능은 있으면 쓰고, 없으면 파일 경로를 알려 주거나 해당 채널을 "미수집"으로 보고합니다.

### 2. AI 에이전트에게 이렇게 말하면 됩니다

| 말하기 | 일어나는 일 |
|---|---|
| "처음 설정해줘" | 목표 역할·연봉·근무지·제외 조건을 묻고 `data/profile/`에 기준을 만듭니다 |
| "공고 찾아줘" | `jobhunt weekly`로 수집한 뒤, 새 공고를 내 기준으로 1차 선별해 현황표로 보여 줍니다 |
| (공고 URL을 붙여넣고) "이 공고 어때?" | 판정과 점수, 조건 확인, 요건과 내 경험 대응표, 지원 전략 |
| "이 공고용 이력서 만들어줘" | 평가의 계획으로 yaml 작성 → PDF 빌드 → 검사 → 수정 반복 |
| "자소서 써줘" / "지원서 문항 답 써줘" | 문항별 구조로 초안 작성, 글자 수 제한·문체 검사 (`jobhunt cover-check`) |
| "이 회사 조사해줘" | 제품·팀·기술·개발 문화·회사 상태·경고 신호를 출처와 함께 정리 (지원 동기·역질문 재료) |
| "면접 준비해줘" | 전형별 준비, 이력서에서 나올 질문과 꼬리질문, 기술 질문, 행동 질문, 역질문 연습지 |
| "모의 면접 해줘" | 면접관처럼 한 문항씩 묻고 내 답에 꼬리질문, 답마다 짧은 피드백 |
| "지원했어" / "서류 붙었어" / "면접 봤어" | 현황표 갱신, 재지원 쿨다운, 면접 기록, 결과가 쌓이면 원인 분석과 기준 조정 제안 |
| "메뉴" (또는 모드 이름만) | 쓸 수 있는 모드와 지금 할 만한 다음 단계 |

### 3. 명령만 따로 쓰기

```bash
jobhunt weekly                       # 수집 → 마감 확인 → 현황표 (LLM 없이, cron·launchd 가능)
jobhunt scan --dry-run               # 파일을 쓰지 않고 수집 결과만 보기
jobhunt report                       # 공고 현황표 HTML (data/search/reports/postings.html)
jobhunt tracker report --alive       # 같은 내용을 텍스트 표로 (마감 여부 포함)
jobhunt tracker set 3 지원함          # 지원 기록
jobhunt render data/resumes/<이름>.yaml   # 이력서 빌드 (yaml → PDF · PNG, 검사까지)
jobhunt where                        # 개인 자료 폴더 위치 (jobhunt --help: 전체 명령)
```

## 🔎 1. 공고 찾기

`jobhunt scan`이 공고를 수집하고, 자격요건 본문을 `data/search/inbox/`에 저장합니다. 1차 선별은 AI 에이전트가 `data/profile/brief.md`의 기준으로 합니다.

| 소스 | 방법 | 자동화 |
|---|---|---|
| 원티드, 점핏 | 공개 JSON 목록·상세 | `scan.py` |
| LinkedIn | 비로그인 공개 API, 한국어 공고만 (영어 전용 JD 제외) | `scan.py` |
| 사람인 | 검색 페이지 HTML → 공고 상세 | `scan.py` |
| Greenhouse·Lever 기업 (당근, 쿠팡, 크래프톤, 채널톡 …) | 공식 공개 API | `scan.py` |
| 토스 전 계열사, 네이버, 카카오, NHN, greetinghr·나인하이어 기업, 공고 링크가 HTML에 있는 채용 페이지 | 채용 사이트 JSON·HTML | `scan.py` (회사는 `discover.py`가 찾아 넣음) |
| Workday·Workable·Ashby·잡플렉스(recruiter.co.kr)·라운드HR·SK Careers 기업 | 채용 시스템 공개 목록 API | `scan.py` (`discover.py`가 채용 시스템을 판별·검증) |
| 첫 화면에 공고 목록이 없는 자체 채용 사이트 (탭·버튼 뒤, 스크립트로 그림) | 탐색 때 한 번 찾은 목록 API(`jsonapi`)·사이트맵 | `scan.py` (`discover.py probe`가 헤드리스 브라우저로 찾아 둠, 매주 수집은 브라우저 없이) |
| 잡코리아, 리멤버, 봇 차단·토큰이 필요한 기업 사이트 | HTML·브라우저·Firecrawl | AI 에이전트가 회사별 읽는 법(`sources.yaml`의 `browse`)과 [`references/judgment.md`](references/judgment.md) §2 유형표대로 수집하고, 결과는 공고 현황표의 "직접 확인한 곳" 장에 남김 |

- **거르는 기준:** 제목 키워드, 요구 연차(숫자가 있을 때), 근무지, 이미 본 공고(다른 사이트에 같은 공고 포함), 제외 회사, 지원 후 재지원 쿨다운(기본 6개월), 영어 전용 JD(설정 시).
- **거르지 않는 기준:** 기술 스택은 수집할 때 거르지 않습니다. 검색어를 특정 언어로 좁히면 언어를 따지지 않는 좋은 공고가 빠지기 때문이에요. 수집 단계에서는 자격요건 문장의 필수/우대 힌트만 붙이고, 판정은 선별 단계에서 합니다. 선별 때 자격요건이 내가 쓰지 않는 언어를 꼭 요구하면(`targets.yaml`의 `stack_languages`로 판단, "등"·"이에 준하는" 같은 여지가 없을 때만) 스크립트가 제외 초안과 근거 문장을 채우고, 에이전트는 그 문장만 확인합니다.
- **마감 판정:** `jobhunt alive`가 사이트별 상세 API로 확인합니다. 공개 목록에서 사라졌다고 마감으로 보지 않습니다.

## 📊 2. 맞춤도 평가

[`modes/evaluate.md`](modes/evaluate.md)의 순서로 "지원할까?"에 답하고 `data/job_postings/<공고>.eval.md`에 남깁니다.

| 절 | 내용 |
|---|---|
| 판정 | 점수·판정과 항목별 점수, 한 줄 이유, 근무지·언어·연봉 조건 요약 |
| 이 자리 | 회사·팀이 만드는 것, 매일 하는 일, 고용 형태·연차·마감, 가장 가까운 내 목표 역할 |
| 조건 | 근무지·영어·기술 스택·연차·고용 형태·연봉 하한을 공고 문장 인용과 함께 통과 / 제외 / 불명확 |
| 요건과 내 경험 | 자격요건·우대사항 ↔ 내 경험(근거 파일), 충족 / 부분 / 없음, 빈틈마다 대응 |
| 보상과 근무 | 포괄임금제, 수습, 성과급·스톡옵션, 재택 등 한국 채용 조건 |
| 지원 전략 | 이력서 계획(기본본, 프로젝트 순서, SKILLS, 용어, SUMMARY 방향), 자소서 문항별 사례, 첫 예상 면접 질문 |
| 확인할 점 | 게시일·재게시, 공고와 회사 정보의 어긋남, 공고 안의 AI 대상 지시문, 리크루터에게 물을 것 |

AI 에이전트가 공고를 한 줄씩 분류하면(해 본 일인지, 필수 요건을 채웠는지, 우대 중 포지션의 핵심 기술은 무엇인지, 원하는 방향의 일인지) `jobhunt score`가 계산합니다. 점수는 두 층으로 나뉩니다.

- **공통 기준 (누구에게나 같음):** 필수·우대를 얼마나 채웠는지로 등급이 정해집니다. 모두 충족하면 4.9 이상, 필수와 포지션 핵심 우대를 채우면 4.5 이상, 필수와 우대 절반 이상이면 4.0 이상, 필수나 핵심 우대를 못 채우면 3.9 이하입니다.
- **개인 선호:** 하고 싶은 일·피하는 일·가점(`data/profile/targets.yaml`)은 등급 안에서 순서만 바꿉니다.

계산 뒤에는 에이전트가 공고 전체를 다시 읽고(연차·범위, 채용 측이 무겁게 볼 요건) 조정 이유를 판정 파일에 남깁니다([`references/judgment.md`](references/judgment.md)). 근무지와 보상은 점수가 아니라 조건으로만 봅니다. 기준은 [`references/scoring.md`](references/scoring.md).

## 📝 3. 맞춤 이력서

[`modes/tailor.md`](modes/tailor.md)의 순서로 진행합니다. 평가가 있으면 "지원 전략"의 이력서 계획을 그대로 추천안으로 씁니다.

| 단계 | AI 에이전트가 하는 일 |
|---|---|
| 0. 지원 방향 | 평가의 맞춤 계획을 보여 주고 가장 가까운 기본본(`base_*.yaml`)을 고릅니다 |
| 1. 자료 수집 | 경험 문서, 로컬 git 로그(`jobhunt git-log`), GitLab MR, 기존 이력서에서 근거와 함께 프로젝트 후보를 모읍니다 |
| 2. 추가 요구사항 | 강조할 점, 뺄 내용, 페이지 수를 이번 공고용 또는 계속 쓸 설정으로 저장합니다 |
| 3. 포트폴리오 | GitHub·블로그 링크와 프로젝트별 관련 글, 링크 접속 확인 |
| 4. 작성과 빌드 | yaml 작성(추론 문장은 `[확인 필요]`), `render.py`로 PDF·PNG 빌드 |
| 5. 검수와 수정 | 검사 결과, 수정 전·후 문장, 태그 붙은 사실 확인을 확정할 때까지 반복합니다 |

**빌드 옵션** (`jobhunt render <yaml>`)

| 옵션 | 설명 |
|---|---|
| `--design A\|B\|C` | 디자인 (기본: yaml `meta.design`, 없으면 B) |
| `--profile PATH` | 개인정보 yaml (기본: `data/profile/profile.yaml`) |
| `--out DIR` | 산출물 폴더 (기본: `data/output`) |
| `--offline` | 링크 접속 검사 생략 |
| `--no-png` / `--no-check` | PNG 미리보기 / 빌드 후 검사 생략 |

**빌드 후 검사** (`jobhunt check`)

| 항목 | 기준 | 수준 |
|---|---|---|
| 형식 | `references/resume.schema.json` — 모르는 키(오타), 타입, 쓸 수 없는 값. 빌드 전에 검사해 틀리면 빌드하지 않음 | 오류 |
| 페이지 수 | `meta.target_pages` (기본 2~3) | 오류 |
| 제목 홀로 남음 | 제목 뒤 같은 쪽 본문 3줄 미만 | 오류 |
| 링크 | PDF 안 모든 링크 접속 | 열리지 않음=오류, 확인 불가=경고 |
| 플레이스홀더 | `【 】`, `TODO`, `TBD`, `[확인 필요]` … | 오류 |
| 금지어 · 기호 | `references/style_rules.yaml` | 오류 |
| 번역투 · 개념어 | 같은 파일 `translationese` | 경고 |
| SUMMARY 말투 | 첫 문단 문장마다 `~니다`로 끝남 | 오류 |

## 📈 쓸수록 정확해지는 개인화

도구(`SKILL.md`, `modes/`, `scripts/`, `references/`)는 uv가 설치하고 업데이트하며, 내 기준과 기록은 개인 자료 폴더의 `data/`에만 쌓입니다.

| 알게 된 것 | 쌓이는 곳 |
|---|---|
| 목표 역할, 이직 서사, 연봉, 근무지·언어·스택 조건(실무로 쓴 언어 `stack_languages`), 가점·감점 신호 | `data/profile/targets.yaml` |
| 1차 선별용 짧은 요약 | `data/profile/brief.md` |
| 경험·프로젝트 근거, 확인받은 사실 | `data/experience/` |
| 작업 규칙, 보고 형식, 이력서 표현 결정 | `data/preferences/standing.md` |
| 검색 조건, 우선 기업, 대기함, 본 공고 기록 | `data/search/` |
| 공고 원문과 평가 | `data/job_postings/` |
| 지원 현황과 결과, 자기소개서 답 | `data/applications/` |
| 면접 연습지, 행동 질문 사례, 면접 기록 | `data/interview/` |

- 판단을 교정하면 그 성격에 맞는 파일에 날짜와 함께 적습니다. 바뀐 결정은 지우지 않고 이전 값을 남깁니다.
- 지원 결과가 3건 이상 쌓이면, 점수와 실제 결과가 어긋난 부분을 찾아 기준 조정을 제안합니다.
- 설계와 단계는 [`docs/ROADMAP.md`](docs/ROADMAP.md)에 있습니다.

## 📁 폴더 구조

```
install.sh                   한 줄 설치 (uv → jobhunt 설치·갱신 → jobhunt setup, 예전 git 설치 전환)
pyproject.toml               jobhunt 패키지 (uv tool install 로 설치하는 명령)
.claude-plugin/ plugin/      Claude Code·Codex 플러그인 저장소와 플러그인 (설치된 스킬로 안내만 함)
AGENTS.md                    모든 AI 에이전트용 작업 안내 (CLAUDE.md 는 이 파일을 불러옴)
LEGAL_DISCLAIMER.md          사용 범위와 면책
CHANGELOG.md                 변경 기록 (버전마다 data/ 이전 안내)
CONTRIBUTING.md              기여 안내 (개발 환경, 확인 방법, 새 수집기 추가)
SKILL.md                     스킬 진입점, 요청을 모드로 연결
modes/                       공통 규칙과 모드별 절차 (onboard · scan · evaluate · tailor · cover · deep · interview · track · outcome)
scripts/
  cli.py                     jobhunt 명령 (명령마다 아래 스크립트를 그대로 실행)
  scan.py · providers/       공고 수집 (사이트별 모듈)
  discover.py                회사 찾기 (채용 사이트·채용 시스템 판별 → 수집 대상 추가)
  alive.py                   마감 확인
  tracker.py                 지원 현황 기록, 통합 현황표
  cover_check.py             자기소개서 문항 글자 수·문체 검사
  eval_golden.py             판정 정답 세트와 에이전트 판정 비교 (분류 규칙을 바꿨을 때)
  weekly.py                  주간 스캔 (scan → alive → report, weekly.sh 는 예전 경로용)
  render.py                  yaml → HTML → PDF + PNG, 디자인 A/B/C
  check.py · check_links.py  빌드 후 검사, 링크 접속 확인
  git_log.sh                 로컬 git 저장소에서 내 커밋 로그 추출
  setup.sh                   설치: 스킬 연결 + Chromium, 폰트, poppler (jobhunt setup 이 실행)
  privacy_check.py           개인 자료 커밋 방지 (CI, .githooks/pre-commit)
references/
  sources.md                 채용 사이트별 수집 방법
  yaml_schema.md · resume.schema.json   이력서 yaml 형식 (설명 · 검사와 편집기 자동완성용 스키마)
  writing_rules.md           문장 규칙과 점검 방법
  style_rules.yaml           금지어 · 번역투 · 기호 한도
  resume_guide.md            이력서 일반 규칙
  cover_letter.md            자기소개서·지원서 문항 작성법
  interview_questions.md     면접 질문 방식·꼬리질문 패턴·답변 구조
docs/ROADMAP.md              설계와 단계
examples/example.yaml        가상 인물 예시
examples/golden/             판정 정답 세트 (가상 지원자·공고·정답)
tests/                       도구를 고친 뒤 돌리는 테스트 (네트워크 없이, python3 -m unittest discover -s tests)
assets/                      README 미리보기 이미지와 예시 PDF
data/                        내 자료 (git 제외, 구조와 예시만 올라감. 설치본은 ~/jobhunt/data)
  profile/ experience/ preferences/ portfolio/ search/ job_postings/ applications/ resumes/ output/ interview/
```

## 🔒 개인정보

- `data/` 아래 실제 파일은 `.gitignore`로 빠지고, 폴더 README·`.gitkeep`·`*.example.*`만 올라갑니다.
- `git add -f` 같은 실수도 막습니다. CI가 PR마다 `data/`의 추적 파일을 검사하고, 커밋 전 훅(`git config core.hooksPath .githooks`로 켬)은 커밋하는 내용에 `profile.yaml`의 이름·이메일·전화번호·학교가 있으면 멈춥니다 (`scripts/privacy_check.py`).
- 이름·연락처는 코드에 없고, 빌드할 때 `data/profile/profile.yaml`에서 읽습니다.
- 원티드·점핏·LinkedIn 게스트 API·기업 사이트 JSON은 비공식 엔드포인트라 개인 용도로 요청 간격을 두고 씁니다.

## ⚖️ 사용 범위와 면책

쓰기 전에 [`LEGAL_DISCLAIMER.md`](LEGAL_DISCLAIMER.md)를 읽어 주세요. 요약하면:

- **개인 구직 용도로만.** 대량 수집, 수집한 공고의 재배포·판매는 범위 밖입니다. 각 사이트의 약관은 사용자가 확인합니다. 요청 간격을 두고, 봇 차단은 우회하지 않습니다.
- **내 PC에만 저장.** 만든 사람이 운영하는 서버나 사용 기록 수집은 없습니다. AI 에이전트를 쓰면 대화와 읽은 파일은 내가 고른 AI 서비스로 갑니다.
- **AI는 틀리거나 지어낼 수 있습니다.** 점수는 참고 의견이고, 이력서·자기소개서는 제출 전에 사실인지 직접 확인하세요. 지원서 제출은 사용자가 직접 합니다.
- MIT 라이선스로 "있는 그대로" 제공되며, 결과에 대한 보증은 없습니다.

## 🤝 기여

고치거나 넓히려면 [`CONTRIBUTING.md`](CONTRIBUTING.md)를 봐 주세요. 사이트 응답 형식이 바뀌어 수집이 멈췄다면 [이슈 양식](https://github.com/jojaden/jobhunt/issues/new/choose)으로 알려 주세요.

## 🙏 참고

모드로 나눈 스킬 구성과 개인화 파일 구조(도구와 개인 자료 분리, 파일이 원본, 쓸수록 개인화)는 [career-ops](https://github.com/santifer/career-ops)의 아이디어를 참고했습니다. 감사합니다.

## 📄 라이선스

[MIT](./LICENSE)
