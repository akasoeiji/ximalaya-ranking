# -*- coding: utf-8 -*-
"""喜马拉雅主播/专辑播放量分档 - 配置加载(支持 config.json + 环境变量覆盖)"""
import json
import os

DEFAULTS = {
    "category": {
        "categoryId": 3,            # 3 = 有声书
        "metadataValues": "男频",   # a3_b5162 中的 b5162
        "sort": 1,                  # 1=最多播放
        "pages": 50,                # 抓取分页数
        "pageSize": 40,             # 每页条数(40*50=2000, 服务端深度上限约2016)
    },
    "crawl": {
        "maxAnchors": 0,            # 限制抓取主播数, 0=全部
        "workers": 6,               # 并发线程
        "timeout": 20,              # 请求超时(秒)
        "retries": 5,               # 重试次数
    },
    "tiers": {
        # 档位阈值(升序生效), 单位: 次播放
        "host": [300000000, 200000000, 100000000, 50000000],   # 主播总播放分档
        "album": [300000000, 200000000, 100000000, 50000000],  # 单专辑播放分档
    },
    "output": {"dir": "output"},
}


def _apply_env(cfg: dict) -> dict:
    c = cfg["category"]
    c["pages"] = int(os.environ.get("XMR_PAGES", c["pages"]))
    c["pageSize"] = int(os.environ.get("XMR_PAGE_SIZE", c["pageSize"]))
    c["categoryId"] = int(os.environ.get("XMR_CATEGORY_ID", c["categoryId"]))
    c["metadataValues"] = os.environ.get("XMR_METADATA", c["metadataValues"])
    c["sort"] = int(os.environ.get("XMR_SORT", c["sort"]))
    w = cfg["crawl"]
    w["maxAnchors"] = int(os.environ.get("XMR_MAX_ANCHORS", w["maxAnchors"]))
    w["workers"] = int(os.environ.get("XMR_WORKERS", w["workers"]))
    cfg["output"]["dir"] = os.environ.get("XMR_OUT", cfg["output"]["dir"])
    return cfg


def load(config_path: str = None) -> dict:
    """加载配置: 内置默认 <- config.json <- 环境变量"""
    cfg = json.loads(json.dumps(DEFAULTS))  # deep copy
    path = config_path or os.path.join(os.getcwd(), "config.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            user = json.load(f)
        for k, v in user.items():
            if k in cfg and isinstance(v, dict) and isinstance(cfg[k], dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
    return _apply_env(cfg)
