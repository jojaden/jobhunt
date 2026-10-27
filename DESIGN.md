---
name: jobhunt posting report (공고 현황)
description: The weekly posting queue issued as one ruled Korean official certificate — 발급 번호, 결재란, 판정 도장.
colors:
  paper: "#ffffff"
  ink: "#17191c"
  ink-2: "#4a5059"
  ink-3: "#6b717a"
  rule: "#1b1d21"
  rule-2: "#c9ced6"
  cell: "#e8ecf1"
  cell-2: "#f4f6f9"
  seal: "#b3122e"
  blue: "#1f3a8a"
  blue-soft: "#e6ebf6"
  paper-dark: "#15171a"
  ink-dark: "#e9eaec"
  ink-2-dark: "#b4b9c1"
  ink-3-dark: "#8d939c"
  rule-dark: "#9aa1ab"
  rule-2-dark: "#3a3f47"
  cell-dark: "#22262c"
  cell-2-dark: "#1b1e22"
  seal-dark: "#ef5a72"
  blue-dark: "#8fa9ff"
  blue-soft-dark: "#1e2640"
typography:
  display:
    fontFamily: "Nanum Myeongjo, AppleMyungjo, Batang, 바탕, serif"
    fontSize: "clamp(2rem, 3.4vw, 2.75rem)"
    fontWeight: 800
    lineHeight: 1.1
    letterSpacing: "0.02em"
  headline:
    fontFamily: "Nanum Myeongjo, AppleMyungjo, Batang, 바탕, serif"
    fontSize: "1.25rem"
    fontWeight: 800
    lineHeight: 1.3
    letterSpacing: "0.04em"
  title:
    fontFamily: "Nanum Myeongjo, AppleMyungjo, Batang, 바탕, serif"
    fontSize: "1rem"
    fontWeight: 700
    lineHeight: 1.6
    letterSpacing: "0.04em"
  body:
    fontFamily: "Apple SD Gothic Neo, Pretendard, Malgun Gothic, 맑은 고딕, Noto Sans KR, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.55
    fontFeature: "tnum"
  label:
    fontFamily: "Apple SD Gothic Neo, Pretendard, Malgun Gothic, 맑은 고딕, Noto Sans KR, system-ui, sans-serif"
    fontSize: "0.8rem"
    fontWeight: 600
    letterSpacing: "0.12em"
  numeral:
    fontFamily: "Apple SD Gothic Neo, Pretendard, Malgun Gothic, 맑은 고딕, Noto Sans KR, system-ui, sans-serif"
    fontSize: "1.3rem"
    fontWeight: 700
    lineHeight: 1.2
    fontFeature: "tnum"
  code:
    fontFamily: "ui-monospace, SF Mono, Menlo, monospace"
    fontSize: "0.85em"
rounded:
  none: "0"
  seal: "50%"
spacing:
  s-1: "0.25rem"
  s-2: "0.5rem"
  s-3: "0.75rem"
  s-4: "1rem"
  s-5: "1.5rem"
  s-6: "2.5rem"
components:
  seal-recommend:
    textColor: "{colors.seal}"
    typography: "{typography.title}"
    rounded: "{rounded.seal}"
    size: "2.9rem"
  stamp-consider:
    textColor: "{colors.blue}"
    typography: "{typography.title}"
    rounded: "{rounded.none}"
    size: "2.6rem"
  ledger-head-cell:
    backgroundColor: "{colors.cell}"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.none}"
    padding: "0.25rem 0.5rem"
  ledger-head-cell-hover:
    backgroundColor: "{colors.blue-soft}"
  ledger-head-cell-pressed:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
  ledger-value-cell:
    typography: "{typography.numeral}"
    padding: "0.75rem 0.5rem"
  table-head:
    backgroundColor: "{colors.cell}"
    textColor: "{colors.ink-2}"
    typography: "{typography.label}"
    padding: "0.5rem 0.75rem"
  table-cell:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    padding: "0.5rem 0.75rem"
  attachment-row:
    backgroundColor: "{colors.cell-2}"
    textColor: "{colors.ink-2}"
    padding: "0.75rem 1rem"
  query-input:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "0.25rem 0"
    width: "min(28rem, 100%)"
  ink-box-mark:
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "0 0.3em"
---

# Design System: jobhunt posting report (공고 현황)

## Overview

**Creative North Star: "The Issued Certificate"**

