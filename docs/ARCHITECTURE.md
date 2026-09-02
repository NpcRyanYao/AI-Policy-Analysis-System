# 技术架构

四层轻量架构，对应设计方案，并按 3 日交付做了收敛。

```
采集层   crawlers + 快照装载 + 手工 URL 补录
处理层   规则引擎结构化 / 可选大模型 JSON 解析 + 合规分析
服务层   FastAPI REST（检索、详情、对比、订阅、导出、采集）
展示层   Vue 3 + Element Plus
```

## 为何这样选

| 选择 | 理由 | 放弃项 |
| --- | --- | --- |
| SQLite + FTS5 | 零运维，评审冷启动成本最低 | Elasticsearch |
| jieba 分词写入 FTS | 中文检索可用且无额外部署 | 自建 ES 分词 |
| 规则引擎 + 可选 LLM | 无 Key 也能验收；有 Key 时提高归纳质量 | 强制依赖商业模型 |
| 单管理员令牌 | 符合 MVP「公开访问 + 写操作保护」 | 完整用户体系 |
| Docker Compose 双容器 | 与设计方案一致，环境可复现 | K8s |

## 目录职责

- `backend/app/api/v1`：HTTP 适配，不放业务规则
- `backend/app/services`：检索、去重、分析、导出、订阅
- `backend/app/crawlers`：礼貌抓取（间隔、UA），失败可观测
- `backend/app/llm`：OpenAI 兼容协议，默认对接豆包 Ark
- `data/snapshots/`：带 `captured_at` 的验收数据

## 数据流

1. 启动 → 建表 + FTS → 库空则装载快照
2. 解析 → 分类 / 条款 / 生效时间
3. 分析 → 四段合规摘要 + provenance
4. 索引 → jieba 分词写入 FTS5
5. 订阅 → 关键词/分类/机构匹配 → 站内日报
