# 单机 Docker 发版

部署目录为 `/home/rwx_cloud/ShowDoc-AI-Assistant`。在服务器上运行以下命令更新跟踪的 Git 分支并发版。

```bash
cd /home/rwx_cloud/ShowDoc-AI-Assistant
./.runtime/release/release.sh
```

开发代码推送到服务器检出的分支后，脚本拉取上游提交并仅允许快进合并。拉取失败时最多尝试三次。当前服务器跟踪 `origin/test`。需要部署已检出的提交时传入 `--local`。部署文件纳入上游分支后，服务器入口会执行仓库内的发版脚本，也可以直接运行 `./deploy/release/release.sh`。脚本需要 Docker Compose 2.24.4 或以上版本、支持 `history rm` 的 Buildx，以及 Docker 访问权限。

发版启动前端、API、Worker、PostgreSQL，以及与本地共用 Compose 配置的 Aegra、Valkey 和 OpenSandbox。Web 默认在服务器 `http://127.0.0.1:18080`，可通过 `SHOWDOC_HTTP_BIND` 和 `SHOWDOC_HTTP_PORT` 配置。PostgreSQL、Aegra 和 OpenSandbox 的宿主端口与本地一致，分别为 `127.0.0.1:55432`、`127.0.0.1:2026` 和 `127.0.0.1:8090`。沙箱执行端口仅绑定 Docker 网桥。

首次运行会在 `.runtime/production` 生成私有配置和凭据，初始管理员账号与密码在 `app.env`。平台、Agent、异步运行和沙箱控制使用 PostgreSQL 上的独立数据库。ContextDB 成员凭据和模型在平台设置中配置。

脚本按 Git 提交构建应用、前端和异步运行镜像，已有同版本镜像直接复用。外部服务镜像仅在本机缺失时拉取。Compose 根据镜像和配置变化更新服务。全部通过健康检查后，脚本删除项目构建器的历史记录，清理旧缓存和未使用的项目镜像。备份时请同时保留 `.runtime/production`、PostgreSQL、Valkey、产物和技能卷。