The posting queue is not a dashboard; it is one official document issued on a given day. It reads like a Korean 공문 서식: a Myeongjo title, 발급일 and 발급 번호 at the upper right, a 결재란 box of counts, then a ruled ledger split into verdict bands, closed with "위와 같이 … 발급합니다. 끝." Every surface is white form paper, black rules and pale steel-grey header cells. Colour is not decoration: red 인주 exists only on a 지원 권장 seal, ink-blue only on 지원 고려 and on links, and everything below those bands fades toward grey ink.

The density is that of a real form: fixed-width cells, tabular numerals, one line of reason per row, the itemised score folded away as a 붙임 attachment row. Depth comes from rules, double rules and cell shading, never from cards, pills or shadows. Dark mode is a carbon copy: charcoal paper, light rules, identical seal logic.

The system has one generator. Every posting report is produced by `scripts/report_html.py`; nothing in this file describes hand-written HTML. The output is one self-contained file (inline CSS and JS, standard-library Python, no build step) that opens in any browser and can be produced or read by any AI agent (Claude Code, Codex, others). The only external resource is the title face; without network the installed Myeongjo fallbacks carry the same look. Hosts that publish HTML (Claude Artifacts) receive the `--fragment` output, which omits `<html>`/`<head>`/`<body>`; publishing is optional delivery, never a dependency. Changes to this DESIGN.md ship together with changes to `report_html.py`, and the reverse.

**Key Characteristics:**
- One certificate per issue: title block, 결재란, verdict bands, closing sentence, footer legend.
- Ruled, square, flat: 1px rules, 3px double rules at the document's top and bottom, zero radius except the round seal.
- Colour-as-law: red means 지원 권장, blue means 지원 고려 or a link, grey means lower bands; nothing else is coloured.
- Myeongjo for headings and stamps, system Korean gothic with tabular numerals for everything read or compared.
- Bands darken ink from top to bottom of the queue (권장 → 확인) by lightening their text.
- Reads on a phone as stacked records, not a squeezed table.

## Colors

A monochrome form palette of paper, ink and rules, with exactly two legal inks: seal red and approval blue.

### Primary
- **Seal Vermilion 인주** (`seal`): the red of a 도장 pad. Used only for the 지원 권장 seal, its count in the 결재란, and the legend seal. In dark mode it lifts to a lighter rose (`seal-dark`) so the ring stays legible on charcoal.

### Secondary
- **Approval Ink Blue 청 결재** (`blue`): 지원 고려 stamps and count, every link, the focus ring, the input caret, the live application state (지원함, 면접 …). Dark mode uses a periwinkle (`blue-dark`).
- **Blue Wash** (`blue-soft`): hover shading on 결재란 header cells and text selection.

### Neutral
- **Form Paper** (`paper`): page background; also the knock-out ring inside the seal.
- **Ink 먹** (`ink`): primary text, company names, box-mark borders, the pressed state of the 마감 7일 이내 toggle.
- **Secondary Ink** (`ink-2`): sub-lines, header-cell labels, reasons (비고), locations, 보류 band text.
- **Faded Ink** (`ink-3`): row numbers, placeholders, units (/5, 건), 확인 필요 band text, struck-through 불합격 and past deadlines, dotted leaders.
- **Frame Rule 괘선** (`rule`): outer table frames, the 결재란 border, header-cell bottom rules, double rules, the attachment's left rule, the query underline.
- **Inner Hairline** (`rule-2`): every inner cell border, link underlines at rest, scrollbar thumb, the empty-state dashed box.
- **Header Cell Shade** (`cell`): table header row, 결재란 header cells and its vertical 판정 title cell.
- **Attachment Shade** (`cell-2`): background of the unfolded 붙임 score row.

### Named Rules
**The Colour-as-Law Rule.** Red appears only where the verdict is 지원 권장; blue only where it is 지원 고려, or on a link, focus ring or live application state. A new element that wants colour must first earn one of those meanings; otherwise it is ink.

**The Fading Ink Rule.** Bands lose ink as they descend: 보류 company, title and score drop to `ink-2` at weight 500; 확인 필요 company and title drop to `ink-3` at weight 500. Never re-emphasise a lower band with colour or weight.

**The Carbon Copy Rule.** Dark mode swaps only token values (paper, ink, rules, cells, seal, blue); structure, weights and colour meanings are identical. It follows `prefers-color-scheme` and can be forced either way with `data-theme="light"` or `data-theme="dark"` on the root; `color-scheme` is set per theme so native scrollbars, inputs and selection follow.

