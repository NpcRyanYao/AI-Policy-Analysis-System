# 部署说明

## Docker

根目录：

```powershell
copy .env.example .env
docker compose up --build
```

- Web: http://127.0.0.1:8080
- 后端健康: http://127.0.0.1:8000/api/v1/health
- 数据卷：`./data` → 容器 `/app/data`

生产请设置：

```
APP_ENV=production
ADMIN_TOKEN=<随机长令牌>
LLM_API_KEY=<可选>
```

## 运维注意

- SQLite 文件在 `data/runtime/app.db`，备份该目录即可。
- `SCHEDULER_ENABLED=true` 后按 cron 在容器时区（Asia/Shanghai）跑采集与日报。
- 不要把 `.env` 打进镜像；compose 使用 `env_file`。
