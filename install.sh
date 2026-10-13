#!/usr/bin/env bash
# jobhunt 한 줄 설치: uv 로 jobhunt 명령을 설치하고(이미 있으면 갱신) jobhunt setup 으로 개인 자료 폴더 · 스킬 연결 · 빌드 환경까지 끝낸다.
#
#   curl -fsSL https://raw.githubusercontent.com/jojaden/jobhunt/main/install.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/jojaden/jobhunt/main/install.sh | bash -s -- --no-skill   (뒤 인자는 jobhunt setup 으로)
#
# 환경 변수
#   JOBHUNT_HOME  개인 자료 폴더 (기본 ~/jobhunt, 예전 이름 JOBHUNT_DIR 도 받음). 기본 위치가 아니면 셸 설정에도 export 해야 jobhunt 가 찾는다
#   JOBHUNT_REF   받을 태그·브랜치·커밋 (예: v1.2.0, 기본은 기본 브랜치)
#   JOBHUNT_REPO  저장소 주소 (fork 를 쓸 때)
#
# 지원: macOS(Homebrew), Debian/Ubuntu(apt), Windows 는 WSL2 Ubuntu 안에서.
# 예전 git 설치(~/jobhunt 가 저장소)에서 다시 실행하면: data/ 는 그 자리에 두고, git 이 관리하던 코드·지침 파일과 .git 을
# ~/jobhunt/.old-repo/ 로 옮겨 둔다 (지우지 않는다). 그 뒤로 도구는 uv 가 관리하고, 이 폴더에는 개인 자료만 남는다.
set -euo pipefail

