#!/usr/bin/env bash
# jobhunt 업데이트: 개인 자료 폴더 · 스킬 연결 · 빌드 환경은 그대로 두고 도구만 새 버전으로 바꾼다 (설치 절차를 다시 밟지 않는다).
#
#   jobhunt update                  설치본(uv tool): 설치할 때 쓴 저장소에서 다시 받아 설치 (받은 폴더에서 설치했으면 그 폴더를 git pull)
#   python3 scripts/cli.py update   저장소 폴더(git clone)에서 쓸 때: main 브랜치를 git pull, 의존성이 바뀌었으면 setup.sh --no-skill
#
# 환경 변수
#   JOBHUNT_REF   받을 태그·브랜치·커밋 (설치본만, 기본은 기본 브랜치)
#   JOBHUNT_REPO  받을 저장소 (설치본만, 기본은 설치할 때 쓴 주소)
#
# 설치본은 이 파일까지 새 버전으로 바뀌므로, 전체를 main 함수로 감싸 다 읽은 뒤에 실행한다.
set -euo pipefail

say() { printf '▶ %s\n' "$*"; }
die() { printf '✗ %s\n' "$*" >&2; exit 1; }

HERE="$(cd "$(dirname "$0")" && pwd -P)"

changelog() {   # changelog <저장소> <예전 커밋> <새 커밋>: 그 사이 CHANGELOG 에 더해진 줄
  git -C "$1" diff "$2" "$3" -- CHANGELOG.md | sed -n 's/^+\(- \)/\1/p'
}

show_changes() {   # show_changes <예전 버전> <새 버전> <바뀐 점 목록>
  if [ "$1" = "$2" ]; then
    say "이미 최신: $2"
    return
  fi
  say "갱신: $1 → $2"
  if printf '%s\n' "$3" | grep -q '^- '; then
    printf '%s\n' "$3" | grep '^- ' | head -40 | sed 's/^/    /'
    echo "  data/ 이전 항목이 있으면 따라 주세요."
  fi
}

