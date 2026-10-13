#!/usr/bin/env bash
# 주간 스캔: scripts/weekly.py 로 옮겼다 (설치본에서는 jobhunt weekly). 예전에 cron/launchd 에 등록한 이 경로도 그대로 돈다.
# 사용: bash scripts/weekly.sh [--since YYYY-MM-DD]   (기본: 7일 전)
exec python3 "$(dirname "$0")/weekly.py" "$@"
