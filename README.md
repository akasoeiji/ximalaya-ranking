# ximalaya-ranking 🎧

喜马拉雅**多分类**「主播 / 专辑播放量分档」工具：对每个分类爬取前 50 个分页 → 去重主播 → 逐主播抓取个人主页全部公开专辑 → 按 **主播总播放量 / 单专辑播放量** 双维度分档（3亿 / 2亿 / 1亿 / 5000万 / 3000万 / 1000万 / 500万）→ 生成交互式排行榜网页 + CSV。

当前内置分类：

| 分类 | URL | categoryId | 子频道 |
|---|---|---|---|
| 有声书-男频 | [a3_b5162](https://www.ximalaya.com/category/a3_b5162/) | 3 | 男频 |
| 生活-生活闲聊 | [a1006_b294641](https://www.ximalaya.com/category/a1006_b294641/) | 1006 | 生活闲聊 |

> 纯 Python 标准库实现，**零第三方依赖**。分类可在 `config.json` 中自由增删。

## 功能

- **多分类并行**：`config.json` 中配置 `categories` 列表，每个分类独立爬取、独立生成榜单，输出到 `output/{分类key}/`，并生成总索引页 `output/index.html`
- **分类分页爬取**：`/revision/category/v2/albums` 接口，默认 50 页 × 40 张（服务端深度上限约 2016 张）
- **主播主页爬取**：`/revision/user/pub`「加载更多」接口，抓取每位主播全部公开专辑，支持并发、断点续抓
- **双维度分档**：主播总播放 = 全部公开专辑播放量之和；档位阈值可在 `config.json` 调整
- **豆瓣评分**：自动为播放量 ≥1亿的爆款专辑匹配豆瓣图书评分（`xmr/douban.py`，标题清洗 + suggest 匹配 + 低频抓取 + 增量缓存 `douban_scores.json`，跨分类共享）；专辑列表支持「按播放 / 按评分」切换
- **报告输出**：每个分类单文件交互式网页（搜索 / 分档筛选 / 排序 / 展开作品明细，离线可用）+ 3 份 CSV + summary.json；根目录另生成多分类总索引页

## 快速开始

### 本地运行

```bash
python -m xmr.run_all                 # 完整跑(所有分类, 各50页)
python -m xmr.run_all --pages 3 --max-anchors 30   # 小规模验证(作用于所有分类)
python -m xmr.run_all --skip-crawl    # 仅用缓存重建报告
```

结果输出到 `output/`：根目录 `index.html`（多分类总索引）与 `summary.json`；每个分类一个子目录 `output/{分类key}/`，内含该分类的 `index.html`（排行榜网页）、`喜马拉雅主播专辑播放量分档.html`、3 份 CSV、`summary.json`。

### Docker 运行

```bash
# 手动执行一次
docker run --rm -v $PWD/output:/app/output totootao/ximalaya-ranking:latest

# 定时模式: 每 86400 秒(每天)自动执行一轮
docker run --rm -e RUN_MODE=schedule -e SCHEDULE_INTERVAL_SECONDS=86400 \
  -v $PWD/output:/app/output totootao/ximalaya-ranking:latest
```

或使用 compose：`docker compose up`（`RUN_MODE=schedule` + `restart: unless-stopped` 即为常驻定时任务）。

镜像：[`totootao/ximalaya-ranking`](https://hub.docker.com/r/totootao/ximalaya-ranking)（由 GitHub Actions 自动构建推送）。

## GitHub Actions（手动执行 + 定时任务）

| Workflow | 触发方式 | 说明 |
|---|---|---|
| **Crawl Ranking** | `workflow_dispatch`（可传 pages / max_anchors）+ `cron: 0 2 * * *`（每天北京 10:00） | 爬取→生成报告→发布到 **GitHub Pages**，并上传 Artifacts |
| **Docker Publish** | `workflow_dispatch` + push main + `cron: 0 3 * * 1`（每周一北京 11:00） | 构建镜像并推送到 Docker Hub |

**在线榜单**：<https://totootao.github.io/ximalaya-ranking/>

> **首次部署前需手动启用 Pages**（一次性）：仓库 `Settings → Pages → Build and deployment → Source` 选择 **GitHub Actions**。GitHub 出于安全设计，自动生成的 `GITHUB_TOKEN` 无权创建 Pages 站点，故 workflow 中不再使用 `configure-pages` 的 `enablement` 参数，需手动开启一次后即可持续自动部署。私有仓库需为公开仓库或付费计划才能使用 Pages。

需要的仓库 Secrets（Settings → Secrets and variables → Actions）：

| Secret | 说明 |
|---|---|
| `DOCKERHUB_USERNAME` | Docker Hub 用户名 |
| `DOCKERHUB_TOKEN` | Docker Hub 密码或 Access Token |

## 配置（config.json / 环境变量）

### 分类列表（categories）

每个分类支持以下字段：

| 键 | 说明 |
|---|---|
| `key` | 分类 URL 标识，形如 `a3_b5162`（也用作输出子目录名） |
| `name` | 分类展示名，如「有声书-男频」 |
| `categoryId` | 喜马拉雅一级分类 ID（3=有声书，1006=生活） |
| `metadataValues` | 子频道名（如「男频」「生活闲聊」） |
| `sort` | 排序方式，1=最多播放 |
| `pages` | 抓取分页数，默认 50 |
| `pageSize` | 每页条数，默认 40 |
| `extraAnchors` | 该分类额外指定主播 UID（不在分类页也会被抓取） |

### 全局配置

| 键 | 环境变量 | 默认 | 说明 |
|---|---|---|---|
| `crawl.maxAnchors` | `XMR_MAX_ANCHORS` | 0 | 限制每个分类抓取主播数，0=全部 |
| `crawl.workers` | `XMR_WORKERS` | 6 | 并发线程 |
| `tiers.host` / `tiers.album` | - | [3e8, 2e8, 1e8, 5e7, 3e7, 1e7, 5e6] | 分档阈值（降序，可增删） |
| `douban.*` | - | - | 豆瓣评分抓取参数 |

> 环境变量 `XMR_PAGES` / `XMR_PAGE_SIZE` 作用于所有分类；`XMR_CATEGORY_ID` / `XMR_METADATA` / `XMR_SORT` 仅在**单分类**场景下切换分类（向后兼容旧用法）。

## 项目结构

```
xmr/
├── config.py       # 配置加载(config.json + 环境变量, 支持多分类)
├── http_client.py  # urllib 封装(重试/退避)
├── crawler.py      # 分类分页 + 主播专辑爬取(并发/断点续抓)
├── analyze.py      # 组装与分档统计
├── report.py       # 交互式HTML + CSV + 多分类总索引页
└── run_all.py      # CLI 入口(遍历所有分类)
.github/workflows/  # crawl.yml(爬取+Pages) / docker-publish.yml(镜像)
entrypoint.sh       # manual / schedule 双模式
```

## 免责声明

本项目仅调用喜马拉雅公开 Web 接口做数据分析，请控制请求频率、勿用于商业用途；数据版权归喜马拉雅及相应创作者所有。

## 需求更新记录

- 2026-10-08 增加「生活-生活闲聊」分类（a1006_b294641），支持多分类并行爬取与分榜单输出，新增多分类总索引页
- 2026-10-09 修复 GitHub Actions Pages 部署报错（GITHUB_TOKEN 无权创建 Pages 站点，移除 configure-pages 的 enablement 参数，改为首次手动启用 Pages）
- 2026-10-09 修复排行榜表头（thead）遮挡第一行的样式问题（表头吸顶位置动态适配工具栏实际高度，避免钻入工具栏下方）
- 2026-10-09 修复主播专辑明细表（table.alb）表头吸顶遮挡行内容的问题（明细区滚动范围小，移除其 thead 的 sticky 定位）