## Typography

**Display Font:** Nanum Myeongjo 700/800 (with AppleMyungjo, Batang, 바탕, serif)
**Body Font:** Apple SD Gothic Neo (with Pretendard, Malgun Gothic, 맑은 고딕, Noto Sans KR, system-ui)
**Label/Mono Font:** body gothic for labels and numerals; ui-monospace / SF Mono / Menlo for file paths only

**Character:** A certificate heading over a clerk's gothic. Myeongjo carries authority (title, band heads, stamps, the attachment number, the closing sentence); gothic carries everything scanned and compared. Numerals are the body face with tabular figures, never a separate display numeral face.

Font status: Nanum Myeongjo is loaded from Google Fonts (one `<link>`, weights 700 and 800) as the current choice. Loading an external font is awaiting the user's confirmation; if declined, the stack falls through to installed AppleMyungjo / Batang with no layout change.

### Hierarchy
- **Display** (Myeongjo 800, clamp(2rem, 3.4vw, 2.75rem), 1.1, +0.02em, balanced wrap): the single document title 공고 현황.
- **Headline** (Myeongjo 800, 1.25rem, 1.3, +0.04em): band heads 지원 권장 / 지원 고려 / 보류 / 확인 필요 / 지원 기록, followed inline by the score range (gothic 400, .85rem, `ink-2`) and count (gothic 500, .9rem).
- **Title** (Myeongjo 700, 1rem, 1.6, +0.04em): the closing sentence; the same face at .85rem/700 for 붙임 n. and .95rem/800 with +0.2em vertical setting for the 결재란 판정 title.
- **Body** (gothic 400, 15px, 1.55, tabular-nums): cells and prose; reasons capped at 60ch.
- **Numeral** (gothic 700, 1.3rem, 1.2): 결재란 counts. Scores are gothic 600 at 1.05rem with a `ink-3` 0.75rem "/5".
- **Label** (gothic 600, .8rem, +0.12em, `ink-2`, no wrap): table header cells. 결재란 header cells are .8rem at +0.06em; issue terms (발급일, 발급 번호) and the 조회 label are .85rem at +0.08em.

### Named Rules
**The Two Voices Rule.** Myeongjo speaks for the issuing office (title, band heads, stamps, attachment number, closing); gothic speaks for the data. Never set a data cell or a number in Myeongjo.

**The Tabular Figures Rule.** `font-variant-numeric: tabular-nums` is set on the body; every score, count, date and issue number aligns in fixed-width columns.

## Layout

One centred sheet, max 1440px, inline padding clamp(16px, 3vw, 40px), block padding 2.5rem. The spacing scale is s-1 … s-6 (0.25, 0.5, 0.75, 1, 1.5, 2.5rem); bands sit s-6 apart, blocks within the header s-5 apart, cell padding is s-2 × s-3.

Order of the sheet: title block (title and sub-line left, 발급일 / 발급 번호 definition list right-aligned) closed by a double rule; the 결재란; the 조회 row (label, underline-only search input, live count); verdict bands in fixed order 권장 → 고려 → 보류 → 확인, each a framed table; the 지원 기록 band; the 직접 확인한 곳 and 판정 못 한 공고 bands (only when there is data); the right-aligned closing sentence; the footer legend above a double rule.

Ledger columns are fixed-width so every band aligns: 번호 3.6rem (centred), 회사 11rem, 근무지 7rem, 점수 6.2rem (right), 판정 4.6rem (centred), 마감 7.4rem; 포지션 and 비고 take the remainder. Header rows stick to the top under the safe-area inset.

**The Narrow Record Rule.** At ≤720px tables stop being tables. Headers are visually hidden (still read by assistive tech); each posting row becomes a four-column grid record — row number down the left, then company / score / seal, position beside the seal, deadline and location, reason full-width. Application rows become a three-column record: number, company / state, role / date, memo full-width; 직접 확인 rows the same: number, channel / result, method / date, memo full-width (판정 못 한 공고: company / found-at, position, reason). The title block stacks and the issue list left-aligns; the attachment drops its indent to a single column. Never ship a horizontally scrolling ledger.

## Elevation & Depth

The system is flat. Depth is conveyed only by rule weight and cell shading: 1px `rule` frames around each band and the 결재란, 1px `rule-2` hairlines inside, 3px double `rule` lines opening and closing the document, `cell` shading for header rows, `cell-2` for unfolded attachments. There are no drop shadows.

