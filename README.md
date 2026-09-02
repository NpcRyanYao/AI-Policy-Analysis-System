# 国内 AI 监管政策动态追踪与合规影响分析系统

面向中小科技企业合规专员、产品负责人和科技律所初级律师的轻量 SaaS：**公开政策采集 → 结构化解析 → 合规影响研判 → 原文可追溯**。

本仓库是考核任务的可运行交付。完整产品判断与取舍见：

- [考核任务书](./AI政策分析系统考核任务书.md)
- [产品与技术设计方案](./国内AI监管政策动态追踪与合规影响分析系统%20产品与技术设计方案.md)
- [已知限制与下一步](./docs/LIMITATIONS.md)
- [架构说明](./docs/ARCHITECTURE.md)
- [接口一览](./docs/API.md)

## 为谁解决什么问题

| 用户 | 问题 | 本系统怎么处理 |
| --- | --- | --- |
| AI 产品负责人 | 政策散落、更新快 | 国家 + 北上广浙定向库 + 检索/订阅 |
| 企业合规专员 | 条文难拆、难判断影响 | 结构化条款 + 合规摘要（带来源摘录） |
| 科技律所初级律师 | 交叉检索慢 | 多维筛选、对比、Excel/PDF 导出 |

**明确不做：** 企业定制法律意见、处罚案例深挖、海外政策、人工专家审核。

## 前置条件

- Python 3.11+（开发验证为 3.12）
- Node.js 20+
- Windows / macOS / Linux 均可；下列命令以 PowerShell 为例
- 可选：Docker Desktop（一键部署）
- 可选：豆包/Ark 或其他 OpenAI 兼容大模型 Key（**无 Key 时使用规则引擎兜底，主流程仍可演示**）

## 本地启动（干净环境）

在仓库根目录执行：

```powershell
# 1. 配置环境变量（不含真实密钥）
copy .env.example .env

# 2. 后端（仓库根目录创建虚拟环境）
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements-dev.txt
$env:PYTHONPATH = "$((Get-Location).Path)\backend"
python -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

另开一个终端：

```powershell
cd frontend
npm install
npm run dev
```

浏览器打开：<http://127.0.0.1:5173>

首次启动若数据库为空，会自动装载 `data/snapshots/2026-08-31/` 快照（含原文 URL 与采集时间戳）。

### Linux / macOS 对照

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt
export PYTHONPATH="$PWD/backend"
python -m uvicorn app.main:app --app-dir backend --reload --port 8000
```

```bash
cd frontend && npm install && npm run dev
```

## 验证

```powershell
# 健康检查
curl http://127.0.0.1:8000/api/v1/health

# 自动化测试（仓库根目录已激活 venv）
cd backend
python -m pytest -q
```

OpenAPI：<http://127.0.0.1:8000/api/docs>

## 快照复现与实时采集

| 模式 | `.env` | 行为 |
| --- | --- | --- |
| 快照（评审推荐） | `DATA_MODE=snapshot` `SNAPSHOT_ID=2026-08-31` | 只读本地带时间戳样例，不访问外网 |
| 实时 | `DATA_MODE=live` `CRAWL_ENABLED=true` | 尝试抓取官方站点；失败则回退快照，不覆盖已有库 |

手动命令：

```powershell
$env:PYTHONPATH = "$((Get-Location).Path)\backend"
python -m app.cli seed
python -m app.cli crawl --snapshot-only
python -m app.cli digest
```

页面「补录/采集」可粘贴官方 URL 或正文；政府站点反爬失败时请改用快照或手工粘贴。

## Docker 一键部署

```powershell
copy .env.example .env
docker compose up --build
```

访问 <http://127.0.0.1:8080> ，API 在容器内通过 Nginx 反代 `/api`。

停止：`docker compose down`

## 事实 / 推断 / 建议

详情页与 API 的 `analysis.provenance` 标明：

- **事实**：标题、发文机构、日期、原文 URL、原文摘录、原文写明的罚则
- **推断**：分类、条款类型、核心监管要求归纳
- **建议**：通用行动清单，**不构成法律意见**

## 密钥

所有密钥只出现在环境变量。请勿把真实 `.env` 提交进仓库。大模型未配置时系统仍可运行。

## 停止

本地：在运行 uvicorn / `npm run dev` 的终端按 `Ctrl+C`。Docker：`docker compose down`。

## 项目结构

```
backend/app/          FastAPI 应用（api / services / crawlers / llm / workers）
frontend/src/       Vue 3 页面（概览、政策库、详情、对比、订阅、补录）
data/snapshots/     带时间戳的可复现样例
docs/               架构、接口、限制与测试记录
```
