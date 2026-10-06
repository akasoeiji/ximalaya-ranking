# -*- coding: utf-8 -*-
"""主入口: 爬取 -> 分析 -> 生成报告
用法:
  python -m xmr.run_all                        # 按默认配置完整跑
  python -m xmr.run_all --pages 3 --max-anchors 30
  python -m xmr.run_all --skip-crawl           # 仅用缓存重新生成报告
"""
import argparse
import datetime
import json
import os
import shutil
import sys

from . import config as cfgmod
from . import crawler, analyze, report


def main():
    ap = argparse.ArgumentParser(description="喜马拉雅主播/专辑播放量分档爬虫与报告生成")
    ap.add_argument("--out", default=None, help="输出目录(默认 output/ 或 XMR_OUT)")
    ap.add_argument("--pages", type=int, default=None, help="分类分页数(默认50)")
    ap.add_argument("--max-anchors", type=int, default=None, help="限制主播抓取数, 0=全部")
    ap.add_argument("--skip-crawl", action="store_true", help="跳过爬取, 使用缓存生成报告")
    ap.add_argument("--config", default=None, help="config.json 路径")
    args = ap.parse_args()

    cfg = cfgmod.load(args.config)
    if args.pages is not None:
        cfg["category"]["pages"] = args.pages
    if args.max_anchors is not None:
        cfg["crawl"]["maxAnchors"] = args.max_anchors
    out_dir = args.out or cfg["output"]["dir"]
    cache_dir = os.path.join(out_dir, "cache")
    os.makedirs(cache_dir, exist_ok=True)
    t0 = datetime.datetime.now()
    print(f"=== 喜马拉雅播放量分档任务开始 {t0:%Y-%m-%d %H:%M:%S} ===")
    print(f"配置: pages={cfg['category']['pages']} pageSize={cfg['category']['pageSize']} "
          f"maxAnchors={cfg['crawl']['maxAnchors']} out={out_dir}")

    # ---------- 1. 爬取 ----------
    if args.skip_crawl:
        cat_albums = json.load(open(os.path.join(cache_dir, "category_albums.json"), encoding="utf-8"))
        anchor_full = json.load(open(os.path.join(cache_dir, "anchor_full.json"), encoding="utf-8"))
        rc = os.path.join(cache_dir, "run_config.json")
        if os.path.exists(rc):
            saved = json.load(open(rc, encoding="utf-8"))
            cfg["category"]["pages"] = saved.get("pages", cfg["category"]["pages"])
            cfg["category"]["pageSize"] = saved.get("pageSize", cfg["category"]["pageSize"])
        print(f"[skip-crawl] 载入缓存: 专辑 {len(cat_albums)}, 主播 {len(anchor_full)}")
    else:
        cat_albums = crawler.fetch_category(cfg)
        print(f"[crawl] 分类页抓取完成: 专辑 {len(cat_albums)}")
        anchor_ids = sorted({str(a["anchorId"]) for a in cat_albums if a.get("anchorId")})
        print(f"[crawl] 去重主播 {len(anchor_ids)} 位")
        anchor_full = crawler.fetch_anchors(anchor_ids, cfg, cache_dir=cache_dir)
        json.dump(cat_albums, open(os.path.join(cache_dir, "category_albums.json"), "w", encoding="utf-8"), ensure_ascii=False)
        json.dump({"pages": cfg["category"]["pages"], "pageSize": cfg["category"]["pageSize"]},
                  open(os.path.join(cache_dir, "run_config.json"), "w", encoding="utf-8"))

    # ---------- 2. 分析 ----------
    anchors, _, _ = analyze.build_anchors(cat_albums, anchor_full)
    stats_d = analyze.stats(anchors, cfg["tiers"]["host"], cfg["tiers"]["album"])
    print(f"[analyze] 主播 {stats_d['anchors']} | 专辑 {stats_d['totalAlbums']} | "
          f"爆款主播 {stats_d['hotAnchors']} | 主播分档(精确) {stats_d['hostTier']} | 未达标 {stats_d['hostBelow']}")
    print(f"[analyze] 专辑分档(各档精确) {stats_d['albumTier']}")

    # ---------- 3. 报告 ----------
    web_path = os.path.join(out_dir, "index.html")
    report.write_web(anchors, len(cat_albums), stats_d, cfg["tiers"]["host"],
                     cfg["tiers"]["album"], cfg["category"]["pages"], web_path)
    csvs = report.write_csvs(anchors, cat_albums, cfg["tiers"]["host"], cfg["tiers"]["album"], out_dir)
    # 附带一份带中文名的网页副本
    shutil.copyfile(web_path, os.path.join(out_dir, "喜马拉雅主播专辑播放量分档.html"))

    summary = {
        "generatedAt": datetime.datetime.now().isoformat(timespec="seconds"),
        "pages": cfg["category"]["pages"],
        "pageSize": cfg["category"]["pageSize"],
        "anchors": stats_d["anchors"],
        "albumsInCategory": len(cat_albums),
        "albumsTotal": stats_d["totalAlbums"],
        "hotAnchors": stats_d["hotAnchors"],
        "hostTier": stats_d["hostTier"],
        "hostBelow": stats_d["hostBelow"],
        "albumTierExact": stats_d["albumTier"],
    }
    json.dump(summary, open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    cost = (datetime.datetime.now() - t0).total_seconds()
    print(f"=== 完成, 耗时 {cost:.0f}s ===")
    print(f"输出: {os.path.abspath(web_path)}")
    for p in csvs:
        print(f"  - {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
