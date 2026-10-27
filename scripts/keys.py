# -*- coding: utf-8 -*-
"""API 키: 공공데이터포털(국민연금 가입 사업장)과 OpenDART. 키는 사용자마다 자기 것을 쓰고 저장소에는 넣지 않는다.

  jobhunt keys                 키가 있는지, 있으면 한 번 불러 써지는지. 없는 키는 발급 방법을 보여 준다
  jobhunt keys set <이름>       키 넣기 (data_go_kr 또는 dart). 터미널에서 화면에 보이지 않게 입력, 파이프로도 받는다

환경 변수(JOBHUNT_DATA_GO_KR_KEY, JOBHUNT_DART_KEY)가 설정 파일(~/.config/jobhunt/keys, 권한 600)보다 먼저다.
키는 화면이나 오류 메시지에 찍지 않는다.
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys
import urllib.parse
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jobkit as K  # noqa: E402

FILE = os.path.join(os.path.dirname(K.HOME_FILE), "keys")
KEYS: Dict[str, Dict[str, Any]] = {
    "data_go_kr": dict(
        title="공공데이터포털 (국민연금 가입자 수 · 평균연봉 추정 · 입사/퇴사)", env="JOBHUNT_DATA_GO_KR_KEY",
        guide=["1. https://www.data.go.kr 회원가입 · 로그인",
               "2. https://www.data.go.kr/data/3046071/openapi.do ('국민연금공단_국민연금 가입 사업장 내역') 에서 [활용신청]",
               "   활용 목적은 '개인 구직용 회사 조사' 정도로 적으면 된다. 자동 승인, 하루 1만 건, 무료",
               "3. 마이페이지 → 개인 API 인증키 → 일반 인증키 (Decoding) 복사",
               "   발급 직후에는 '등록되지 않은 키'로 나올 수 있다. 1~2시간 뒤 jobhunt keys 로 다시 확인"]),
    "dart": dict(
        title="OpenDART (대표자 · 사업자등록번호 · 매출/영업이익 · 감사보고서)", env="JOBHUNT_DART_KEY",
        guide=["1. https://opendart.fss.or.kr → [인증키 신청] → 사용자 구분 '개인'",
               "2. 이메일 · 비밀번호 · 사용 환경 · 사용 용도를 적고 이메일 인증. 개인은 바로 발급, 하루 2만 건, 무료",
               "3. 이메일 인증을 마친 뒤 로그인 → [인증키 신청/관리] → [오픈API 이용현황] 의 API Key (40자리) 복사",
               "   ([인증키 관리] 화면에는 키가 나오지 않는다)"]),
}


def _read_file() -> Dict[str, str]:
    try:
        with open(FILE, encoding="utf-8") as f:
            pairs = (ln.strip().split("=", 1) for ln in f if "=" in ln and not ln.lstrip().startswith("#"))
            return {k.strip(): v.strip() for k, v in pairs}
    except FileNotFoundError:
        return {}


def get(name: str) -> Optional[str]:
    """키 값. 환경 변수 → 설정 파일. 공공데이터포털의 인코딩된 키(%2B …)를 넣었어도 원래 값으로 푼다."""
    v = os.environ.get(KEYS[name]["env"]) or _read_file().get(name)
    if not v:
        return None
    return urllib.parse.unquote(v) if name == "data_go_kr" and "%" in v else v


def where(name: str) -> str:
    return "환경 변수 " + KEYS[name]["env"] if os.environ.get(KEYS[name]["env"]) else FILE


def save(name: str, value: str) -> None:
    """설정 파일에 한 줄로 저장 (폴더 700, 파일 600). 다른 키 줄은 그대로 둔다."""
    keys = _read_file()
    keys[name] = value
    os.makedirs(os.path.dirname(FILE), mode=0o700, exist_ok=True)
    fd = os.open(FILE + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("# jobhunt API 키 (jobhunt keys set). 저장소나 다른 사람에게 올리지 마세요\n")
        f.writelines(f"{k}={v}\n" for k, v in keys.items())
    os.replace(FILE + ".tmp", FILE)
    os.chmod(FILE, 0o600)


def ping(name: str, key: str) -> None:
    """한 번 불러 본다. 실패하면 RuntimeError (메시지에 키는 없다)."""
    if name == "data_go_kr":
        import nps
        nps.ping(key)
    else:
        import dart
        dart.ping(key)


def missing() -> List[str]:
    return [n for n in KEYS if not get(n)]


def guide(name: str) -> str:
    return "\n".join([f"[{KEYS[name]['title']}] 발급 방법"] + [f"  {ln}" for ln in KEYS[name]["guide"]]
                     + [f"  4. 터미널에서 jobhunt keys set {name} (키를 대화창에 붙여 넣지 마세요)"])


def status() -> int:
    bad = 0
    for name, k in KEYS.items():
        key = get(name)
        if not key:
            print(f"✗ {k['title']}: 키 없음\n{guide(name)}\n")
            bad += 1
            continue
        try:
            ping(name, key)
            print(f"✓ {k['title']}: 쓸 수 있음 ({where(name)})")
        except (RuntimeError, K.ShapeError) as e:
            print(f"✗ {k['title']}: {e} ({where(name)})")
            bad += 1
        except OSError as e:
            print(f"? {k['title']}: 확인하지 못함, 연결 실패 ({type(e).__name__})")
            bad += 1
    if bad:
        print("키 없이도 jobhunt company 는 원티드 회사 정보로 동작합니다.")
    return 1 if bad else 0


def set_key(name: str) -> int:
    if sys.stdin.isatty():
        print(guide(name), file=sys.stderr)
        value = getpass.getpass(f"{name} 키 (입력은 화면에 보이지 않음): ")
    else:
        value = sys.stdin.readline()
    value = value.strip()
    if not value:
        print("키를 받지 못했습니다. 아무것도 바꾸지 않았습니다.", file=sys.stderr)
        return 1
    save(name, value)
    print(f"저장함: {FILE} (권한 600)")
    if os.environ.get(KEYS[name]["env"]):
        print(f"주의: 환경 변수 {KEYS[name]['env']} 가 설정 파일보다 먼저 쓰입니다.")
    try:
        ping(name, get(name) or "")
        print("확인: 이 키로 불러 써짐")
    except (RuntimeError, K.ShapeError) as e:
        print(f"확인 실패: {e}")
        return 1
    except OSError as e:
        print(f"확인하지 못함, 연결 실패 ({type(e).__name__}). 저장은 됐습니다.")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="API 키 (공공데이터포털 · OpenDART) 상태 확인과 저장")
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("set", help="키 넣기 (화면에 보이지 않게 입력, 파이프로도 받음)")
    s.add_argument("name", choices=list(KEYS))
    a = ap.parse_args(argv)
    return set_key(a.name) if a.cmd == "set" else status()


if __name__ == "__main__":
    sys.exit(main())
