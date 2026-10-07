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
        "extraAnchors": [],         # 额外指定主播UID(不在分类页也会被抓取), 如 [79758517]
    },
    "tiers": {
        # 档位阈值(升序生效), 单位: 次播放
        "host": [300000000, 200000000, 100000000, 50000000,
                 30000000, 10000000, 5000000],   # 主播总播放分档
        "album": [300000000, 200000000, 100000000, 50000000,
                  30000000, 10000000, 5000000],  # 单专辑播放分档
    },
    "douban": {
        "enabled": True,           # 是否抓取豆瓣评分
        "minPlay": 100000000,      # 仅给播放量≥此值的专辑抓评分(1亿)
        "delay": 1.5,              # 请求间隔(秒), 豆瓣风控需低频
        "limit": 0,                # 本次最多新查条数, 0=不限制
        "cache": "douban_scores.json",  # 评分缓存文件(相对输出目录; 建议入git供CI复用)
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
    extra = os.environ.get("XMR_EXTRA_ANCHORS")
    if extra:
        w["extraAnchors"] = [u.strip() for u in extra.split(",") if u.strip()]
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
