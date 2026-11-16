# OpenSandbox 本机受限开发部署

使用官方 OpenSandbox 1.2.1 自托管控制服务、官方 Python SDK 和用户批准的 Apache-2.0 社区 `langchain-sandbox-opensandbox==0.1.2`。沿用现有 PostgreSQL 服务；控制服务的原生 PostgreSQL store 使用第三个专用数据库和账号，与平台、Agent 数据库均隔离，不部署 SQLite。

1. 在本项目 `.env` 设置随机的 `OPEN_SANDBOX_API_KEY` 和专用 `OPENSANDBOX_STORE_POSTGRESQL_DSN`；不要提交此文件。应用使用同一个 API key，默认控制服务为 `127.0.0.1:8090`。先由引导管理员创建独立 `opensandbox_control` 库及受限账号，撤销 PUBLIC CONNECT，只授予控制账号 CONNECT、public schema USAGE/CREATE；业务账号不具备该库连接权限。Docker Desktop 中 DSN 主机使用 `host.docker.internal`；正式 Linux 部署使用控制容器可达的内网地址。官方服务自行初始化 store，不自建表或实现控制状态层。
2. 安装项目锁定的 requirements 到项目 `.venv`。
3. 启动独立控制服务：

   ```sh
   docker compose -f compose.opensandbox.yml up -d
   curl -fsS http://127.0.0.1:8090/health
   ```

4. 构建固定附件解析镜像：

   ```sh
   docker build -t showdoc-attachment-parser:local -f docker/attachment-parser.Dockerfile docker
   ```

   镜像预装固定解析依赖和 Docling OCR 模型；下载仅发生在构建时。运行时非 root、无宿主挂载、无凭据、默认拒绝网络，临时沙箱解析后销毁。模型调试图片也在此镜像中校验真实 MIME。镜像未构建或沙箱不可用时失败，不回退宿主解析。
5. 在原版 Agent 编辑器选择 `OpenSandbox（受限开发环境）`。执行容器按 owner/session 独立创建；只读账号及 `read_only` 访问级别保持无 Shell。`confirm` 使用官方 HITL 审批命令执行。
6. 需要运行真实本机回归时：

   ```sh
   OPEN_SANDBOX_TEST_REAL=1 .venv/bin/pytest -q tests/test_platform_sandbox.py tests/test_attachment_parser.py tests/test_platform_artifacts.py
   ```

控制服务仅发布到本机 8090。可信控制服务需要 Docker socket 管理子容器；该 socket 和宿主目录不会传给执行容器。不要把本机控制服务或执行端口直接开放到公共网络。

官方 Docker 后端不支持 `secure_access=True`，会明确返回 400；执行端点的 loopback 端口不能隔离同一宿主上的其他本地进程。本机方案仅用于用户已接受的可信单用户开发环境。生产端点鉴权须使用官方 Kubernetes ingress gateway，未自行添加网关。[官方限制](https://github.com/opensandbox-group/OpenSandbox/blob/main/docs/guides/secure-access.md)

执行环境默认 1 CPU、512 MiB、128 进程、30 分钟 TTL，无请求卷挂载、无平台凭据，使用官方 `dns+nft` 出网默认拒绝策略。依赖安装、浏览器外网访问等需要管理员另行确认出网策略，不能从 Agent 表单绕过托管配置。

SDK 客户端关闭与沙箱销毁分开：HTTP 请求结束只关闭客户端；删除或清空会话先调用官方 kill 再删除句柄。过期环境不会在普通聊天中静默重建；原版终端上的主动创建动作可重建已回收环境。Fork 创建新环境，只恢复 checkpoint 中的附件，不复制旧执行文件系统。

官方 Docker 过期调度使用相对 Timer。正常时钟下，独立初次创建的 60 秒 TTL 已实测自行回收执行容器、egress 和卷；但本机也观察到墙钟大幅前进、单调时间未同比前进时，旧环境超过 `expires_at` 仍运行，之后才被原生计时器清理。具体暂停或调时原因尚未确认，因此不能把此开发部署的 TTL 宣称为严格墙钟截止保证。本次未添加自制过期清理器。

`/state/` 和 `/memories/` 是官方 CompositeBackend 的虚拟路由。Skill 仍是只读虚拟文件，Shell 不能直接执行其中的附带脚本。真实沙箱当前文件没有消息级历史版本；本次未自行发明产物快照机制。

本机 Docker Desktop 只有 runc，尚未配置 Kata，daemon 报告 seccomp profile 为 unconfined。这里完成的是受限开发功能验证；生产强化方案及待验收清单见[生产部署说明](opensandbox.production.md)。官方 server-proxy 路径仍可用但已进入安全和缺陷维护模式，生产使用官方 Gateway。

既有 SQLite 控制元数据切换前须确认官方列表中没有活动沙箱，并保留旧控制卷备份；不能直接删除数据库来跳过仍运行的环境。业务 checkpoint/Store 的迁移使用[双库迁移工具](../docs/guides/agent-postgres-isolation.md)，与控制服务 store 无关。

开发验收曾观察到官方 Docker 端口分配碰撞导致 503，失败环境已由官方服务清理。配置使用官方默认的 40000–60000 端口候选范围降低碰撞概率，仍仅发布 loopback；没有添加自制分配器或重试掩盖失败。此部署不保证端口分配永不失败。

上游依据：[Deep Agents 示例](https://open-sandbox.ai/examples/deep-agents)、[官方 Docker Compose](https://github.com/opensandbox-group/OpenSandbox/blob/main/server/docker-compose.example.yaml)、[官方 PTY 协议](https://github.com/opensandbox-group/OpenSandbox/blob/main/components/execd/PTY.md)。
