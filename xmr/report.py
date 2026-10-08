# -*- coding: utf-8 -*-
"""报告生成: 双视图分档 HTML(数据内嵌/懒渲染) + 三份 CSV + 多分类总索引页"""
import copy
import csv
import datetime
import json
import os

TIER_COLORS = ["#e03131", "#d9480f", "#e8590c", "#1971c2", "#0c8599", "#6741d9", "#2f9e44"]


def _fmt(n):
    if n is None:
        return "-"
    if n >= 1e8:
        v = n / 1e8
        return f"{v:.2f}亿".replace(".00亿", "亿")
    if n >= 1e4:
        return f"{n/1e4:,.0f}万"
    return f"{n:,}"


def _esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _tier_names(thresholds):
    return [_fmt(t) + "档" for t in thresholds]
