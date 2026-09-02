# 数据库要点（SQLite）

文件默认：`data/runtime/app.db`。

## 表

| 表 | 用途 |
| --- | --- |
| policies | 政策主数据，唯一约束 `(title, issuing_org, publish_time)` |
| policy_categories | 6 大类 + 子类 |
| policy_clauses | 强制 / 禁止 / 推荐条款及原文摘录 |
| policy_structured | 适用范围、主题、关键条款 |
| compliance_analyses | 四段合规摘要 + provenance |
| favorites | 收藏（MVP 单用户） |
| subscriptions | 关键词 / 分类 / 机构订阅 |
| digests | 站内日报 |
| crawl_jobs | 采集任务审计 |
| policy_fts | FTS5 全文索引（jieba 分词后写入） |

字段与设计方案 4.2 对齐，并补充 `content_hash`、`ingest_method`、`snapshot_id`、`review_flag` 以支持去重、复现与质量标记。
