# -*- coding: utf-8 -*-
"""alive.py: 같은 사이트는 차례로, 다른 사이트는 동시에 확인하고, 결과는 넣은 순서대로 주소마다 하나."""
import threading
import time
import unittest

import support  # noqa: F401  (scripts/ 를 import 경로에 넣는다)

import alive as A


class Run(unittest.TestCase):
    def test_lanes(self):
        lock, now, peak, calls = threading.Lock(), {}, {}, []

        def check(url):
            site = url.split("/")[2]
            with lock:
                calls.append(url)
                now[site] = now.get(site, 0) + 1
                peak[site] = max(peak.get(site, 0), now[site])
                peak["all"] = max(peak.get("all", 0), sum(now.values()))
            time.sleep(0.05)
            with lock:
                now[site] -= 1
            return url.endswith("1"), site

        urls = ["https://a.example/1", "https://a.example/2", "https://b.example/1", "https://a.example/1"]
        saved, A.check = A.check, check
        try:
            res = A.run([dict(url=u, company="", title="", where="pipeline") for u in urls])
        finally:
            A.check = saved
        self.assertEqual([(r["url"], r["alive"]) for r in res],
                         [("https://a.example/1", True), ("https://a.example/2", False), ("https://b.example/1", True)])
        self.assertEqual(sorted(calls), sorted(urls[:3]))              # 같은 주소는 한 번만
        self.assertEqual((peak["a.example"], peak["b.example"]), (1, 1))   # 같은 사이트는 하나씩
        self.assertEqual(peak["all"], 2)                                # 사이트끼리는 동시에


if __name__ == "__main__":
    unittest.main()
