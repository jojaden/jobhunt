# resume.yaml format

Content is yaml, layout is `jobhunt render`. Personal details (name, email, phone) stay out of the yaml and are read from `data/profile/profile.yaml`.

The machine-readable version is `references/resume.schema.json` (JSON Schema). `render.py` and `check.py` validate against it before anything else, so an unknown key (a typo such as `sumary`), a wrong type or a value outside the allowed set stops the build with its location. Keep the schema and this page in sync when either changes. Start every resume yaml with the schema line so editors (VS Code YAML extension and others using yaml-language-server) autocomplete and flag errors as you type:

```yaml
# yaml-language-server: $schema=../../references/resume.schema.json      (in data/resumes/)
```

## Inline markup

| Write | Result |
|---|---|
| `**굵게**` | bold |
| `` `코드` `` | monospace code |
| `[글자](https://주소)` | link |
| `[확인 필요] 문장` | yellow highlight. The checker flags it as an error. Remove the tag after the user confirms |

Use only the markup above; HTML tags print as literal text.

## Full structure

```yaml
meta:
  job: Backend                 # 2nd filename slot. If empty, the header job title below → 홍길동_Backend_가나다_v1.pdf
  version: 가나다_v1           # 3rd filename slot
  position: 서비스 백엔드       # target position (memo)
  design: B                    # A editorial / B Swiss grid (default) / C dark masthead
  target_pages: [2, 3]         # check target. A single integer also works
  posting: data/job_postings/2026-10-01_가나다_백엔드.md   # posting file (optional)
  omit_sections: []            # section keys to drop: summary, skills, experience, projects, other

header:
  role: Backend Developer      # the one job-title line under the name, no subtitle. If empty, profile role; with neither, the line is dropped

portfolio:                     # if absent, the PORTFOLIO box and header links are dropped
  items:
    - { label: github.com/me, url: "https://github.com/me" }
  desc: "기술 블로그. …"

summary:
  lead: "… 4년차입니다. … 담당하고 있습니다."   # '~합니다' style (checked)
  bullets: ["…", "…"]                         # clipped style

skills:
  - { name: Backend, items: "Kotlin · Spring Boot · MySQL" }

experience:
  - company: 회사명
    title: 백엔드 개발자
    period: "2022.03 ~ 재직 중"
    tenure: 4년차              # years label. If empty, the period shows without parentheses
    intro: "회사·제품 한두 줄"
    timeline:
      - { period: "2025.07 ~", desc: "…" }

projects:                      # max 5. Numbered 01, 02 … in order
  - title: "주문 API p99 820ms → 240ms : …"
    period: "2025.02 ~ 05"
    role: 설계·개발 단독
    techs: [Kotlin, Redis]
    summary: "요약 바 1~2줄"
    rows:
      - { label: 문제, text: "…" }
      - { label: 원인 규명, text: ["문단1", "문단2"] }
      - label: 선택지
        options:
          - { title: "① DB 읽기 복제본 추가", adopted: false, body: "장점. 그러나 단점" }
          - { title: "② 조회 묶기 + 캐시 키 분산", adopted: true, body: "채택 근거 + 약점 통제" }
      - { label: 실행, bullets: ["…", "…"] }
      - label: 결과
        kpis:
          - { value: "820ms → 240ms", label: "주문 API p99" }
      # to split one project into A/B
      - sub: { num: "A.", title: "소제목" }
      - group: { num: "B.", title: "점선 아래 하위 블록", rows: [ …same row format… ] }
    links:                     # 1–2 per project
      - { title: "글 제목", url: "https://…" }

other:
  - "**제목** (기간) — 한 줄"

extra_sections:                # user-added sections (optional)
  - title: CERTIFICATES
    title_ko: 자격증            # Korean title used by design C
    after: other               # placed after this section
    items: ["정보처리기사 (2020)"]
```

Section order is fixed: header → PORTFOLIO → SUMMARY → SKILLS → EXPERIENCE → PROJECTS → OTHER (→ extra). There is no EDUCATION section.