The seal's inner ring (`box-shadow: inset 0 0 0 2px paper, inset 0 0 0 3px seal`) is not elevation; it draws the double ring of a physical 인장 and belongs to the seal alone.

### Named Rules
**The Rule-Not-Shadow Rule.** Separation is a line, a double line or a shaded cell. If something seems to need lift, it needs a rule.

## Shapes

Square everywhere: zero radius on tables, cells, input, box marks and the blue stamp. The single round form is the 지원 권장 seal (50%), tilted per row between roughly −13° and −5° so a column of seals reads as hand-stamped. Border vocabulary: solid 1px for frames and box marks, 1.5px for the blue stamp, 2px for the seal, dashed 1px for provisional things (확인 필요 stamp, empty state, demo notice), dotted 1px for attachment leaders.

## Components

### 판정 Stamps (signature)
Four verdict marks in the fixed 판정 cell, each weaker than the one above.
- **지원 권장 seal:** 2.9rem circle, 2px `seal` border plus an inset paper gap and 1px inner ring, `seal` text "지원 / 권장" in Myeongjo 800 .9rem on two lines, rotated by the per-row `--r`, opacity .9.
- **지원 고려 stamp:** 2.6rem square, 1.5px `blue` border, `blue` Myeongjo 700 .78rem "지원 / 고려", not rotated.
- **보류:** no frame; `ink-3` text .82rem, +0.08em.
- **확인 필요:** dashed 1px `ink-3` frame, `ink-2` text .78rem — visibly provisional.
- **Motion:** only the seal moves. With `prefers-reduced-motion: no-preference` it presses into place: from scale 1.28 / opacity .55 to scale 1 / opacity .9 over .5s `cubic-bezier(.16, 1, .3, 1)`, staggered 45ms per row (capped at row 12). It is visible from the first frame (`both` fill). The legend seal is static.

### 결재란 Count Ledger (navigation)
A bordered box: a 2.4rem vertical 판정 title cell (Myeongjo, vertical-rl, `cell` shade) then auto-fit cells of min 128px. Each cell is a header (`cell`, .8rem label plus a small range line in `ink-3`) over a value (numeral 1.3rem + small 건). Cells for bands are anchor links to their band; 지원 권장 count is `seal`, 지원 고려 count is `blue`. The 마감 7일 이내 cell is a toggle button (`aria-pressed`): pressed inverts its header to `ink` on `paper`. Hover shades the header `blue-soft`. The 지원 기록 cell shows 진행 중 / 전체; the 직접 확인 cell shows 다시 볼 곳 / 전체 and jumps to that band.

### Band Sections and Ledger Table
Each verdict band is a Myeongjo headline with inline range and live count, then a table in a 1px `rule` frame. Header row: `cell` shade, label type, 1px `rule` bottom. Body cells: `rule-2` hairlines right and bottom, top-aligned. Company is weight 600; position links are `ink` with a `rule-2` underline that turns `blue` on hover. Empty bands are omitted; search hides bands with no matching rows and updates their counts.

### Box Marks (신규, 주의, D-n)
Inline ink boxes: 1px `ink` border, 0 .3em padding, no fill, no radius.
- **신규** under the row number (.75rem, 600, +0.08em) for postings first seen since the previous issue.
- **주의** replaces a leading ⚠ in a reason (.78rem, 600, +0.06em); glyph warnings are never rendered.
- **D-n deadline:** 마감 within 7 days shows "MM.DD · D-n" boxed at weight 700; past deadlines are `ink-3` struck through; 상시 and — are plain.

### 붙임 Attachment Row (signature)
Folded by default; a small underlined `blue` text button 항목별 점수 / 접기 in the score cell toggles it (`aria-expanded`). The row spans all columns on `cell-2`, indented to the 회사 column behind a 1px `rule` left line. It opens with "붙임 n. 항목별 점수 (1–5)" in Myeongjo, then leader rows — label (`ink-2`, .85rem), a flexible 1px dotted `ink-3` leader, bold value — for 업무 / 필수 / 우대 / 방향 / 신호·가점 (signed). Beside it, .82rem meta: 상한 notes, the judgment file path in code, 처음 찾은 날.

