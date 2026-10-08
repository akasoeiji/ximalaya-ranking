# -*- coding: utf-8 -*-
"""主入口: 多分类 爬取 -> 分析 -> 生成报告
用法:
  python -m xmr.run_all                        # 按默认配置完整跑
  python -m xmr.run_all --pages 3 --max-anchors 30
  python -m xmr.run_all --skip-crawl           # 仅用缓存重新生成报告
  python -m xmr.run_all --skip-scores          # 跳过豆瓣评分抓取(仍使用已有缓存)
"""
import argparse
import datetime
import json
import os
import shutil
import sys

from . import config as cfgmod
from . import crawler, analyze, report, douban


def _score_cache_path(cfg: dict) -> str:
    """豆瓣评分缓存路径(默认相对项目根目录)"""
    name = cfg["douban"]["cache"]
    if os.path.isabs(name):
        return name
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, name)


def _load_scores(sp: str) -> dict:
    if os.path.exists(sp):
        with open(sp, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _process_category(cat: dict, cfg: dict, out_dir: str, scores: dict, args) -> tuple:
    """处理单个分类: 爬取 -> 评分 -> 分析 -> 报告, 返回 (summary, scores)"""
    cat_out = os.path.join(out_dir, cat["key"])
    cache_dir = os.path.join(cat_out, "cache")
    os.makedirs(cache_dir, exist_ok=True)
    t0 = datetime.datetime.now()
    print(f"\n===== 分类: {cat['name']} ({cat['key']}) =====")
    print(f"categoryId={cat['categoryId']} metadata={cat['metadataValues']} "
          f"pages={cat['pages']} pageSize={cat['pageSize']}")

    # ---------- 1. 爬取 ----------
    if args.skip_crawl:
        cat_albums = json.load(open(os.path.join(cache_dir, "category_albums.json"), encoding="utf-8"))
        anchor_full = json.load(open(os.path.join(cache_dir, "anchor_full.json"), encoding="utf-8"))
        print(f"[skip-crawl] 载入缓存: 专辑 {len(cat_albums)}, 主播 {len(anchor_full)}")
    else:
        cat_albums = crawler.fetch_category(cat, cfg["crawl"])
        print(f"[crawl] 分类页抓取完成: 专辑 {len(cat_albums)}")
        anchor_ids = sorted({str(a["anchorId"]) for a in cat_albums if a.get("anchorId")})
        print(f"[crawl] 去重主播 {len(anchor_ids)} 位")
        extra = [str(u) for u in (cat.get("extraAnchors") or []) if str(u) not in anchor_ids]
        if extra:
            print(f"[crawl] 追加指定主播 {len(extra)} 位: {', '.join(extra)}")
        anchor_ids = extra + anchor_ids
        anchor_full = crawler.fetch_anchors(anchor_ids, cfg, cache_dir=cache_dir)
        json.dump(cat_albums, open(os.path.join(cache_dir, "category_albums.json"), "w", encoding="utf-8"), ensure_ascii=False)
        json.dump({"pages": cat["pages"], "pageSize": cat["pageSize"]},
                  open(os.path.join(cache_dir, "run_config.json"), "w", encoding="utf-8"))

    # ---------- 1.5 豆瓣评分 ----------
    sp = _score_cache_path(cfg)
    if cfg["douban"]["enabled"] and not args.skip_scores and not args.skip_crawl:
        scores = douban.backfill(anchor_full, sp,
                                 min_play=cfg["douban"]["minPlay"],
                                 delay=cfg["douban"]["delay"],
                                 limit=cfg["douban"]["limit"],
                                 max_seconds=cfg["douban"].get("maxSeconds", 600))
    elif scores:
        print(f"[scores] 使用评分缓存 {len(scores)} 条")

    # ---------- 2. 分析 ----------
    anchors, _, _ = analyze.build_anchors(cat_albums, anchor_full, scores or None)
    stats_d = analyze.stats(anchors, cfg["tiers"]["host"], cfg["tiers"]["album"])
    print(f"[analyze] 主播 {stats_d['anchors']} | 专辑 {stats_d['totalAlbums']} | "
          f"爆款主播 {stats_d['hotAnchors']} | 主播分档 {stats_d['hostTier']} | 未达标 {stats_d['hostBelow']}")
    print(f"[analyze] 专辑分档 {stats_d['albumTier']}")

    # ---------- 3. 报告 ----------
    web_path = os.path.join(cat_out, "index.html")
    report.write_web(anchors, len(cat_albums), stats_d, cfg["tiers"]["host"],
                     cfg["tiers"]["album"], cat["pages"], web_path,
                     cat_name=cat["name"], cat_key=cat["key"])
    report.write_csvs(anchors, cat_albums, cfg["tiers"]["host"], cfg["tiers"]["album"], cat_out)
    # 附带一份带中文名的网页副本
    shutil.copyfile(web_path, os.path.join(cat_out, "喜马拉雅主播专辑播放量分档.html"))

    summary = {
        "key": cat["key"],
        "name": cat["name"],
        "categoryId": cat["categoryId"],
        "metadataValues": cat["metadataValues"],
        "url": f"https://www.ximalaya.com/category/{cat['key']}/",
        "generatedAt": datetime.datetime.now().isoformat(timespec="seconds"),
        "pages": cat["pages"],
        "pageSize": cat["pageSize"],
        "anchors": stats_d["anchors"],
        "albumsInCategory": len(cat_albums),
        "albumsTotal": stats_d["totalAlbums"],
        "hotAnchors": stats_d["hotAnchors"],
        "hostTier": stats_d["hostTier"],
        "hostBelow": stats_d["hostBelow"],
        "albumTierExact": stats_d["albumTier"],
    }
    json.dump(summary, open(os.path.join(cat_out, "summary.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    cost = (datetime.datetime.now() - t0).total_seconds()
    print(f"[done] {cat['name']} 耗时 {cost:.0f}s, 输出 {os.path.abspath(cat_out)}")
    return summary, scores


def main():
    ap = argparse.ArgumentParser(description="喜马拉雅主播/专辑播放量分档爬虫与报告生成(多分类)")
    ap.add_argument("--out", default=None, help="输出目录(默认 output/ 或 XMR_OUT)")
    ap.add_argument("--pages", type=int, default=None, help="分类分页数(默认50, 作用于所有分类)")
    ap.add_argument("--max-anchors", type=int, default=None, help="限制每个分类主播抓取数, 0=全部")
    ap.add_argument("--skip-crawl", action="store_true", help="跳过爬取, 使用缓存生成报告")
    ap.add_argument("--skip-scores", action="store_true", help="跳过豆瓣评分抓取(仍使用已有缓存)")
    ap.add_argument("--config", default=None, help="config.json 路径")
    args = ap.parse_args()

    cfg = cfgmod.load(args.config)
    if args.pages is not None:
        for c in cfg["categories"]:
            c["pages"] = args.pages
    if args.max_anchors is not None:
        cfg["crawl"]["maxAnchors"] = args.max_anchors
    out_dir = args.out or cfg["output"]["dir"]
    os.makedirs(out_dir, exist_ok=True)

    t0 = datetime.datetime.now()
    print(f"=== 喜马拉雅播放量分档任务开始 {t0:%Y-%m-%d %H:%M:%S} ===")
    print(f"分类数: {len(cfg['categories'])} | maxAnchors={cfg['crawl']['maxAnchors']} | out={out_dir}")

    sp = _score_cache_path(cfg)
    scores = _load_scores(sp)
    if scores:
        print(f"[scores] 载入评分缓存 {len(scores)} 条: {sp}")

    summaries = []
    for cat in cfg["categories"]:
        summary, scores = _process_category(cat, cfg, out_dir, scores, args)
        summaries.append(summary)

    # ---------- 总索引 + 汇总 ----------
    report.write_index(summaries, out_dir)
    total = {
        "generatedAt": datetime.datetime.now().isoformat(timespec="seconds"),
        "categories": summaries,
    }
    json.dump(total, open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    cost = (datetime.datetime.now() - t0).total_seconds()
    print(f"\n=== 完成, 耗时 {cost:.0f}s, 共 {len(summaries)} 个分类 ===")
    print(f"总索引: {os.path.abspath(os.path.join(out_dir, 'index.html'))}")
    for s in summaries:
        print(f"  - {s['name']}: {os.path.abspath(os.path.join(out_dir, s['key'], 'index.html'))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
