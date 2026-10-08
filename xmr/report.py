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


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>喜马拉雅 · 主播及专辑播放量分档</title>
<style>
:root{--bg:#f4f6f9;--card:#fff;--line:#e9ecef;--ink:#212529;--sub:#6c757d;--brand:#ff4d4f;--gray:#868e96}
*{box-sizing:border-box} html{scroll-behavior:smooth}
body{margin:0;font-family:"PingFang SC","Hiragino Sans GB","Microsoft YaHei",-apple-system,sans-serif;background:var(--bg);color:var(--ink);font-size:14px}
a{color:inherit}
.wrap{max-width:1180px;margin:0 auto;padding:0 14px 80px}
.hero{background:linear-gradient(130deg,#182848,#27447c 55%,#3b5998);color:#fff;border-radius:0 0 20px 20px;padding:30px 0 24px;margin-bottom:-90px;position:relative;overflow:hidden}
.hero:before{content:"";position:absolute;right:-60px;top:-80px;width:340px;height:340px;border-radius:50%;background:radial-gradient(closest-side,rgba(255,255,255,.10),transparent)}
.hero h1{margin:0 0 6px;font-size:25px}
.hero h1 .em{background:linear-gradient(90deg,#ffd43b,#ff922b);-webkit-background-clip:text;background-clip:text;color:transparent}
.hero .sub{font-size:12.5px;opacity:.78;line-height:1.7}
.kpis{display:grid;grid-template-columns:repeat(8,1fr);gap:9px;margin-top:18px;position:relative;z-index:2}
.kpi{background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.12);border-radius:12px;padding:11px 6px;text-align:center}
.kpi b{display:block;font-size:21px;font-variant-numeric:tabular-nums}
.kpi span{font-size:11px;opacity:.75}
.kpi.hot b{color:#ffd43b}
.ov-card{background:var(--card);border-radius:16px;box-shadow:0 2px 10px rgba(20,40,80,.06);padding:16px 20px 8px;margin-top:110px}
.ov-card h3{margin:0 0 12px;font-size:16px}
.ov{display:grid;grid-template-columns:repeat(auto-fit,minmax(196px,1fr));gap:10px;margin-bottom:12px}
.ov .cell{border-radius:12px;padding:12px 14px;color:#fff}
.ov .cell b{display:block;font-size:24px;font-variant-numeric:tabular-nums}
.ov .cell span{font-size:11.5px;opacity:.85}
.viewtabs{display:flex;gap:8px;margin-top:4px;flex-wrap:wrap}
.vtab{border:1px solid #dee2e6;background:#fff;border-radius:10px;padding:9px 16px;font-size:14px;cursor:pointer;font-weight:600;color:#495057;transition:.15s}
.vtab.on{background:#212529;color:#fff;border-color:#212529}
.vtab .d{display:block;font-size:11px;font-weight:400;opacity:.65;margin-top:2px}
.toolbar{position:sticky;top:0;z-index:50;background:rgba(244,246,249,.94);backdrop-filter:blur(8px);padding:10px 0;border-bottom:1px solid var(--line);margin-top:12px}
.bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.search{flex:1;min-width:200px;position:relative}
.search input{width:100%;padding:9px 12px 9px 34px;border:1px solid #dee2e6;border-radius:10px;font-size:14px;background:#fff;outline:none}
.search input:focus{border-color:#ff8787;box-shadow:0 0 0 3px rgba(255,77,79,.12)}
.search .ic{position:absolute;left:11px;top:50%;transform:translateY(-50%);color:#adb5bd}
.chips{display:flex;gap:6px;flex-wrap:wrap}
.chip{border:1px solid #dee2e6;background:#fff;border-radius:20px;padding:6px 12px;font-size:13px;cursor:pointer;user-select:none;color:#495057}
.chip.on{color:#fff;border-color:transparent}
select{padding:8px 10px;border:1px solid #dee2e6;border-radius:10px;background:#fff;font-size:13px;color:#495057;outline:none;cursor:pointer}
.meta{font-size:12px;color:var(--sub);margin-top:8px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:6px}
.tbl-card{background:var(--card);border-radius:16px;box-shadow:0 2px 10px rgba(20,40,80,.06);margin-top:12px;overflow:hidden}
table.main{width:100%;border-collapse:collapse}
table.main thead th{position:sticky;top:55px;z-index:10;background:#f8f9fa;font-size:12.5px;color:#868e96;text-align:left;padding:10px 12px;border-bottom:1px solid var(--line);white-space:nowrap}
table.main td{padding:11px 12px;border-bottom:1px solid #f1f3f5;vertical-align:middle}
tr.arow:hover td{background:#fafbfd} tr.arow.expanded td{background:#fff8f0}
.rank{display:inline-flex;align-items:center;justify-content:center;min-width:30px;height:30px;border-radius:8px;font-weight:700;font-size:13px;color:#868e96;background:#f1f3f5}
.rank.top{color:#fff}
.who{display:flex;align-items:center;gap:9px;min-width:0}
.who{display:flex;align-items:center;gap:9px;min-width:0;cursor:pointer}
.who:hover .nm{color:var(--brand);text-decoration:underline}
.avatar{width:34px;height:34px;border-radius:50%;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:15px;flex:none}
.who .nm{font-weight:600;font-size:14.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:170px;display:block}
.who .sig{font-size:11px;color:#adb5bd;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:190px;display:block}
.tag{display:inline-block;font-size:11px;padding:2px 8px;border-radius:10px;font-weight:600;color:#fff;white-space:nowrap}
.tag.tgray{background:#ced4da;color:#868e96}
.badges{display:flex;gap:4px;flex-wrap:wrap}
.bd{font-size:11px;padding:2px 7px;border-radius:9px;font-weight:700;color:#fff;white-space:nowrap}
.num{font-variant-numeric:tabular-nums;white-space:nowrap}
.num.play{font-weight:700;color:#d6336c;font-size:15px}
.mini{color:#adb5bd;font-size:11px}
.ext{display:flex;gap:6px;justify-content:flex-end}
.btn{border:1px solid #dee2e6;background:#fff;border-radius:8px;padding:5px 10px;font-size:12px;cursor:pointer;color:#495057;white-space:nowrap;text-decoration:none;display:inline-block}
.btn:hover{border-color:#ff8787;color:var(--brand)}
.btn.pri{background:linear-gradient(90deg,#ff6b6b,#ff4d4f);color:#fff;border:none}
tr.det td{padding:0;background:#fbfcfe}
.det-inner{padding:14px 18px 18px;max-height:480px;overflow:auto}
.dhead{display:flex;gap:14px;flex-wrap:wrap;align-items:center;margin-bottom:10px;font-size:12px;color:var(--sub)}
.dhead b{color:var(--ink);font-size:13px}
table.alb{width:100%;border-collapse:collapse;font-size:12.8px;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 0 0 1px var(--line)}
table.alb th{background:#f8f9fa;text-align:left;padding:7px 10px;font-size:11.5px;color:#868e96;position:sticky;top:0}
table.alb td{padding:6.5px 10px;border-bottom:1px solid #f6f7f9}
table.alb tr:hover td{background:#fffdf5}
.alb .r{color:#ced4da;width:34px}
.alb .p{font-weight:700;color:#d6336c;white-space:nowrap;font-variant-numeric:tabular-nums}
.scorev{color:#f59f00;font-weight:700;font-size:12.5px;white-space:nowrap;cursor:help}
.dsort{display:inline-flex;gap:4px;margin-left:auto}
.dbtn{border:1px solid #dee2e6;background:#fff;border-radius:8px;padding:3px 9px;font-size:11.5px;cursor:pointer;color:#868e96;font-weight:600}
.dbtn.on{background:#212529;color:#fff;border-color:#212529}
.alb a{text-decoration:none}.alb a:hover{color:var(--brand)}
.st-fin{color:#2f9e44;font-size:11.5px}.st-ong{color:#e8590c;font-size:11.5px}
.star{color:#f59f00;font-size:11px;margin-left:4px}
.empty-tip{padding:50px 0;text-align:center;color:#adb5bd}
.flash{animation:fl 1.6s ease}@keyframes fl{0%{background:#fff3bf}100%{background:transparent}}
.note{background:var(--card);border-radius:14px;padding:16px 20px;margin-top:18px;font-size:12px;color:var(--sub);line-height:2}
.note b{color:var(--ink)}
.totop{position:fixed;right:22px;bottom:26px;width:42px;height:42px;border-radius:50%;background:#fff;box-shadow:0 4px 14px rgba(0,0,0,.15);border:1px solid var(--line);cursor:pointer;font-size:16px;color:#495057;z-index:60}
@media(max-width:900px){.kpis{grid-template-columns:repeat(4,1fr)}.ov{grid-template-columns:repeat(2,1fr)}.hide-m{display:none}.who .sig{display:none}.who .nm{max-width:110px}}

/* ===== 移动端专属优化 (≤700px: 卡片式布局) ===== */
@media(max-width:700px){
  .wrap{padding:0 8px 70px}
  .hero{padding:20px 0 16px;margin-bottom:-74px}
  .hero h1{font-size:18.5px;letter-spacing:0}
  .hero h1 .em{display:block;margin-top:2px}
  .hero .sub{font-size:10.5px;line-height:1.6}
  .kpis{grid-template-columns:repeat(2,1fr);gap:6px;margin-top:14px}
  .kpi{padding:8px 4px;border-radius:10px}
  .kpi b{font-size:16px}
  .kpi span{font-size:10px}
  .ov-card{margin-top:92px;padding:13px 12px 8px;border-radius:14px}
  .ov-card h3{font-size:14.5px;margin-bottom:10px}
  .ov{grid-template-columns:repeat(2,1fr);gap:8px}
  .ov .cell{padding:10px;border-radius:10px}
  .ov .cell b{font-size:18px}
  .ov .cell span{font-size:10px;line-height:1.5;display:block}
  .viewtabs{gap:6px;margin-top:10px}
  .vtab{flex:1 1 auto;padding:8px 6px;font-size:13px;text-align:center}
  .vtab .d{font-size:10px;margin-top:1px}
  .toolbar{padding:8px 0 6px}
  .bar{gap:6px}
  .search input{font-size:16px;padding:8px 10px 8px 32px;border-radius:9px} /* 16px 防iOS聚焦缩放 */
  .search .ic{left:10px}
  select{padding:8px 6px;font-size:12px;max-width:118px;border-radius:9px}
  .chips{flex-wrap:nowrap;overflow-x:auto;-webkit-overflow-scrolling:touch;margin:0 -8px;padding:2px 8px 6px;scrollbar-width:none}
  .chips::-webkit-scrollbar{display:none}
  .chip{flex:0 0 auto;font-size:12px;padding:6px 11px;touch-action:manipulation}
  .chip b{font-weight:700}
  .meta{font-size:11px;margin-top:6px;gap:4px}
  .meta #tip{flex-basis:100%;line-height:1.5}
  /* 主列表 → 卡片 */
  .tbl-card{border-radius:14px;background:transparent;box-shadow:none;overflow:visible}
  table.main thead{display:none}
  table.main,table.main tbody{display:block}
  tr.arow{display:grid;grid-template-columns:auto minmax(0,1fr) auto;
    grid-template-areas:"rank who play" "info info ops";
    gap:6px 10px;align-items:center;background:#fff;
    border:1px solid var(--line);border-radius:12px;margin:8px 2px;padding:11px 12px;
    box-shadow:0 1px 3px rgba(20,40,80,.05)}
  tr.arow td{display:block;padding:0;border:none;background:transparent}
  tr.arow:hover td{background:transparent}
  tr.arow.expanded{border-color:#ffc078;background:#fff8f0}
  td.c-rank{grid-area:rank}
  td.c-who{grid-area:who}
  td.c-info{grid-area:info}
  td.c-play{grid-area:play;text-align:right}
  td.c-play .num.play{font-size:16.5px}
  td.c-ops{grid-area:ops;justify-self:stretch}
  td.c-ops .ext{gap:8px}
  td.c-ops .btn{flex:1;text-align:center;padding:7px 8px;font-size:12.5px;touch-action:manipulation}
  .who .nm{max-width:100%;white-space:normal;font-size:15px;line-height:1.35;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
  .avatar{width:36px;height:36px}
  /* 专辑明细 → 卡片流 */
  tr.det{display:block;margin:0 2px 8px}
  tr.det td{display:block;padding:0 2px;background:transparent}
  .det-inner{padding:10px 10px 12px;max-height:66vh;border-radius:12px;background:#fbfcfe;box-shadow:0 0 0 1px var(--line)}
  .dhead{font-size:11px;gap:8px;line-height:1.7}
  table.alb{box-shadow:0 0 0 1px var(--line);border-radius:10px;background:#fff}
  table.alb thead{display:none}
  table.alb,table.alb tbody{display:block}
  table.alb tr{display:flex;flex-wrap:wrap;align-items:center;gap:3px 10px;padding:9px 10px;border-bottom:1px dashed var(--line)}
  table.alb tr:last-child{border-bottom:none}
  table.alb td{border:none;padding:0;background:transparent}
  table.alb tr:hover td{background:transparent}
  td.a-title{flex:1 1 100%;order:-1;line-height:1.5;font-size:13.5px}
  td.a-title a{word-break:break-all}
  table.alb td.r{display:none}
  td.a-play{font-size:13.5px}
  td.a-trk,td.a-fin,td.a-score{font-size:11px;color:var(--sub)}
  td.a-score .scorev{font-size:11.5px}
  td.a-trk::after{content:" 集"}
  .totop{right:12px;bottom:14px;width:40px;height:40px}
  .note{padding:12px 14px;font-size:11.5px;border-radius:12px}
}
</style>
</head>
<body>
<div class="hero">
 <div class="wrap">
  <h1>喜马拉雅 · __CAT_NAME__ <span class="em">主播及专辑播放量分档</span></h1>
  <div class="sub">双视图：按主播总播放分档 · 按单专辑播放分档（每位主播的爆款专辑） · 数据源 ximalaya.com/category/__CAT_KEY__ 前__PAGES__个分页 · 生成日期 __DATE__</div>
  <div class="kpis">
   <div class="kpi"><b>__N_ALBUMS_ALL__</b><span>主播公开专辑</span></div>
   <div class="kpi hot"><b>__NA0__</b><span>专辑 ≥ __TAN0__</span></div>
   <div class="kpi"><b>__NA1__</b><span>专辑 ≥ __TAN1__</span></div>
   <div class="kpi"><b>__NA2__</b><span>专辑 ≥ __TAN2__</span></div>
   <div class="kpi"><b>__NA3__</b><span>专辑 ≥ __TAN3__</span></div>
   <div class="kpi"><b>__NA4__</b><span>专辑 ≥ __TAN4__</span></div>
   <div class="kpi"><b>__NA5__</b><span>专辑 ≥ __TAN5__</span></div>
   <div class="kpi"><b>__NHOT__</b><span>拥有爆款的主播</span></div>
  </div>
 </div>
</div>

<div class="wrap">
 <div class="ov-card">
  <h3>📊 单专辑播放量分档总览</h3>
  <div class="ov" id="ov"></div>
  <div class="viewtabs">
   <button class="vtab on" id="vtabB" onclick="setMode('B')">🎧 作品分档模式<span class="d">每位主播的爆款专辑（单专辑播放量分档）</span></button>
   <button class="vtab" id="vtabA" onclick="setMode('A')">👤 主播分档模式<span class="d">按主播总播放分档，看全部达标专辑</span></button>
  </div>
 </div>

 <div class="toolbar">
  <div class="bar">
   <div class="search"><span class="ic">🔍</span><input id="q" type="text" placeholder="搜索主播昵称或 UID…" autocomplete="off"></div>
   <select id="sort">
    <option value="0">按总播放量 ↓</option>
    <option value="1">按爆款专辑数 ↓</option>
    <option value="2">按粉丝数 ↓</option>
    <option value="3">按最高档专辑数 ↓</option>
    <option value="4">按最高豆瓣评分 ↓</option>
   </select>
  </div>
  <div class="bar" style="margin-top:9px"><div class="chips" id="chips"></div></div>
  <div class="meta"><span id="cnt"></span><span id="tip">💡 点击主播名称或「作品」展开专辑列表（按播放量降序）</span></div>
 </div>

 <div class="tbl-card">
  <table class="main">
   <thead id="thead"></thead>
   <tbody id="list"></tbody>
  </table>
  <div class="empty-tip" id="empty" style="display:none">没有匹配的数据，换个条件试试～</div>
 </div>

 <div class="note">
  <b>统计口径</b><br>
  ① 数据源：分类页「__CAT_NAME__」前 <b>__PAGES__</b> 个分页共 <b>__N_ALBUMS_CAT__</b> 张专辑，去重得到 <b>__N_ANCHORS__</b> 位主播，再经主播主页「加载更多」接口抓取全部公开专辑（共 <b>__N_ALBUMS_ALL__</b> 张）；<br>
  ② <b>作品分档模式</b>：按单专辑播放量分档；<b>主播分档模式</b>：按主播全部公开专辑总播放量分档；<br>
  ③ 主播总播放量 = 全部公开专辑播放量之和；⭐ 表示该专辑出现在分类前__PAGES__页榜单中；<br>
  ④ ★ 评分为<b>豆瓣图书评分</b>（悬浮可见评分人数），覆盖播放量 ≥ 1亿的爆款专辑；喜马拉雅站内评分接口未公开，无法获取；专辑列表支持「按播放 / 按评分」切换排序；<br>
  ⑤ 数据由开源项目 ximalaya-ranking 自动生成（<a href="https://github.com/totootao/ximalaya-ranking" target="_blank">GitHub</a> · 支持定时/手动任务）。
 </div>
</div>
<button class="totop" onclick="window.scrollTo({top:0,behavior:'smooth'})">↑</button>

<script>
var DATA=__PAYLOAD__;
var HT=__HOST_TH__;      /* 主播总播放档位阈值(降序) */
var AT2=__ALBUM_TH__;    /* 单专辑播放档位阈值(降序) */
var GEN_DATE="__DATE__";

function fmt(n){if(n==null)return"-";if(n>=1e8){var v=n/1e8;return(Math.round(v*100)/100)+"亿";}if(n>=1e4)return Math.round(n/1e4).toLocaleString("en-US")+"万";return(n||0).toLocaleString("en-US");}
function aTier(p){for(var i=0;i<AT2.length;i++)if(p>=AT2[i])return i;return -1;}
function hTier(t){for(var i=0;i<HT.length;i++)if(t>=HT[i])return i;return -1;}
function thName(v){return fmt(v)+"档";}
function maxScore(a){var m=-1;for(var i=0;i<a[7].length;i++){var r=a[7][i];if(r.length>6&&r[6]!=null&&r[6]>m)m=r[6];}return m;}
function scoreCell(al){if(al.length<=6||al[6]==null)return '<span class="mini">-</span>';var t='★'+al[6];return '<span class="scorev" title="豆瓣 '+(al[6])+' 分'+(al[7]?' · '+al[7].toLocaleString("en-US")+' 人评':'')+'">'+t+'</span>';}
var HN=[];for(var i=0;i<HT.length;i++)HN.push(thName(HT[i]));HN.push("未达标");
var AN=[];for(var i=0;i<AT2.length;i++)AN.push(thName(AT2[i]));
var TC=__TIER_COLORS__;
var NC=Math.min(HT.length,TC.length);
function tc(i){return TC[i%TC.length];}
var AVC=["#ff6b6b","#ffa94d","#4dabf7","#69db7c","#b197fc","#f783ac","#63e6be","#a9e34b"];
var mode="B", state={t:"all",q:"",s:0};

function bigCount(a,t){var c=0;for(var i=0;i<a[7].length;i++){var x=aTier(a[7][i][2]);if(x>=0&&x<=t)c++;}return c;}
function hotCount(a){return bigCount(a,AT2.length-1);}
function topCount(a){return bigCount(a,0);}

function listOf(){
 return DATA.filter(function(a){
  if(mode==="A"){ if(state.t!=="all"&&hTier(a[6])!==+state.t)return false; }
  else{
   if(state.t==="all"){ if(hotCount(a)===0)return false; }
   else{ var t=+state.t; if(bigCount(a,t)===0)return false; }
  }
  if(state.q){var q=state.q.toLowerCase(); if(a[1].toLowerCase().indexOf(q)<0&&a[0].indexOf(q)<0)return false;}
  return true;
 }).slice().sort(function(x,y){
  var s=state.s;
  if(s===1)return hotCount(y)-hotCount(x)||y[6]-x[6];
  if(s===2)return y[2]-x[2];
  if(s===3)return topCount(y)-topCount(x)||y[6]-x[6];
  if(s===4)return maxScore(y)-maxScore(x)||y[6]-x[6];
  return y[6]-x[6];
 });
}
function avatarColor(nm){var h=0;for(var i=0;i<nm.length;i++)h=(h*31+nm.charCodeAt(i))>>>0;return AVC[h%AVC.length];}
function esc(s){return(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");}

function albumTable(a,onlyTier,sortKey){
 var rows="",list=[];
 for(var i=0;i<a[7].length;i++){
  var al=a[7][i], t=aTier(al[2]);
  if(t<0)continue;
  if(onlyTier!==null&&onlyTier!==undefined&&t!==onlyTier)continue;
  list.push(al);
 }
 if(sortKey==="score")list.sort(function(x,y){var sx=x.length>6&&x[6]!=null?x[6]:-1,sy=y.length>6&&y[6]!=null?y[6]:-1;return sy-sx||y[2]-x[2];});
 for(var i=0;i<list.length;i++){
  var al=list[i], t=aTier(al[2]);
  rows+='<tr><td class="r">'+(i+1)+'</td>'
   +'<td class="a-title"><a href="https://www.ximalaya.com/album/'+al[0]+'" target="_blank">'+esc(al[1])+'</a>'+(al[5]?'<span class="star">⭐</span>':'')+'</td>'
   +'<td class="a-tier"><span class="tag" style="background:'+tc(t)+'">'+AN[t]+'</span></td>'
   +'<td class="a-play p">'+fmt(al[2])+'</td>'
   +'<td class="a-score">'+scoreCell(al)+'</td>'
   +'<td class="a-trk num">'+al[3]+'</td>'
   +'<td class="a-fin">'+(al[4]?'<span class="st-fin">已完结</span>':'<span class="st-ong">连载中</span>')+'</td></tr>';
 }
 if(!rows)rows='<tr><td colspan="7" style="color:#adb5bd">该条件下暂无专辑</td></tr>';
 return '<table class="alb"><thead><tr><th>#</th><th>专辑名称</th><th>档位</th><th>播放量</th><th>评分</th><th>集数</th><th>状态</th></tr></thead><tbody>'+rows+'</tbody></table>';
}

function badges(a){
 var h="",tot=0;
 for(var t=0;t<AT2.length;t++){
  var c=bigCount(a,t)-(t>0?bigCount(a,t-1):0);
  if(c>0){h+='<span class="bd" style="background:'+tc(t)+'">'+AN[t]+'×'+c+'</span>';tot+=c;}
 }
 return h||'<span class="mini">无达标爆款</span>';
}

function theadHTML(){
 if(mode==="A")return '<tr><th style="width:52px">排名</th><th>主播</th><th class="hide-m">档位</th><th>总播放</th><th class="hide-m">专辑数</th><th class="hide-m">粉丝数</th><th class="hide-m">上榜</th><th style="text-align:right">操作</th></tr>';
 return '<tr><th style="width:52px">排名</th><th>主播</th><th>爆款分布</th><th>总播放</th><th class="hide-m">爆款数</th><th class="hide-m">粉丝数</th><th style="text-align:right">操作</th></tr>';
}

function render(){
 var arr=listOf(),tb="";
 document.getElementById("thead").innerHTML=theadHTML();
 for(var i=0;i<arr.length;i++){
  var a=arr[i],r=i+1,ht=hTier(a[6]);
  var top3=(ht>=0&&ht<NC&&r<=3);
  var rk='<span class="rank"'+(top3?' style="background:'+tc(ht)+';color:#fff"':'')+'>'+r+'</span>';
  var who='<div class="who" title="点击展开/收起专辑列表（按播放量降序）" onclick="toggle(\''+a[0]+'\')"><span class="avatar" style="background:'+avatarColor(a[1])+'">'+esc(a[1].slice(0,1))+'</span>'
   +'<span style="min-width:0"><span class="nm">'+esc(a[1])+'</span>'
   +(a[4]?'<span class="sig">'+esc(a[4])+'</span>':'')+'</span></div>';
  var colspan=(mode==="A")?8:7;
  if(mode==="A"){
   tb+='<tr class="arow" id="ar-'+a[0]+'"><td class="c-rank">'+rk+'</td><td class="c-who">'+who+'</td>'
    +'<td class="c-info"><span class="tag" style="background:'+(ht>=0?tc(ht):'#ced4da')+';'+(ht<0?'color:#868e96':'')+'">'+HN[ht<0?HT.length:ht]+'</span></td>'
    +'<td class="c-play"><span class="num play">'+fmt(a[6])+'</span></td>'
    +'<td class="num hide-m">'+a[7].length+'</td>'
    +'<td class="num hide-m">'+fmt(a[2])+'</td>'
    +'<td class="num hide-m">'+(a[5]||0)+'<span class="mini"> 张</span></td>'
    +'<td class="c-ops"><div class="ext"><button class="btn pri" onclick="toggle(\''+a[0]+'\')">作品</button>'
    +'<a class="btn" href="https://www.ximalaya.com/zhubo/'+a[0]+'" target="_blank">主页</a></div></td></tr>'
    +'<tr class="det" id="det-'+a[0]+'" style="display:none"><td colspan="'+colspan+'"><div class="det-inner" id="inner-'+a[0]+'"></div></td></tr>';
  }else{
   tb+='<tr class="arow" id="ar-'+a[0]+'"><td class="c-rank">'+rk+'</td><td class="c-who">'+who+'</td>'
    +'<td class="c-info"><div class="badges">'+badges(a)+'</div></td>'
    +'<td class="c-play"><span class="num play">'+fmt(a[6])+'</span></td>'
    +'<td class="num hide-m">'+hotCount(a)+'</td>'
    +'<td class="num hide-m">'+fmt(a[2])+'</td>'
    +'<td class="c-ops"><div class="ext"><button class="btn pri" onclick="toggle(\''+a[0]+'\')">作品</button>'
    +'<a class="btn" href="https://www.ximalaya.com/zhubo/'+a[0]+'" target="_blank">主页</a></div></td></tr>'
    +'<tr class="det" id="det-'+a[0]+'" style="display:none"><td colspan="'+colspan+'"><div class="det-inner" id="inner-'+a[0]+'"></div></td></tr>';
  }
 }
 document.getElementById("list").innerHTML=tb;
 document.getElementById("empty").style.display=arr.length?"none":"block";
 document.getElementById("cnt").textContent="共 "+arr.length+" / "+DATA.length+" 位主播"+(mode==="B"?"（拥有达标爆款专辑）":"");
}

var rendered={};
var detSort="play";
function renderDet(uid){
 var a=null;for(var i=0;i<DATA.length;i++)if(DATA[i][0]===uid){a=DATA[i];break;}
 if(!a)return;
 var scope=(mode==="B"&&state.t!=="all")?+state.t:null;
 var scopeTxt=scope===null?"全部达标专辑（≥ "+thName(AT2[AT2.length-1])+"）":"仅"+AN[scope]+"专辑";
 var so='<span class="dsort"><button class="dbtn'+(detSort==="play"?" on":"")+'" onclick="setDetSort(\'play\')">按播放 ↓</button>'
  +'<button class="dbtn'+(detSort==="score"?" on":"")+'" onclick="setDetSort(\'score\')">按评分 ↓</button></span>';
 document.getElementById("inner-"+uid).innerHTML=
  '<div class="dhead"><b>'+esc(a[1])+' 的专辑列表</b><span style="color:#e8590c;font-weight:600">↓ '+((detSort==="score")?"按豆瓣评分降序":"按播放量降序")+'</span><span>总播放 <b style="color:#d6336c">'+fmt(a[6])+'</b></span>'
  +'<span>粉丝 '+fmt(a[2])+'</span><span>全部专辑 '+a[7].length+' 张</span>'
  +'<span>当前展示：'+(scope===null?hotCount(a)+' 张达标爆款':scopeTxt)+'</span>'+so+'</div>'
  +albumTable(a,scope,detSort);
}
function setDetSort(k){
 if(detSort===k)return;
 detSort=k;
 var open=document.querySelectorAll('tr.det').length?document.querySelectorAll('tr.det'):[];
 for(var i=0;i<open.length;i++){
  if(open[i].style.display!=="none"){
   var uid=open[i].id.replace("det-","");
   if(document.getElementById("inner-"+uid))renderDet(uid);
  }
 }
}
function toggle(uid){
 var det=document.getElementById("det-"+uid),row=document.getElementById("ar-"+uid);
 if(!det||!row)return;
 var open=det.style.display==="none";
 if(open){
  if(!rendered[uid]){
   renderDet(uid);
   rendered[uid]=true;
  }
  det.style.display="";row.classList.add("expanded");
  det.scrollIntoView({behavior:"smooth",block:"nearest"});
 }else{det.style.display="none";row.classList.remove("expanded");}
}

function jumpTo(uid){
 if(state.q){state.q="";document.getElementById("q").value="";}
 syncChips();render();
 var row=document.getElementById("ar-"+uid);if(!row)return;
 row.scrollIntoView({behavior:"smooth",block:"center"});
 if(document.getElementById("det-"+uid).style.display!=="")toggle(uid);
 row.classList.remove("flash");void row.offsetWidth;row.classList.add("flash");
}

function setMode(m){
 mode=m;state.t="all";rendered={};
 document.getElementById("vtabA").classList.toggle("on",m==="A");
 document.getElementById("vtabB").classList.toggle("on",m==="B");
 buildChips();
 document.getElementById("tip").textContent=m==="B"?"💡 点击主播名称或「作品」展开专辑列表（按播放量降序）":"💡 点击主播名称或「作品」展开全部达标专辑（按播放量降序）";
 render();
}

function buildChips(){
 var h="";
 if(mode==="A"){
  var counts=[];for(var i=0;i<=HT.length;i++)counts.push(0);
  for(var i=0;i<DATA.length;i++){var t=hTier(DATA[i][6]);counts[t<0?HT.length:t]++;}
  for(var i=0;i<HT.length;i++)h+='<span class="chip" data-t="'+i+'">'+HN[i]+' <b>'+counts[i]+'</b></span>';
  h+='<span class="chip" data-t="'+HT.length+'">未达标 <b>'+counts[HT.length]+'</b></span>';
  h+='<span class="chip on" data-t="all">全部 <b>'+DATA.length+'</b></span>';
 }else{
  function withT(t){var c=0;for(var i=0;i<DATA.length;i++)if(bigCount(DATA[i],t)>0)c++;return c;}
  for(var i=0;i<AT2.length;i++)h+='<span class="chip" data-t="'+i+'">含 '+AN[i]+'专辑 <b>'+withT(i)+'</b></span>';
  h+='<span class="chip on" data-t="all">全部爆款主播 <b>'+withT(AT2.length-1)+'</b></span>';
 }
 document.getElementById("chips").innerHTML=h;syncChips();
}
function syncChips(){
 var cs=document.querySelectorAll("#chips .chip");
 for(var i=0;i<cs.length;i++)cs[i].classList.toggle("on",cs[i].getAttribute("data-t")===state.t);
}

(function(){
 /* 分档总览卡片(各档精确区间数量) */
 var ov="",exact=[];
 for(var i=0;i<AT2.length;i++){
  var lo=AT2[i],hi=i>0?AT2[i-1]:null,c=0;
  for(var k=0;k<DATA.length;k++)for(var j=0;j<DATA[k][7].length;j++){var p=DATA[k][7][j][2];if(p>=lo&&(hi===null||p<hi))c++;}
  exact.push(c);
 }
 for(var i=0;i<AT2.length;i++){
  ov+='<div class="cell" style="background:linear-gradient(120deg,'+tc(i)+',#ffffff55)"><b>'+fmt(exact[i])+' 张</b><span>'+AN[i]+' · '+fmt(AT2[i])+' ≤ 播放量'+(i>0?' < '+fmt(AT2[i-1]):'')+'</span></div>';
 }
 document.getElementById("ov").innerHTML=ov;

 document.getElementById("chips").addEventListener("click",function(e){
  var c=e.target.closest(".chip");if(!c)return;
  state.t=c.getAttribute("data-t");rendered={};syncChips();render();
 });
 var tm=null;
 document.getElementById("q").addEventListener("input",function(e){
  clearTimeout(tm);tm=setTimeout(function(){state.q=e.target.value.trim();render();},140);
 });
 document.getElementById("sort").addEventListener("change",function(e){state.s=+e.target.value;render();});
 buildChips();render();
})();
</script>
</body>
</html>"""


INDEX_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>喜马拉雅 · 主播及专辑播放量分档</title>
<style>
:root{--bg:#f4f6f9;--card:#fff;--ink:#212529;--sub:#6c757d;--brand:#ff4d4f}
*{box-sizing:border-box}
body{margin:0;font-family:"PingFang SC","Hiragino Sans GB","Microsoft YaHei",-apple-system,sans-serif;background:var(--bg);color:var(--ink);font-size:14px}
a{color:inherit;text-decoration:none}
.wrap{max-width:1000px;margin:0 auto;padding:36px 16px 80px}
.hero{background:linear-gradient(130deg,#182848,#27447c 55%,#3b5998);color:#fff;border-radius:20px;padding:30px 28px;margin-bottom:22px;position:relative;overflow:hidden}
.hero:before{content:"";position:absolute;right:-50px;top:-70px;width:280px;height:280px;border-radius:50%;background:radial-gradient(closest-side,rgba(255,255,255,.10),transparent)}
.hero h1{margin:0 0 8px;font-size:24px}
.hero p{margin:0;font-size:13px;opacity:.82;line-height:1.8}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px}
.card{background:var(--card);border-radius:16px;box-shadow:0 2px 10px rgba(20,40,80,.06);padding:22px;display:block;transition:.15s}
.card:hover{transform:translateY(-3px);box-shadow:0 8px 24px rgba(20,40,80,.12)}
.card .cname{font-size:18px;font-weight:700;margin-bottom:4px}
.card:hover .cname{color:var(--brand)}
.card .ckey{font-size:12px;color:var(--sub);margin-bottom:16px;font-family:monospace}
.card .cstats{display:flex;gap:18px;flex-wrap:wrap;margin-bottom:8px}
.card .cstats span{font-size:12px;color:var(--sub)}
.card .cstats b{display:block;font-size:21px;color:var(--ink);font-variant-numeric:tabular-nums}
.card .cgen{font-size:12px;color:#adb5bd;margin-top:4px}
.card .go{display:inline-block;margin-top:14px;background:linear-gradient(90deg,#ff6b6b,#ff4d4f);color:#fff;border-radius:8px;padding:7px 14px;font-size:13px;font-weight:600}
.note{font-size:12px;color:var(--sub);margin-top:24px;line-height:1.9}
@media(max-width:640px){.hero h1{font-size:20px}.grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="wrap">
 <div class="hero">
  <h1>喜马拉雅 · 主播及专辑播放量分档</h1>
  <p>多分类排行榜总览：点击任意分类卡片进入对应榜单（主播总播放分档 · 单专辑播放分档）<br>生成日期 __DATE__</p>
 </div>
 <div class="grid">__CARDS__</div>
 <div class="note">数据由开源项目 ximalaya-ranking 自动生成（<a href="https://github.com/totootao/ximalaya-ranking" target="_blank">GitHub</a> · 支持定时/手动任务）。数据版权归喜马拉雅及相应创作者所有。</div>
</div>
</body>
</html>"""


def write_web(anchors, cat_albums_count, stats_d, host_th, album_th, pages, out_path,
              cat_name="有声书-男频", cat_key="a3_b5162"):
    payload = json.dumps(anchors, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    alb_names = _tier_names(album_th)
    doc = HTML_TEMPLATE
    doc = doc.replace("__PAYLOAD__", payload)
    doc = doc.replace("__HOST_TH__", json.dumps(host_th))
    doc = doc.replace("__ALBUM_TH__", json.dumps(album_th))
    doc = doc.replace("__TIER_COLORS__", json.dumps(TIER_COLORS))
    doc = doc.replace("__DATE__", datetime.date.today().isoformat())
    doc = doc.replace("__CAT_NAME__", _esc(cat_name))
    doc = doc.replace("__CAT_KEY__", _esc(cat_key))
    doc = doc.replace("__PAGES__", str(pages))
    doc = doc.replace("__N_ALBUMS_CAT__", str(cat_albums_count))
    doc = doc.replace("__N_ANCHORS__", str(len(anchors)))
    doc = doc.replace("__N_ALBUMS_ALL__", f"{stats_d['totalAlbums']:,}")
    doc = doc.replace("__NHOT__", str(stats_d["hotAnchors"]))
    cum = []
    s = 0
    for c in stats_d["albumTier"]:
        s += c
        cum.append(s)
    for i in range(6):
        doc = doc.replace(f"__NA{i}__", str(cum[i]) if i < len(cum) else "0")
        doc = doc.replace(f"__TAN{i}__", alb_names[i].replace("档", "") if i < len(alb_names) else "-")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(doc)
    return out_path


def write_index(summaries: list, out_dir: str):
    """生成多分类总索引页(index.html), 返回索引页路径"""
    cards = ""
    for s in summaries:
        link = f"{s['key']}/index.html"
        cards += (
            '<a class="card" href="' + _esc(link) + '">'
            '<div class="cname">' + _esc(s["name"]) + '</div>'
            '<div class="ckey">' + _esc(s["key"]) + ' · ' + _esc(s["metadataValues"]) + '</div>'
            '<div class="cstats">'
            f'<span><b>{s["anchors"]:,}</b>主播</span>'
            f'<span><b>{s["albumsTotal"]:,}</b>专辑</span>'
            f'<span><b>{s["hotAnchors"]}</b>爆款主播</span>'
            '</div>'
            '<div class="cgen">更新于 ' + _esc(s["generatedAt"][:16].replace("T", " ")) + '</div>'
            '<span class="go">查看榜单 →</span>'
            '</a>'
        )
    doc = INDEX_TEMPLATE.replace("__CARDS__", cards)
    doc = doc.replace("__DATE__", datetime.date.today().isoformat())
    out_path = os.path.join(out_dir, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(doc)
    return out_path


def write_csvs(anchors, cat_albums, host_th, album_th, out_dir):
    host_names = _tier_names(host_th) + ["未达标"]
    alb_names = _tier_names(album_th)

    def host_tier_i(total):
        for i, th in enumerate(host_th):
            if total >= th:
                return i
        return len(host_th)

    def alb_tier_i(play):
        for i, th in enumerate(album_th):
            if play >= th:
                return i
        return -1

    p1 = os.path.join(out_dir, "主播播放量分档总表.csv")
    with open(p1, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["档位", "排名", "主播昵称", "UID", "主页", "粉丝数", "公开专辑数",
                    "总播放量", "总播放(格式化)", "分类页上榜专辑数", "声音总数"])
        for i, a in enumerate(anchors, 1):
            ti = host_tier_i(a[6])
            w.writerow([host_names[ti], i if ti < len(host_th) else "", a[1], a[0],
                        f"https://www.ximalaya.com/zhubo/{a[0]}", a[2], len(a[7]),
                        int(a[6]), _fmt(a[6]), a[5], a[3]])

    p2 = os.path.join(out_dir, "达标主播作品明细.csv")
    with open(p2, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["主播档位", "主播(总播放降序)", "主播总播放", "专辑内排名", "专辑名",
                    "专辑档位", "播放量", "播放(格式化)", "豆瓣评分", "评分人数", "集数", "完结", "链接", "分类页上榜"])
        for a in anchors:
            ti = host_tier_i(a[6])
            if ti >= len(host_th):
                continue
            for i, al in enumerate(a[7], 1):
                at = alb_tier_i(al[2])
                if at < 0:
                    continue
                sc = al[6] if len(al) > 6 else None
                vt = al[7] if len(al) > 7 else None
                w.writerow([host_names[ti], a[1], _fmt(a[6]), i, al[1], alb_names[at],
                            al[2], _fmt(al[2]), sc, vt, al[3], "完结" if al[4] else "连载/未知",
                            f"https://www.ximalaya.com/album/{al[0]}",
                            "是" if al[5] else ""])

    p3 = os.path.join(out_dir, "分类页专辑明细.csv")
    with open(p3, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["分类页排名", "专辑ID", "专辑名", "主播昵称", "主播ID", "播放量",
                    "播放(格式化)", "集数", "付费", "完结", "链接"])
        albums = sorted(cat_albums, key=lambda x: x.get("albumPlayCount", 0), reverse=True)
        for i, a in enumerate(albums, 1):
            pc = a.get("albumPlayCount", 0)
            w.writerow([i, a.get("albumId"), a.get("albumTitle", ""), a.get("albumUserNickName", ""),
                        a.get("anchorId"), pc, _fmt(pc), a.get("albumTrackCount", 0),
                        "付费" if a.get("isPaid") else "免费",
                        "完结" if a.get("isFinished") == 1 else "连载",
                        "https://www.ximalaya.com" + (a.get("albumUrl") or "")])
    return [p1, p2, p3]
