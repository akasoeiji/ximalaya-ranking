# -*- coding: utf-8 -*-
"""爬虫: ①分类分页(专辑+主播) ②每位主播个人主页全部公开专辑"""
import json
import os
import random
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

from .http_client import get_json

CATEGORY_API = ("https://www.ximalaya.com/revision/category/v2/albums"
                "?pageSize={pageSize}&sort={sort}&categoryId={categoryId}"
                "&metadataValues={metadata}&pageNum={page}")
ANCHOR_PUB_API = ("https://www.ximalaya.com/revision/user/pub"
                  "?page={page}&pageSize=100&keyWord=&uid={uid}")
ANCHOR_BASIC_API = "https://www.ximalaya.com/revision/user/basic?uid={uid}"


def fetch_category(cfg: dict, log=print) -> list:
    """抓取分类前 N 个分页, 返回去重后的专辑列表"""
    c = cfg["category"]
    base = CATEGORY_API.format(pageSize=c["pageSize"], sort=c["sort"],
                               categoryId=c["categoryId"],
                               metadata=urllib.parse.quote(c["metadataValues"], safe=""),
                               page="{page}")
    albums, empty_streak = {}, 0
    total_pages = c["pages"]
    for p in range(1, total_pages + 1):
        d = get_json(base.format(page=p), timeout=cfg["crawl"]["timeout"],
                     retries=cfg["crawl"]["retries"])
        items = (d or {}).get("data", {}).get("albums", []) if d else []
        if not items:
            empty_streak += 1
            log(f"[category] page {p}: 空 (连续 {empty_streak})")
            if empty_streak >= 3:
                log("[category] 连续空页, 提前结束")
                break
            time.sleep(0.8)
            continue
        empty_streak = 0
        for a in items:
            aid = a.get("albumId")
            if aid and aid not in albums:
                albums[aid] = a
        log(f"[category] page {p}: +{len(items)}, 累计去重 {len(albums)}")
        time.sleep(0.4 + random.random() * 0.4)
    return list(albums.values())


def _fetch_one_anchor(uid: str, cfg: dict) -> dict:
    """单个主播: 基本信息 + 全部公开专辑(分页)"""
    t, r = cfg["crawl"]["timeout"], cfg["crawl"]["retries"]
    basic = get_json(ANCHOR_BASIC_API.format(uid=uid), timeout=t, retries=r) or {}
    b = basic.get("data") or {}
    albums, page, total = [], 1, None
    while True:
        d = get_json(ANCHOR_PUB_API.format(page=page, uid=uid), timeout=t, retries=r)
        if not d:
            break
        data = d.get("data") or {}
        lst = data.get("albumList") or []
        if total is None:
            total = data.get("totalCount") or 0
        albums.extend(lst)
        if not lst or len(albums) >= total or page >= 40:
            break
        page += 1
        time.sleep(0.25 + random.random() * 0.25)
    return {
        "nickName": b.get("nickName", ""),
        "fansCount": b.get("fansCount", 0),
        "albumsCount": b.get("albumsCount", 0),
        "tracksCount": b.get("tracksCount", 0),
        "personalSignature": b.get("personalSignature", ""),
        "albums": albums,
    }


def fetch_anchors(anchor_ids: list, cfg: dict, cache_dir: str = None, log=print) -> dict:
    """并发抓取所有主播, 支持基于缓存的断点续抓"""
    result = {}
    cache_file = None
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, "anchor_full.json")
        if os.path.exists(cache_file):
            with open(cache_file, encoding="utf-8") as f:
                result = json.load(f)
            log(f"[anchors] 载入缓存 {len(result)} 位, 续抓 {len(anchor_ids) - len(result)} 位")

    todo = [u for u in anchor_ids if u not in result]
    if cfg["crawl"]["maxAnchors"] > 0:
        todo = todo[: cfg["crawl"]["maxAnchors"]]
    log(f"[anchors] 待抓取 {len(todo)} 位 (并发 {cfg['crawl']['workers']})")

    done = 0
    with ThreadPoolExecutor(max_workers=cfg["crawl"]["workers"]) as ex:
        futs = {ex.submit(_fetch_one_anchor, u, cfg): u for u in todo}
        for fut in as_completed(futs):
            uid = futs[fut]
            try:
                result[str(uid)] = fut.result()
            except Exception as e:  # 单个失败不影响整体
                log(f"[anchors] uid={uid} 失败: {e}")
            done += 1
            if done % 25 == 0:
                log(f"[anchors] 进度 {done}/{len(todo)}")
                if cache_file:
                    json.dump(result, open(cache_file, "w", encoding="utf-8"), ensure_ascii=False)
    if cache_file:
        json.dump(result, open(cache_file, "w", encoding="utf-8"), ensure_ascii=False)
    return result