update_installed() {
  command -v uv >/dev/null 2>&1 || export PATH="$HOME/.local/bin:$PATH"
  command -v uv >/dev/null 2>&1 || die "uv 를 찾지 못했습니다. 설치 명령(install.sh)으로 다시 설치하세요."
  local py bin src old new ref="${JOBHUNT_REF:-}"
  # 도구의 가상환경: <도구 폴더>/jobhunt/lib/pythonX.Y/site-packages/jobhunt 에서 네 단계 위 (UV_TOOL_DIR 로 옮긴 설치도 같다)
  local venv; venv="$(cd "$HERE/../../../.." && pwd -P)"
  py="$venv/bin/python" bin="$venv/bin/jobhunt"
  export UV_TOOL_DIR="$(dirname "$venv")"   # 다시 설치도 지금 설치된 도구 폴더에 (UV_TOOL_DIR 를 이번에 주지 않았어도)
  # 설치할 때 받은 곳 (pip 의 direct_url.json): 'vcs <주소>' · 'dir <폴더>' · 'archive <주소>'
  # 파이썬은 -I 로: 실행한 폴더에 있는 파일(copy.py 등)이 표준 모듈을 가리지 않게
  src="$("$py" -I - <<'EOF'
import json
from importlib import metadata
from urllib.parse import urlsplit
from urllib.request import url2pathname
d = json.loads(metadata.distribution("jobhunt").read_text("direct_url.json") or "{}")
kind = "vcs" if "vcs_info" in d else "dir" if "dir_info" in d else "archive"
url = d.get("url", "")
# 받은 폴더는 파일 주소(file:///…/%EB%B0%9B%EC%9D%80%20%ED%8F%B4%EB%8D%94)라 경로로 풀어 둔다
print(kind, url2pathname(urlsplit(url).path) if kind == "dir" and url.startswith("file:") else url)
EOF
)"
  old="$("$bin" --version | cut -d' ' -f2-)"
  case "$src" in
    dir\ /*)
      local dir="${src#dir }"
      [ -d "$dir/.git" ] || die "받은 폴더($dir)가 없거나 git 저장소가 아닙니다. 설치 명령(install.sh)으로 다시 설치하세요."
      say "받은 폴더에서 새 버전 받기: $dir"
      old="$(git -C "$dir" rev-parse HEAD)"   # 받은 폴더 설치는 버전에 커밋이 없어 git 으로 비교한다
      git -C "$dir" pull --ff-only || die "git pull 이 멈췄습니다. $dir 에서 위 메시지를 확인하세요."
      new="$(git -C "$dir" rev-parse HEAD)"
      uv tool install -q --force --reinstall-package jobhunt --python 3.12 "$dir" || die "uv tool install 실패 (data/ 는 건드리지 않았습니다)."
      show_changes "${old:0:7}" "${new:0:7}" "$(changelog "$dir" "$old" "$new")"
      ;;
    vcs\ *)
      local repo="${JOBHUNT_REPO:-${src#vcs }}"
      say "새 버전 받기: $repo${ref:+ ($ref)}"
      uv tool install -q --force --reinstall-package jobhunt --python 3.12 "git+$repo${ref:+@$ref}" \
        || die "uv tool install 실패 (data/ 는 건드리지 않았습니다)."
      new="$("$bin" --version | cut -d' ' -f2-)"
      show_changes "$old" "$new" "$("$bin" changes "${old%% *}")"
      ;;
    *) die "휠 파일로 설치해 받을 곳을 모릅니다 ($src). 설치 명령(install.sh)으로 다시 설치하세요." ;;
  esac
  # 새 버전에 생긴 data/ 뼈대 파일만 더한다 (있는 파일은 건드리지 않음)
  "$py" -I -c "import sys; sys.path.insert(0, sys.argv[1]); import cli, jobkit as K; cli.prepare_home(K.RES, K.ROOT)" "$HERE"
}

update_checkout() {
  local root branch main=main old new   # 릴리스는 main 에 태그로 붙인다
  root="$(dirname "$HERE")"
  branch="$(git -C "$root" symbolic-ref --short HEAD 2>/dev/null || echo "")"
  [ "$branch" = "$main" ] || die "지금 브랜치가 '${branch:-분리된 HEAD}' 입니다. 'git checkout $main' 뒤에 다시 실행하세요 (작업 중인 브랜치는 건드리지 않습니다)."
  old="$(git -C "$root" rev-parse HEAD)"
  say "새 버전 받기: $root ($main)"
  git -C "$root" pull --ff-only || die "git pull 이 멈췄습니다. 위 메시지를 확인하세요 (고친 파일이 겹치면 커밋하거나 git stash 한 뒤 다시)."
  new="$(git -C "$root" rev-parse HEAD)"
  show_changes "${old:0:7}" "${new:0:7}" "$(changelog "$root" "$old" "$new")"
  if [ "$old" != "$new" ] && ! git -C "$root" diff --quiet "$old" "$new" -- requirements.txt scripts/setup.sh; then
    say "의존성이 바뀌어 빌드 환경을 맞춤: bash scripts/setup.sh --no-skill"
    bash "$root/scripts/setup.sh" --no-skill
  fi
}

main() {
  # 설치본은 references/ 를 코드와 같은 폴더에 함께 담는다 (jobkit.RES 와 같은 판별, 도구 폴더 위치와 무관)
  if [ -d "$HERE/references" ]; then
    update_installed
  else
    [ -e "$(dirname "$HERE")/.git" ] || die "설치본도 git 저장소도 아닙니다 ($HERE). 설치 명령(install.sh)으로 설치하세요."
    update_checkout
  fi
  echo "✓ 업데이트 끝. 개인 자료와 스킬 연결은 그대로입니다."
}

main "$@"
