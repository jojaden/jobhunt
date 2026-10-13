#!/usr/bin/env bash
# jobhunt 한 줄 설치: 저장소를 받아(이미 있으면 갱신) scripts/setup.sh 로 스킬 연결과 빌드 환경까지 끝낸다.
#
#   curl -fsSL https://raw.githubusercontent.com/jojaden/jobhunt/main/install.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/jojaden/jobhunt/main/install.sh | bash -s -- --no-skill   (뒤 인자는 setup.sh 로)
#
# 환경 변수
#   JOBHUNT_DIR   설치 폴더 (기본 ~/jobhunt)
#   JOBHUNT_REF   받을 태그·브랜치 (예: v1.0.0, 기본은 기본 브랜치)
#   JOBHUNT_REPO  저장소 주소 (fork 를 쓸 때)
#
# 지원: macOS(Homebrew), Debian/Ubuntu(apt), Windows 는 WSL2 Ubuntu 안에서.
# 이미 설치한 폴더에서 다시 실행하면 git pull 로 도구만 갱신한다. data/ 는 git 이 다루지 않아 그대로 남는다.
set -euo pipefail

REPO="${JOBHUNT_REPO:-https://github.com/jojaden/jobhunt.git}"
DIR="${JOBHUNT_DIR:-$HOME/jobhunt}"
REF="${JOBHUNT_REF:-}"

say() { printf '▶ %s\n' "$*"; }
die() { printf '✗ %s\n' "$*" >&2; exit 1; }

need() {   # need <명령> <apt 패키지>: 없으면 apt 로 설치하거나 설치 방법을 알려 준다
  "$1" --version >/dev/null 2>&1 && return   # macOS 의 /usr/bin/git 은 명령줄 도구가 없으면 실행이 실패한다
  if [ "$OS" = mac ]; then
    die "$1 이 없습니다. 'xcode-select --install' 로 명령줄 도구를 설치한 뒤 다시 실행하세요."
  elif command -v apt-get >/dev/null 2>&1; then
    say "$2 설치 (sudo 암호를 물을 수 있음)"
    sudo apt-get update -qq && sudo apt-get install -y -qq "$2"
  else
    die "$1 이 없습니다. 설치한 뒤 다시 실행하세요 (지원: macOS, Debian/Ubuntu, Windows WSL2)."
  fi
}

is_jobhunt() { grep -q '^name: jobhunt' "$1/SKILL.md" 2>/dev/null; }

changes() {   # changes <갱신 전 커밋>: 버전이 바뀌었으면 그 사이 CHANGELOG.md 에 더해진 줄을 보여 준다
  local old="$1" new ver notes
  new="$(git -C "$DIR" rev-parse HEAD)"
  ver() { git -C "$DIR" describe --tags --always "$1" 2>/dev/null || echo "${1:0:7}"; }
  if [ "$old" = "$new" ]; then
    say "이미 최신: $(ver "$new")"
    return
  fi
  say "갱신: $(ver "$old") → $(ver "$new")"
  notes="$(git -C "$DIR" diff "$old" "$new" -- CHANGELOG.md | grep '^+' | grep -v '^+++' | cut -c2- | grep -v '^[[:space:]]*$' || true)"
  if [ -n "$notes" ]; then
    printf '%s\n' "$notes" | head -40 | sed 's/^/    /'
    echo "  전체 기록: $DIR/CHANGELOG.md  (data/ 이전 항목이 있으면 따라 주세요)"
  else
    echo "  변경 기록에 더해진 항목 없음 (커밋 $(git -C "$DIR" rev-list --count "$old..$new")개)"
  fi
}

main() {
  case "$(uname -s)" in
    Darwin) OS=mac ;;
    Linux) OS=linux ;;
    *) die "macOS·Linux 에서 실행하세요. Windows 는 PowerShell(관리자)에서 'wsl --install -d Ubuntu' 뒤 Ubuntu 터미널에서 이 명령을 다시 실행합니다." ;;
  esac
  if grep -qi microsoft /proc/version 2>/dev/null; then
    case "$DIR" in
      /mnt/*) die "Windows 드라이브($DIR)는 느리고 스킬 링크가 깨질 수 있습니다. JOBHUNT_DIR 을 WSL 홈(~) 아래로 지정하세요." ;;
    esac
  fi

  need git git
  need python3 python3
  python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' || die "Python 3.10 이상이 필요합니다 (지금: $(python3 -V 2>&1))."

  if [ -d "$DIR/.git" ]; then
    is_jobhunt "$DIR" || die "$DIR 는 다른 저장소입니다. JOBHUNT_DIR 로 다른 폴더를 지정하세요."
    say "이미 설치됨: $DIR — 도구만 갱신 (data/ 는 그대로)"
    old="$(git -C "$DIR" rev-parse HEAD)"
    if [ -n "$REF" ]; then
      git -C "$DIR" fetch -q --tags origin
      git -C "$DIR" checkout -q "$REF" || die "$REF 로 바꾸지 못했습니다. $DIR 에서 git status 를 확인하세요."
    fi
    if git -C "$DIR" symbolic-ref -q HEAD >/dev/null; then   # 태그(분리된 HEAD)면 pull 하지 않는다
      git -C "$DIR" pull -q --ff-only || die "git pull 실패 (고친 파일이 있거나 기록이 갈라짐). $DIR 에서 git status 를 확인하세요."
    fi
    changes "$old"
  elif [ -e "$DIR" ] && [ -n "$(ls -A "$DIR" 2>/dev/null)" ]; then
    die "$DIR 에 다른 파일이 있어 건드리지 않았습니다. 비우거나 JOBHUNT_DIR 로 다른 폴더를 지정하세요."
  else
    say "받기: $REPO${REF:+ ($REF)} → $DIR"
    git -c advice.detachedHead=false clone -q ${REF:+--branch "$REF"} "$REPO" "$DIR"
  fi

  say "설정: scripts/setup.sh $*"
  bash "$DIR/scripts/setup.sh" "$@"

  cat <<EOF

✓ 설치 끝: $DIR
  시작: cd $DIR && claude   (Codex 는 codex, 그 밖의 에이전트는 이 폴더에서 열고 "AGENTS.md 를 읽고 시작해줘")
  처음이면 에이전트에게 "처음 설정해줘" 라고 하면 목표·조건을 묻고 data/ 를 함께 채웁니다.
  업데이트: 같은 설치 명령을 다시 실행하거나 cd $DIR && git pull
EOF
}

main "$@"   # 전체를 함수로 감싸 'curl | bash' 가 끝까지 받은 뒤에 실행되게 한다
