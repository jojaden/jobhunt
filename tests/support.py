# -*- coding: utf-8 -*-
"""테스트 공통: scripts/ 를 import 경로에 넣고, 사용자 data/ 대신 임시 폴더를 쓰고, 고정 응답으로 http_get 을 바꾼다.

이 모듈을 import 하는 순간 jobkit.P 가 임시 경로로 바뀐다. 테스트는 사용자 data/ 를 읽지도 쓰지도 않는다.
"""
import atexit
import json
import os
import shutil
import sys
import tempfile
from contextlib import contextmanager

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))

import jobkit as K  # noqa: E402
import providers  # noqa: E402

FIXTURES = os.path.join(HERE, "fixtures")
TMP = tempfile.mkdtemp(prefix="jobhunt-test-")
atexit.register(shutil.rmtree, TMP, True)
for _k, _v in K.P.items():                     # 같은 dict 를 고친다 (공급원 모듈이 `from jobkit import P` 로 들고 있다)
    K.P[_k] = os.path.join(TMP, os.path.relpath(_v, K.DATA))
for _v in K.P.values():
    os.makedirs(os.path.dirname(_v), exist_ok=True)
shutil.copy(os.path.join(FIXTURES, "sources.yaml"), K.P["sources"])
# API 키와 DART 고유번호 캐시도 사용자 것 대신 임시 폴더 (키는 테스트가 넣을 때만 있다)
import dart  # noqa: E402
import keys  # noqa: E402
keys.FILE = os.path.join(TMP, "config", "keys")
dart.CACHE = os.path.join(TMP, "cache", "dart-corpcode.xml")
for _n in keys.KEYS.values():
    os.environ.pop(_n["env"], None)


def load_fixture(*parts):
    with open(os.path.join(FIXTURES, *parts), encoding="utf-8") as f:
        return json.load(f)


def body_of(r: dict) -> str:
    """고정 응답 → 본문 글. json: 객체, next_data: Next.js 페이지에 넣을 객체, html: 글 그대로."""
    if "json" in r:
        return json.dumps(r["json"], ensure_ascii=False)
    if "next_data" in r:
        return ('<html><head><title>채용</title></head><body><script id="__NEXT_DATA__" type="application/json">'
                + json.dumps(r["next_data"], ensure_ascii=False) + "</script></body></html>")
    return r.get("html", "")


class Replay:
    """주소 → 고정 응답. 목록이면 차례로 돌려주고 마지막 것은 계속 쓴다. 고정 응답이 없는 요청은 실패시킨다(네트워크 없음)."""

    def __init__(self, responses: dict):
        self.queues = {u: list(r) if isinstance(r, list) else [r] for u, r in responses.items()}
        self.calls = []

    def __call__(self, url, accept="application/json", delay=1.0, timeout=20, headers=None, data=None):
        self.calls.append((url, data))
        q = self.queues.get(url)
        if not q:
            raise AssertionError(f"고정 응답 없는 요청: {url}")
        r = q.pop(0) if len(q) > 1 else q[0]
        return r.get("status", 200), body_of(r)


@contextmanager
def replay(responses: dict):
    """jobkit 과 공급원 모듈의 http_get 을 Replay 로 바꾼다 (모듈마다 `from jobkit import http_get` 로 이름을 들고 있다)."""
    fake = Replay(responses)
    mods = [K] + [m for m in providers.ALL if hasattr(m, "http_get")]
    saved = [(m, m.http_get) for m in mods]
    for m in mods:
        m.http_get = fake
    providers.jsonapi._specs.cache_clear()
    K._ALIAS = None
    try:
        yield fake
    finally:
        for m, f in saved:
            m.http_get = f
