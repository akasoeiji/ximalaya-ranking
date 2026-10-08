# -*- coding: utf-8 -*-
"""喜马拉雅主播/专辑播放量分档 - 配置加载(支持 config.json + 环境变量覆盖)"""
import json
import os

# 单个分类的默认配置
_CATEGORY_DEFAULTS = {
    "key": "a3_b5162",            # 分类 URL 标识(a{categoryId}_b{metadataValueId})
    "name": "有声书-男频",        # 分类展示名
    "categoryId": 3,              # 3 = 有声书
    "metadataValues": "男频",     # 子频道
    "sort": 1,                    # 1=最多播放
    "pages": 50,                  # 抓取分页数
    "pageSize": 40,               # 每页条数(40*50=2000, 服务端深度上限约2016)
    "extraAnchors": [],           # 该分类额外指定主播UID(不在分类页也会被抓取)
}

DEFAULTS = {
    "categories": [dict(_CATEGORY_DEFAULTS)],
    "crawl": {
        "maxAnchors": 0,            # 限制每个分类抓取主播数, 0=全部
        "workers": 6,               # 并发线程
        "timeout": 20,              # 请求超时(秒)
        "retries": 5,               # 重试次数
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
        "maxSeconds": 600,         # 单分类单轮时间预算(秒), 0=不限; CI建议≤600
        "cache": "douban_scores.json",  # 评分缓存文件(相对项目根目录; 建议入git供CI复用)
    },
    "output": {"dir": "output"},
}


def _normalize_categories(cfg: dict) -> list:
    """把旧版单分类配置(category)规范化为多分类列表, 并补齐默认字段"""
    old = cfg.pop("category", None)
    raw = cfg.get("categories")
    if old is not None:
        raw = [old]
    elif not raw:
        raw = [dict(_CATEGORY_DEFAULTS)]
    legacy_extra = (cfg.get("crawl") or {}).pop("extraAnchors", None)
    out = []
    for c in raw:
        cat = dict(_CATEGORY_DEFAULTS)
        cat.update(c or {})
        if "extraAnchors" not in (c or {}) and legacy_extra:
            cat["extraAnchors"] = list(legacy_extra)
        out.append(cat)
    return out


def _apply_env(cfg: dict) -> dict:
    pages = os.environ.get("XMR_PAGES")
    page_size = os.environ.get("XMR_PAGE_SIZE")
    cat_id = os.environ.get("XMR_CATEGORY_ID")
    metadata = os.environ.get("XMR_METADATA")
    sort = os.environ.get("XMR_SORT")
    for c in cfg["categories"]:
        if pages:
            c["pages"] = int(pages)
        if page_size:
            c["pageSize"] = int(page_size)
        # 单分类场景下允许环境变量切换分类(向后兼容); 多分类时忽略避免混淆
        if len(cfg["categories"]) == 1:
            if cat_id:
                c["categoryId"] = int(cat_id)
            if metadata:
                c["metadataValues"] = metadata
            if sort:
                c["sort"] = int(sort)
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
            if k == "categories":
                cfg["categories"] = v
            elif k in cfg and isinstance(v, dict) and isinstance(cfg[k], dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
    cfg["categories"] = _normalize_categories(cfg)
    return _apply_env(cfg)
