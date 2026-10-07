# -*- coding: utf-8 -*-
"""豆瓣评分补全: 标题清洗 -> suggest 匹配 -> 详情页提取评分/人数
仅处理播放量 >= minPlay 的达标专辑, 结果增量缓存(可直接入 git 供 CI 复用)"""
import json
import os
import random
import re
import time
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
SUGGEST_API = "https://book.douban.com/j/subject_suggest?q={q}"
RATE_RE = re.compile(r'v:average">\s*([\d.]+)\s*<')
VOTES_RE = re.compile(r'v:votes">(\d+)')
TITLE_RE = re.compile(r'<h1>\s*<span[^>]*>([^<]+)</span>')
SPLIT_RE = re.compile(r'[｜|/／:：,，。;；!！?？\-—·\s]+')


def clean_title(title: str) -> str:
    """提取书名核心: 去【】括号块, 取第一个分段(书名通常在最前)"""
    t = re.sub(r'【[^】]*】', ' ', title)
    t = re.sub(r'（[^）]*）|\([^)]*\)', ' ', t)
    parts = [p.strip() for p in SPLIT_RE.split(t) if p.strip()]
    if not parts:
        return title.strip()[:20]
    first = parts[0]
    if len(first) < 2:
        first = max(parts, key=len)
    return first[:20]


_BLOCK = {"count": 0, "until": 0.0}   # 全局风控冷却


def _cool(sec: float):
    import datetime
    _BLOCK["until"] = time.time() + sec
    print(f"[douban] 风控冷却 {sec:.0f}s 至 {datetime.datetime.now():%H:%M:%S}")


def _get(url: str, retries: int = 3, timeout: int = 20, log=print) -> str:
    """带随机bid cookie与403退避的GET; None=风控拒绝(勿缓存), ""=确认无内容"""
    if time.time() < _BLOCK["until"]:
        time.sleep(_BLOCK["until"] - time.time())
    delay = 2.0
    for i in range(retries):
        bid = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=11))
        req = urllib.request.Request(url, headers={
            "User-Agent": UA, "Referer": "https://book.douban.com/",
            "Cookie": f"bid={bid}", "Accept-Language": "zh-CN,zh;q=0.9"})
        try:
            r = urllib.request.urlopen(req, timeout=timeout)
            _BLOCK["count"] = 0
            return r.read().decode("utf-8", "ignore")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return ""
            if e.code in (403, 429):
                _BLOCK["count"] += 1
                if _BLOCK["count"] >= 3:
                    _cool(45.0)
                    _BLOCK["count"] = 0
                time.sleep(delay)
                delay *= 2.2
            else:
                raise
        except Exception:
            time.sleep(delay)
            delay *= 2.2
    return None


class Blocked(Exception):
    """豆瓣风控拒绝, 本条不缓存待下轮重试"""


def fetch_score(title: str, log=print) -> dict:
    """查一本书: 返回 {score, votes, matched, url} 或 {empty:True}; 风控时抛 Blocked"""
    name = clean_title(title)
    if len(name) < 2:
        return {"empty": True}
    body = _get(SUGGEST_API.format(q=urllib.parse.quote(name)))
    if body is None:
        raise Blocked("suggest 403")
    if not body:
        return {"empty": True}
    try:
        cands = json.loads(body)
    except Exception:
        return {"empty": True}
    if not cands:
        # 偶发限流返回空数组, 二次确认
        time.sleep(3)
        body = _get(SUGGEST_API.format(q=urllib.parse.quote(name)))
        if body is None:
            raise Blocked("suggest 403(retry)")
        try:
            cands = json.loads(body) if body else []
        except Exception:
            cands = []
        if not cands:
            return {"empty": True}
    # 候选匹配: 标题完全相等 > 包含清洗名 > 第一条
    key = name.replace(" ", "")
    best = cands[0]
    for c in cands[:5]:
        if (c.get("title") or "").replace(" ", "") == key:
            best = c
            break
    else:
        for c in cands[:5]:
            if key in (c.get("title") or "").replace(" ", ""):
                best = c
                break
    url = best.get("url") or ""
    if not url:
        return {"empty": True}
    time.sleep(random.uniform(1.0, 1.8))
    page = _get(url)
    if page is None:
        raise Blocked("detail 403")
    if not page:
        return {"matched": best.get("title", ""), "url": url}
    m, v = RATE_RE.search(page), VOTES_RE.search(page)
    if not m:
        # 页面正常但无评分模块(新书/评分人数不足): 确定性无分
        return {"empty": True, "matched": best.get("title", ""), "url": url}
    return {
        "score": float(m.group(1)),
        "votes": int(v.group(1)) if v else None,
        "matched": best.get("title", ""),
        "url": url,
    }


def _done(entry) -> bool:
    """已获得评分, 或确认豆瓣无此书"""
    return bool(entry and (entry.get("score") is not None or entry.get("empty")))


def backfill(anchor_full: dict, cache_path: str, min_play: int = 100000000,
             delay: float = 2.5, limit: int = 0, log=print) -> dict:
    """增量补全评分: 已有评分/明确无结果的跳过; 风控条目保留待下轮"""
    cache = {}
    if os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as f:
            cache = json.load(f)
    # 收集需查询的专辑(播放量降序, 头部优先)
    albs = []
    for uid, info in anchor_full.items():
        for a in info.get("albums") or []:
            if (a.get("playCount") or 0) >= min_play:
                albs.append((a["playCount"], a["id"], a.get("title", "")))
    albs.sort(reverse=True)
    if limit:
        albs = albs[:limit]
    todo = [x for x in albs if not _done(cache.get(str(x[1])))]
    log(f"[douban] 目标 {len(albs)} 张(≥{min_play/1e8:.0f}亿), 已完成 {len(albs)-len(todo)}, 待查 {len(todo)}")
    done = ok = consec_skip = 0
    for i, (pc, aid, title) in enumerate(todo):
        try:
            r = fetch_score(title, log=log)
        except Blocked as e:
            log(f"[douban] {aid} 风控跳过({e}), 留待下轮")
            consec_skip += 1
            if consec_skip >= 8:
                log("[douban] 连续风控过多, 提前结束本轮(已完成部分已缓存)")
                break
            continue
        except Exception as e:
            log(f"[douban] {aid} 异常 {str(e)[:40]}")
            continue
        consec_skip = 0
        cache[str(aid)] = r
        done += 1
        if r.get("score"):
            ok += 1
            log(f"[douban] {i+1}/{len(todo)} {title[:22]} -> {r['score']}分({r.get('votes')}人) 匹配:{r.get('matched','')[:14]}")
        if done % 25 == 0:
            _save(cache_path, cache)
        time.sleep(delay + random.random())
    _save(cache_path, cache)
    got = sum(1 for v in cache.values() if v.get("score") is not None)
    log(f"[douban] 本轮查询 {done} 命中 {ok} | 缓存总量 {len(cache)}, 有评分 {got}")
    return cache


def _save(path: str, cache: dict):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)
    os.replace(tmp, path)
