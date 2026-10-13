#!/usr/bin/env bash
# 설치: AI 에이전트 스킬 연결 + 빌드 환경(Python 패키지, Playwright Chromium, 폰트 Pretendard·Noto Sans/Serif CJK KR, poppler)
# 사용: bash scripts/setup.sh              전부
#       bash scripts/setup.sh --skill-only 스킬 연결만
#       bash scripts/setup.sh --no-skill   스킬 연결 없이 빌드 환경만
# 스킬 폴더: 설치된 에이전트를 찾아 연결한다 (~/.claude → ~/.claude/skills, ~/.codex → ~/.codex/skills).
#   다른 에이전트·위치는 SKILLS_DIR=경로[:경로…] 로 지정 (예전 이름 CLAUDE_SKILLS_DIR 도 받음).
#   스킬을 읽지 않는 에이전트는 이 폴더에서 실행하면 AGENTS.md 를 따른다.
# 설치본(uv tool)에서는 jobhunt setup 이 부른다: JOBHUNT_PY(도구의 파이썬)·JOBHUNT_SKILL_SRC(패키지 폴더)를 넘기고,
#   파이썬 패키지는 uv 가 이미 깔았으므로 pip 단계를 건너뛴다.
set -euo pipefail
PY="${JOBHUNT_PY:-python3}"
if [ -n "${JOBHUNT_SKILL_SRC:-}" ]; then
  SRC="$JOBHUNT_SKILL_SRC"
else
  cd "$(dirname "$0")/.."
  SRC="$(pwd -P)"
fi

SKILL=1; ENV=1
for a in "$@"; do
  case "$a" in
    --skill-only) ENV=0 ;;
    --no-skill) SKILL=0 ;;
    *) echo "알 수 없는 옵션: $a"; exit 2 ;;
  esac
done