### 조회 Query Field (input)
Label 조회 in spaced `ink-2`; the input has no box, only a 1px `rule` underline, transparent background, `blue` caret, `ink-3` placeholder "회사, 포지션, 근거로 찾기", width min(28rem, 100%). A polite live count reads 전체 n건 or 조건에 맞는 공고 n건. When nothing matches, a dashed `rule-2` empty box explains how to clear the filter.

### 지원 기록 Applications Band
Same band and table grammar. State cell is weight 600: live states in `blue`; 불합격 in `ink-3`, struck through, weight 500. Live states sort first, then newest.

### 직접 확인한 곳 · 판정 못 한 공고 Bands
Same band and table grammar, after 지원 기록. 직접 확인한 곳 lists every channel the scripts cannot read (번호 · 채널 linked to its list page · 결과 7.4rem · 확인일 · 읽는 법 8.4rem · 내용); channels to revisit sort first. A result that needs work (못 봄, 주소 깨짐, 일부만 확인, 확인 기록 없음) is an ink box mark at weight 700; a check older than 7 days shows its date struck in `ink-3` with 다시 확인 below. 판정 못 한 공고 lists postings seen but not judged (번호 · 회사 · 포지션 · 찾은 곳 11rem · 사유). No colour: neither band carries a verdict.

### 준비 자료 Link and Page
A posting with a prep file (`modes/prep.md`) gets a small boxed link under its title, and under the role in 지원 기록: 1px `blue` border, `blue` text .78rem, "준비 자료" plus "남은 n" (or "모두 끝냄") in `ink-2`; `blue-soft` fill on hover. It opens `prep/<key>.html`, a separate page generated by `scripts/prep_page.py` from the same tokens and CSS: ← 공고 현황 back link, the same 표제부 (company + "준비 자료", posting link, 작성일 and file name), a 준비 결재란 (더 준비할 것 남은/전체 in `seal` when any remain, 예상 질문, 시험, 경고 신호), a Myeongjo lede, then bands in reading order: 이 회사여야 하는 이유 · 더 준비할 것 · 전형과 시험 · 예상 질문 · 직무가 원하는 것 · 이 팀이 하는 일 · 회사 · 경고 신호 · 역질문 · 출처. Priority marks are ink boxes (높음 1.5px `seal`, 보통 1px `ink-2`, 낮음 plain `ink-3`); finished tasks are struck in `ink-3` and sort last. 내 상태 충족 is `blue`, 없음 `seal`. Revenue rows carry a `blue-soft` bar behind the figure scaled to the largest year; negative operating profit is `seal`; 영업이익률 and 전년 대비 are computed by the script. Every fact carries a small superscript source number linking to the numbered 출처 list. The page never shows a local file path. Below 720px every table stacks into ruled blocks.

### Focus and Links
All focusable elements get a 2px `blue` (`focus`) outline at 2px offset on `:focus-visible`. Links are `blue`, underline 1px at 3px offset, thickening to 2px on hover.

## Do's and Don'ts

### Do:
- **Do** generate every posting report with `scripts/report_html.py`; use `--fragment` for Artifact-style hosts and `--demo` for fictional samples.
- **Do** keep the output one self-contained file: inline CSS and JS, standard library only, working with no host feature and in any agent's hands; the Myeongjo `<link>` is the sole external request.
- **Do** change DESIGN.md and `report_html.py` in the same commit when either one changes.
- **Do** spend colour only by the Colour-as-Law Rule: `seal` for 지원 권장, `blue` for 지원 고려, links, focus and live states.
- **Do** separate with rules: 1px `rule` frames, 1px `rule-2` hairlines, 3px double rules at the document's edges.
- **Do** keep fixed-width ledger columns and tabular numerals so bands align.
- **Do** turn tables into grid records at ≤720px rather than letting them scroll sideways.
- **Do** set every theme value through the tokens so the carbon-copy dark mode stays a pure value swap.
- **Do** keep motion to the seal press, and only under `prefers-reduced-motion: no-preference`.

### Don't:
- **Don't** hand-write report HTML or fork the CSS into another file.
- **Don't** use cards, pills, rounded containers or drop shadows; the only round shape is the 지원 권장 seal.
- **Don't** put red or blue on anything that does not carry its verdict meaning.
- **Don't** render glyph icons or emoji warnings; convert them to ink box marks such as 주의.
- **Don't** set data cells or numbers in Myeongjo.
- **Don't** depend on a host runtime (Artifact APIs, agent-specific features) for the page to work.
