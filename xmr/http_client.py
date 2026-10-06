# -*- coding: utf-8 -*-
"""HTTP 客户端: urllib 封装, 带重试/退避/限速, 零第三方依赖"""
import json
import random
import time
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def get_json(url: str, referer: str = "https://www.ximalaya.com/",
             timeout: int = 20, retries: int = 5, ok_ret: int = 200):
    """GET 请求并解析 JSON, 失败重试(指数退避+抖动), 全部失败返回 None"""
    headers = {"User-Agent": UA, "Referer": referer, "Accept": "application/json"}
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.loads(r.read().decode("utf-8"))
            if d.get("ret") == ok_ret:
                return d
            time.sleep(1.0 * (i + 1) + random.random())
        except Exception:
            time.sleep(1.5 * (i + 1) + random.random())
    return None
