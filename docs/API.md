# HTTP API 一览

基址：`/api/v1`。交互式文档：`/api/docs`。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 健康检查、数据模式、政策条数 |
| GET | `/meta` | 分类树、数据源、条款类型 |
| GET | `/dashboard` | 首页统计 |
| GET | `/policies` | 检索筛选，`q/title/policy_level/issuing_org/category/clause_type/date_from/date_to/sort/page` |
| GET | `/policies/{id}` | 详情（结构化 + 分析 + 原文） |
| GET | `/policies/{id}/related` | 相关政策 |
| POST | `/policies/{id}/analyze` | 刷新分析（写操作，生产需 `X-Admin-Token`） |
| POST | `/policies/compare` | 多政策对比 |
| POST/DELETE | `/favorites/{id}` | 收藏 |
| GET | `/export/excel?ids=` | 列表与合规摘要 Excel |
| GET | `/export/pdf/{id}` | 单政策 PDF |
| GET/POST/DELETE | `/subscriptions` | 订阅 |
| POST | `/digests/generate` | 生成日报 |
| POST | `/ingest/url` | URL/正文补录 |
| POST | `/ingest/snapshot` | 装载快照 |
| POST | `/ingest/crawl` | 实时采集（失败回退快照） |

写操作在 `APP_ENV=production` 且配置了 `ADMIN_TOKEN` 时必须携带请求头 `X-Admin-Token`。开发默认放行以便冷启动。
