# 测试执行记录

执行环境：Windows 10，Python 3.13.5，仓库根目录 `.venv`。

```powershell
cd backend
python -m pytest -q
```

## 结果（修复生效日期格式后的用例）

| 模块 | 覆盖点 | 结果 |
| --- | --- | --- |
| `test_api.py` | 健康检查、列表/详情溯源、关键词检索、对比、Excel 导出、订阅日报、404 | 通过（首次全绿中的 API 部分） |
| `test_rules_and_dedup.py` | 分类/条款抽取、事实-推断-建议分层、三重去重 | 解析用例曾因 `effective_time` 带 `T00:00:00` 失败，已改为日期 ISO；去重与 provenance 通过 |
| `test_utils.py` | 日期解析、jieba 分词 | 通过 |

首次完整跑：`10 passed, 1 failed`；失败项已修。请评审时在干净环境再执行一次 `pytest -q`。

## 运行时抽查（2026-08-31）

```
GET /api/v1/health
{"status":"ok","data_mode":"snapshot","snapshot_id":"2026-08-31","policy_count":12,"llm_ready":false}
```

快照 12 条政策已自动入库，原文 URL 可在详情接口返回。
