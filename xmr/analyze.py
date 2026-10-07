# -*- coding: utf-8 -*-
"""分析: 组装主播/专辑记录, 按阈值分档排序"""


def build_anchors(cat_albums: list, anchor_full: dict, scores: dict = None) -> tuple:
    """返回 (anchors 记录列表, 分类专辑ID集合, 主播->分类上榜数映射)
    scores: {albumId: {score, votes, matched, url}} 豆瓣评分(可选)"""
    cat_ids = {a["albumId"] for a in cat_albums}
    in_cat = {}
    for a in cat_albums:
        uid = str(a.get("anchorId") or "")
        if uid:
            in_cat[uid] = in_cat.get(uid, 0) + 1

    anchors = []
    for uid, info in anchor_full.items():
        albs = []
        for al in info.get("albums") or []:
            aid = al.get("id")
            row = [aid, al.get("title", ""), al.get("playCount") or 0,
                   al.get("trackCount") or 0, 1 if al.get("isFinished") else 0,
                   1 if aid in cat_ids else 0]
            if scores is not None:
                sc = scores.get(str(aid)) or {}
                row += [sc.get("score"), sc.get("votes")]
            albs.append(row)
        albs.sort(key=lambda x: -x[2])
        total = sum(a[2] for a in albs)
        anchors.append([str(uid), info.get("nickName") or ("主播" + str(uid)),
                        info.get("fansCount", 0), info.get("tracksCount", 0),
                        (info.get("personalSignature") or "").strip(),
                        in_cat.get(str(uid), 0), total, albs])
    anchors.sort(key=lambda x: -x[6])
    return anchors, cat_ids, in_cat


def album_tier(play: float, thresholds: list) -> int:
    """单专辑播放量 -> 档位索引; 未达标返回 -1. thresholds 降序: [3e8,2e8,1e8,5e7]"""
    for i, th in enumerate(thresholds):
        if play >= th:
            return i
    return -1


def host_tier(total: float, thresholds: list) -> int:
    """主播总播放 -> 档位索引; 未达标返回 -1"""
    for i, th in enumerate(thresholds):
        if total >= th:
            return i
    return -1


def stats(anchors: list, host_th: list, album_th: list) -> dict:
    """汇总统计, 供 KPI 展示"""
    n = len(anchors)
    host_counts = [0] * (len(host_th) + 1)   # 各档 + 未达标
    for a in anchors:
        t = host_tier(a[6], host_th)
        host_counts[t if t >= 0 else -1] += 1
    alb_counts = [0] * len(album_th)
    hot_anchors = 0
    total_albums = 0
    for a in anchors:
        total_albums += len(a[7])
        best = -1
        for al in a[7]:
            t = album_tier(al[2], album_th)
            if t >= 0:
                alb_counts[t] += 1
                best = 0
        if best == 0:
            hot_anchors += 1
    host_counts[-1] = n - sum(host_counts[:-1])
    return {
        "anchors": n, "totalAlbums": total_albums, "hotAnchors": hot_anchors,
        "hostTier": host_counts[:-1], "hostBelow": host_counts[-1],
        "albumTier": alb_counts,
    }