REPO="${JOBHUNT_REPO:-https://github.com/jojaden/jobhunt.git}"
HOME_DIR="${JOBHUNT_HOME:-${JOBHUNT_DIR:-$HOME/jobhunt}}"
case "$HOME_DIR" in /*) ;; *) HOME_DIR="$PWD/$HOME_DIR" ;; esac   # cron 등 다른 위치에서 돌아도 같은 폴더를 가리키게
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

is_jobhunt() {   # 전환이 중간에 멈췄으면 SKILL.md 는 이미 .old-repo/ 에 있을 수 있다
  grep -q '^name: jobhunt' "$1/SKILL.md" 2>/dev/null || grep -q '^name: jobhunt' "$1/.old-repo/SKILL.md" 2>/dev/null
}

install_uv() {
  command -v uv >/dev/null 2>&1 && return
  if [ ! -x "$HOME/.local/bin/uv" ]; then
    say "uv 설치 (파이썬 도구 관리자, https://docs.astral.sh/uv)"
    curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null
  fi
  export PATH="$HOME/.local/bin:$PATH"
  command -v uv >/dev/null 2>&1 || die "uv 를 찾지 못했습니다. 새 터미널에서 다시 실행하세요."
}

move_old_repo() {   # 예전 git 설치: data/ 와 git 이 모르는 파일은 두고, git 이 관리하던 파일과 .git 을 .old-repo/ 로 옮긴다
  # 중간에 멈췄다가 다시 돌려도 이어서 옮긴다 (이미 옮긴 파일은 건너뜀)
  local dest="$HOME_DIR/.old-repo" edited f d
  [ -e "$dest/.git" ] && die "$HOME_DIR/.git 과 $dest/.git 이 둘 다 있습니다. 어느 쪽이 맞는지 확인한 뒤 다시 실행하세요."
  edited="$(git -C "$HOME_DIR" status --porcelain --untracked-files=no -- . ':!data' | grep -cE '^(M|.M)' || true)"
  say "예전 git 설치를 옮겨 둠: 코드·지침 → $dest (data/ 는 그대로)"
  mkdir -p "$dest"
  while IFS= read -r -d '' f; do
    case "$f" in data/*) continue ;; esac
    [ -e "$HOME_DIR/$f" ] || [ -L "$HOME_DIR/$f" ] || continue
    mkdir -p "$dest/$(dirname "$f")"
    mv "$HOME_DIR/$f" "$dest/$f"
  done < <(git -C "$HOME_DIR" ls-files -z)
  # 옮긴 파일이 있던 폴더만 정리한다 (사용자가 만든 빈 폴더 · .venv 는 건드리지 않음)
  while IFS= read -r d; do
    rm -rf "$HOME_DIR/$d/__pycache__"
    rmdir "$HOME_DIR/$d" 2>/dev/null || true
  done < <(git -C "$HOME_DIR" ls-files | grep -v '^data/' | awk -F/ '{p=""; for (i=1;i<NF;i++) {p=p (i>1?"/":"") $i; print p}}' | sort -ru)
  mv "$HOME_DIR/.git" "$dest/.git"
  [ "$edited" = 0 ] || echo "  고쳐 둔 파일 ${edited}개도 $dest 에 그대로 있습니다."
}

keep_schedule() {   # cron·launchd 가 예전 scripts/weekly.sh 를 부르면, 그 자리에 jobhunt weekly 로 이어 주는 파일을 둔다
  local old="$HOME_DIR/scripts/weekly.sh" found="" pat
  pat="$(basename "$HOME_DIR").*scripts/weekly\.sh"     # …/jobhunt/scripts/weekly.sh, cd ~/jobhunt && bash scripts/weekly.sh
  crontab -l 2>/dev/null | grep -qE "$pat" && found="crontab"
  grep -lsE "$pat" "$HOME"/Library/LaunchAgents/*.plist >/dev/null 2>&1 && found="${found:+$found · }launchd"
  grep -lsE "$pat" "$HOME"/.config/systemd/user/*.service >/dev/null 2>&1 && found="${found:+$found · }systemd"
  [ -n "$found" ] || return 0
  mkdir -p "$HOME_DIR/scripts"
  cat > "$old" <<EOF
#!/usr/bin/env bash
# 예전 git 설치 때 $found 에 등록한 경로를 이어 주는 파일 (install.sh 가 만듦). 예약을 '$(uv tool dir --bin)/jobhunt weekly' 로 바꾸면 지워도 된다.
export JOBHUNT_HOME="\${JOBHUNT_HOME:-$HOME_DIR}"
exec "$(uv tool dir --bin)/jobhunt" weekly "\$@"
EOF
  chmod +x "$old"
  echo "  $found 이 예전 주간 실행 경로를 부릅니다. 그대로 돌도록 $old 가 jobhunt weekly 를 부르게 해 두었습니다."
}

main() {
  case "$(uname -s)" in
    Darwin) OS=mac ;;
    Linux) OS=linux ;;
    *) die "macOS·Linux 에서 실행하세요. Windows 는 PowerShell(관리자)에서 'wsl --install -d Ubuntu' 뒤 Ubuntu 터미널에서 이 명령을 다시 실행합니다." ;;
  esac
  if grep -qi microsoft /proc/version 2>/dev/null; then
    case "$HOME_DIR" in
      /mnt/*) die "Windows 드라이브($HOME_DIR)는 느리고 스킬 링크가 깨질 수 있습니다. JOBHUNT_HOME 을 WSL 홈(~) 아래로 지정하세요." ;;
    esac
  fi

  old_repo=0
  if [ -e "$HOME_DIR/.git" ]; then
    is_jobhunt "$HOME_DIR" || die "$HOME_DIR 는 다른 저장소입니다. JOBHUNT_HOME 으로 다른 폴더를 지정하세요."
    old_repo=1
  elif [ -e "$HOME_DIR" ] && [ ! -d "$HOME_DIR/data" ] && [ -n "$(ls -A "$HOME_DIR" 2>/dev/null)" ]; then
    die "$HOME_DIR 에 다른 파일이 있어 건드리지 않았습니다. 비우거나 JOBHUNT_HOME 으로 다른 폴더를 지정하세요."
  fi

  need curl curl
  need git git          # uv 가 git 저장소에서 설치할 때 쓴다
  install_uv

  old=""   # '1.1.0 (464475d)' — 버전과 커밋
  if [ "$old_repo" = 1 ]; then
    old="$(git -C "$HOME_DIR" describe --tags --abbrev=0 2>/dev/null | sed 's/^v//') ($(git -C "$HOME_DIR" rev-parse --short=7 HEAD))"
  elif [ -d "$HOME_DIR/.old-repo/.git" ] && [ ! -x "$(uv tool dir --bin)/jobhunt" ]; then   # 전환 뒤 설치가 끝나지 않았던 경우
    old="$(git -C "$HOME_DIR/.old-repo" describe --tags --abbrev=0 2>/dev/null | sed 's/^v//') (옮겨 둔 설치)"
  elif [ -x "$(uv tool dir --bin)/jobhunt" ]; then
    old="$("$(uv tool dir --bin)/jobhunt" --version 2>/dev/null | cut -d' ' -f2- || true)"
  fi

  say "jobhunt 설치: $REPO${REF:+ ($REF)}"
  uv tool install -q --force --reinstall-package jobhunt --python 3.12 "git+$REPO${REF:+@$REF}" \
    || die "uv tool install 실패. 위 메시지를 확인하세요 (data/ 는 건드리지 않았습니다)."
  export PATH="$(uv tool dir --bin):$PATH"
  command -v jobhunt >/dev/null 2>&1 || die "jobhunt 명령을 찾지 못했습니다 ($(uv tool dir --bin))."

  [ "$old_repo" = 1 ] && move_old_repo
  [ -d "$HOME_DIR/.old-repo" ] && keep_schedule       # 전환이 앞서 멈췄던 경우에도 예약은 이어 둔다

  new="$(jobhunt --version | cut -d' ' -f2-)"       # 바뀐 점은 setup 전에 보여 준다 (setup 이 실패해도 data/ 이전 안내는 남게)
  if [ -n "$old" ] && [ "$old" = "$new" ]; then
    say "이미 최신: $new"
  elif [ -n "$old" ]; then   # 버전 번호가 같아도 커밋이 다르면 "다음 버전" 에 항목이 더해졌을 수 있다
    say "갱신: $old → $new"
    notes="$(jobhunt changes "${old%% *}" | grep -v '^[[:space:]]*$' || true)"
    if printf '%s\n' "$notes" | grep -q '^- '; then
      printf '%s\n' "$notes" | head -40 | sed 's/^/    /'
      echo "  data/ 이전 항목이 있으면 따라 주세요 (전체: jobhunt changes ${old%% *})"
    fi
  fi

  say "설정: jobhunt setup $*"
  JOBHUNT_HOME="$HOME_DIR" jobhunt setup "$@"
  uv tool update-shell -q 2>/dev/null || true   # 새 터미널에서도 jobhunt 가 보이게 PATH 를 셸 설정에 넣는다 (이미 있으면 그대로)

  cat <<EOF

✓ 설치 끝 (jobhunt $new). 개인 자료: $HOME_DIR/data
  시작: cd $HOME_DIR && claude   (Codex 는 codex, 그 밖의 에이전트는 이 폴더에서 열고 "AGENTS.md 를 읽고 시작해줘")
  처음이면 에이전트에게 "처음 설정해줘" 라고 하면 목표·조건을 묻고 data/ 를 함께 채웁니다.
  업데이트: 같은 설치 명령을 다시 실행
EOF
  if [ "$HOME_DIR" != "$HOME/jobhunt" ]; then
    echo "  개인 자료 폴더가 기본 위치가 아닙니다. 셸 설정(~/.zshrc 또는 ~/.bashrc)에 넣으세요: export JOBHUNT_HOME=\"$HOME_DIR\""
  fi
}

main "$@"   # 전체를 함수로 감싸 'curl | bash' 가 끝까지 받은 뒤에 실행되게 한다
