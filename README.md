# ximalaya-ranking 🎧

喜马拉雅「有声书-男频」分类（[a3_b5162](https://www.ximalaya.com/category/a3_b5162/)）**主播 / 专辑播放量分档**工具：
爬取分类前 50 个分页 → 去重主播 → 逐主播抓取个人主页全部公开专辑 → 按 **主播总播放量 / 单专辑播放量** 双维度分档（3亿 / 2亿 / 1亿 / 5000万 / 3000万 / 1000万 / 500万）→ 生成交互式排行榜网页 + CSV。

> 纯 Python 标准库实现，**零第三方依赖**。

## 功能

- **分类分页爬取**：`/revision/category/v2/albums` 接口，默认 50 页 × 40 张（服务端深度上限约 2016 张）
- **主播主页爬取**：`/revision/user/pub`「加载更多」接口，抓取每位主播全部公开专辑，支持并发、断点续抓
- **双维度分档**：主播总播放 = 全部公开专辑播放量之和；档位阈值可在 `config.json` 调整
- **报告输出**：单文件交互式网页（搜索 / 分档筛选 / 排序 / 展开作品明细，离线可用）+ 3 份 CSV + summary.json

## 快速开始

### 本地运行

```bash
python -m xmr.run_all                 # 完整跑(50页)
python -m xmr.run_all --pages 3 --max-anchors 30   # 小规模验证
python -m xmr.run_all --skip-crawl    # 仅用缓存重建报告
```

结果输出到 `output/`：`index.html`（排行榜网页）、`喜马拉雅主播专辑播放量分档.html`、3 份 CSV、`summary.json`。

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

需要的仓库 Secrets（Settings → Secrets and variables → Actions）：

| Secret | 说明 |
|---|---|
| `DOCKERHUB_USERNAME` | Docker Hub 用户名 |
| `DOCKERHUB_TOKEN` | Docker Hub 密码或 Access Token |

## 配置（config.json / 环境变量）

| 键 | 环境变量 | 默认 | 说明 |
|---|---|---|---|
| `category.pages` | `XMR_PAGES` | 50 | 分类抓取分页数 |
| `category.pageSize` | `XMR_PAGE_SIZE` | 40 | 每页专辑数 |
| `category.categoryId` | `XMR_CATEGORY_ID` | 3 | 3=有声书 |
| `category.metadataValues` | `XMR_METADATA` | 男频 | 子频道 |
| `crawl.maxAnchors` | `XMR_MAX_ANCHORS` | 0 | 限制主播数，0=全部 |
| `crawl.workers` | `XMR_WORKERS` | 6 | 并发线程 |
| `crawl.extraAnchors` | `XMR_EXTRA_ANCHORS` | [] | 额外指定主播UID（逗号分隔），不在分类页也会被抓取 |
| `tiers.host` / `tiers.album` | - | [3e8, 2e8, 1e8, 5e7, 3e7, 1e7, 5e6] | 分档阈值（降序，可增删） |

## 项目结构

```
xmr/
├── config.py       # 配置加载(config.json + 环境变量)
├── http_client.py  # urllib 封装(重试/退避)
├── crawler.py      # 分类分页 + 主播专辑爬取(并发/断点续抓)
├── analyze.py      # 组装与分档统计
├── report.py       # 交互式HTML + CSV 生成
└── run_all.py      # CLI 入口
.github/workflows/  # crawl.yml(爬取+Pages) / docker-publish.yml(镜像)
entrypoint.sh       # manual / schedule 双模式
```

## 免责声明

本项目仅调用喜马拉雅公开 Web 接口做数据分析，请控制请求频率、勿用于商业用途；数据版权归喜马拉雅及相应创作者所有。