skill_name() { sed -n 's/^name:[[:space:]]*//p' "$1/SKILL.md" 2>/dev/null | head -1; }
is_installed_copy() { case "$1" in */tools/jobhunt/lib/*/site-packages/jobhunt) return 0 ;; esac; return 1; }   # uv tool 설치본

plugin_installed() {   # 이 에이전트에 jobhunt 플러그인이 (사용자 범위로) 깔려 있나 — 그러면 플러그인이 스킬을 띄운다
  case "$1" in
    "$HOME/.claude/skills")
      "$PY" -c 'import json,sys; d=json.load(open(sys.argv[1])).get("plugins", {}); sys.exit(not any(e.get("scope") == "user" for k, v in d.items() if k.startswith("jobhunt@") for e in v))' \
        "$HOME/.claude/plugins/installed_plugins.json" 2>/dev/null ;;
    "$HOME/.codex/skills") grep -q '^\[plugins\."jobhunt@' "$HOME/.codex/config.toml" 2>/dev/null ;;
    *) return 1 ;;
  esac
}

link_skill() {
  # 스킬 폴더(저장소 또는 설치된 패키지 폴더)를 그대로 연결한다. 복사하지 않으므로 업데이트가 스킬에 바로 반영된다.
  local repo name dir="$1" dest target
  repo="$SRC"
  name="$(skill_name "$SRC")"
  dest="$dir/$name"
  if plugin_installed "$dir"; then
    # 같은 스킬이 두 번 보이지 않게 링크는 만들지 않고, 예전에 이 설치가 만든 링크는 걷어 낸다
    target="$(cd "$dest" 2>/dev/null && pwd -P || true)"
    if [ -L "$dest" ] && { [ "$target" = "$repo" ] || is_installed_copy "$target"; }; then
      rm "$dest"
      echo "  jobhunt 플러그인이 있어 $dest 링크를 뺐습니다"
    else
      echo "  jobhunt 플러그인이 있어 $dir 에는 연결하지 않습니다"
    fi
    return
  fi
  mkdir -p "$dir"
  if [ -L "$dest" ]; then
    target="$(cd "$dest" 2>/dev/null && pwd -P || true)"
    if [ "$target" = "$repo" ]; then
      echo "  이미 연결됨: $dest"
    elif [ -z "$target" ] || [ ! -f "$target/SKILL.md" ] || { [ "$(skill_name "$target")" = "$name" ] && is_installed_copy "$target"; }; then
      # 사라진 곳, 예전 git 설치(옮겨 둔 뒤 SKILL.md 가 없음), 예전 설치본(uv 도구 폴더)이면 새 위치로 바꾼다
      local old; old="$(readlink "$dest")"
      ln -sfn "$repo" "$dest"
      echo "  다시 연결함: $dest → $repo (예전: $old)"
    elif [ "$(skill_name "$target")" = "$name" ]; then
      # 살아 있는 다른 사본(개발용 저장소 clone 등)은 사용자가 고른 것이라 그대로 둔다
      echo "  $dest 가 다른 jobhunt 사본($target)을 가리켜 그대로 둡니다. 이 설치로 바꾸려면: rm \"$dest\" 후 다시 실행"
    else
      echo "  $dest 가 다른 스킬($(readlink "$dest"))을 가리킵니다. 바꾸려면: rm \"$dest\" 후 다시 실행"
    fi
  elif [ -e "$dest" ]; then
    echo "  $dest 에 폴더/파일이 이미 있어 건드리지 않았습니다. 옮긴 뒤 다시 실행하세요."
  else
    ln -s "$repo" "$dest"
    echo "  연결함: $dest → $repo"
  fi
}

skill_dirs() {
  local dirs="${SKILLS_DIR:-${CLAUDE_SKILLS_DIR:-}}"
  if [ -n "$dirs" ]; then
    echo "$dirs" | tr ':' '\n'
    return
  fi
  [ -d "$HOME/.claude" ] && echo "$HOME/.claude/skills"   # Claude Code
  [ -d "$HOME/.codex" ] && echo "$HOME/.codex/skills"     # Codex
  return 0
}

if [ "$SKILL" = 1 ]; then
  echo "▶ AI 에이전트 스킬 연결"
  found=0
  while IFS= read -r d; do
    [ -n "$d" ] || continue
    found=1
    link_skill "$d"
  done < <(skill_dirs)
  if [ "$found" = 0 ]; then
    echo "  스킬 폴더를 찾지 못했습니다. 에이전트를 이 폴더에서 실행하면 AGENTS.md 를 따릅니다 (스킬로 쓰려면 SKILLS_DIR=경로)."
  fi
fi
if [ -z "${JOBHUNT_SKILL_SRC:-}" ] && git rev-parse --git-dir >/dev/null 2>&1 && [ "$(git config --get core.hooksPath || true)" != ".githooks" ]; then
  echo "▶ (선택) 이 저장소에 커밋한다면 개인 자료 검사 훅을 켜세요: git config core.hooksPath .githooks"
fi
[ "$ENV" = 1 ] || exit 0

if grep -qi microsoft /proc/version 2>/dev/null; then   # Windows WSL2
  case "${JOBHUNT_HOME:-$SRC}" in
    /mnt/*) echo "  ⚠ Windows 드라이브(/mnt/...)에 있습니다. 느리고 링크가 깨질 수 있어 WSL 홈(~)에 clone 하는 걸 권합니다." ;;
  esac
fi
if [ -z "${JOBHUNT_PY:-}" ]; then   # 저장소: 시스템 파이썬에 pip 로 설치 (설치본은 uv 가 이미 깔았다)
  if [[ "$(uname)" != "Darwin" ]] && ! python3 -m pip --version >/dev/null 2>&1; then
    echo "▶ pip"
    sudo apt-get update -qq && sudo apt-get install -y -qq python3-pip
  fi
  PIP_FLAGS=""
  python3 -m pip install --help 2>/dev/null | grep -q -- "--break-system-packages" && PIP_FLAGS="--break-system-packages"
  echo "▶ Python 패키지"
  python3 -m pip install -q $PIP_FLAGS -r requirements.txt
fi

echo "▶ Chromium"
if [ -n "${PLAYWRIGHT_BROWSERS_PATH:-}" ] && ls "$PLAYWRIGHT_BROWSERS_PATH" 2>/dev/null | grep -q chromium; then
  echo "  이미 설치됨 ($PLAYWRIGHT_BROWSERS_PATH)"
else
  "$PY" -m playwright install chromium
fi
if [[ "$(uname)" != "Darwin" ]]; then   # 새로 설치한 Ubuntu(WSL2 포함)에는 Chromium 실행용 시스템 라이브러리가 없다
  "$PY" -m playwright install-deps chromium   # 내부에서 sudo apt-get 으로 설치 (암호를 물을 수 있음)
fi

echo "▶ 폰트 · poppler"
if [[ "$(uname)" == "Darwin" ]]; then
  command -v brew >/dev/null || { echo "  Homebrew 가 필요합니다: https://brew.sh"; exit 1; }
  fc-list 2>/dev/null | grep -qi "Noto Sans CJK KR" || ls ~/Library/Fonts 2>/dev/null | grep -qi "NotoSansCJK" \
    || brew install --cask font-noto-sans-cjk-kr
  fc-list 2>/dev/null | grep -qi "Noto Serif CJK KR" || ls ~/Library/Fonts 2>/dev/null | grep -qi "NotoSerifCJK" \
    || brew install --cask font-noto-serif-cjk-kr
  fc-list 2>/dev/null | grep -qi "Pretendard" || ls ~/Library/Fonts 2>/dev/null | grep -qi "Pretendard" \
    || brew install --cask font-pretendard
  command -v pdftoppm >/dev/null || brew install poppler
else
  if ! fc-list | grep -qi "Noto Sans CJK"; then   # fonts-noto-cjk 에 Serif CJK 도 들어 있다
    sudo apt-get update -qq && sudo apt-get install -y -qq fonts-noto-cjk
  fi
  if ! fc-list | grep -qi "Pretendard"; then
    dir=~/.local/share/fonts/pretendard; mkdir -p "$dir"
    for w in Regular Medium SemiBold Bold ExtraBold; do
      curl -fsSL -o "$dir/Pretendard-$w.otf" "https://cdn.jsdelivr.net/npm/pretendard@1.3.9/dist/public/static/Pretendard-$w.otf"
    done
    fc-cache -f "$dir" >/dev/null
  fi
  command -v pdftoppm >/dev/null || sudo apt-get install -y -qq poppler-utils
fi

echo "▶ 확인"
"$PY" - <<'PY'
import yaml, pdfplumber, pdf2image
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    p.chromium.launch().close()
print("  준비 완료")
PY
