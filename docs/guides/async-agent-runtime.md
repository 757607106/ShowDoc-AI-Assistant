# 后台异步 Agent 运行服务

本机已按本次授权部署第三方开源 **Aegra 0.11.0 + Valkey**，由官方 Deep Agents `AsyncSubAgent`/LangGraph SDK 通过 Agent Protocol 调用。Aegra 是第三方运行服务，不是 LangChain 官方 Agent Server；本项目使用固定版本及源码 SHA 门禁的兼容补丁，不能称为官方服务器原样直接兼容。主应用继续使用现有 `.venv`，运行服务的 Python 包隔离在 Docker 镜像内。

截至 2026-11-17：服务在 `127.0.0.1:2026` 健康运行，审批恢复、更新、取消、身份范围与崩溃恢复已有下文实测证据；最终并发策略与镜像复验均已通过，`ASYNC_AGENT_RUNTIME_ENABLED=1`。浏览器已实际提交一次子代理审批并看到完成结果，也确认“后台异步”可以选择；临时验证配置未保存，用户原 Agent 配置未修改，无需另行部署。

## 固定版本与授权

- Aegra `0.11.0`，Apache-2.0，[源码 commit `46055c0b9adffe51fb168974f79dfadaa6edd612`](https://github.com/aegra/aegra/tree/46055c0b9adffe51fb168974f79dfadaa6edd612)，[许可原文](https://github.com/aegra/aegra/blob/46055c0b9adffe51fb168974f79dfadaa6edd612/LICENSE)。使用 Aegra 项目发布的 PyPI wheel，SHA256 为 `6d49695aecd4133289b9b0e84d39eb67f1fb7581cedcb1554405d93b580648d3`；应用本项目兼容补丁前，已与该源码的 102 个 Python 文件逐字比对一致。
- Valkey `9.0.7-alpine`，BSD-3-Clause，镜像固定为 `sha256:2d04268dfa26ab31cfa3fdc538866e76438b2d00e41db41b8cb86d780ac5a416`。版本来自 [Valkey 官方下载页](https://valkey.io/download/)，镜像由 [官方容器项目](https://github.com/valkey-io/valkey-container)维护。
- Deep Agents `0.7.35`、LangChain `1.5.0`、LangGraph `1.2.20` 与当前应用一致。完整依赖固定在 `deployment/async-agent/requirements.txt`。

这些组件均可免费自托管，未新增 LangSmith 或其他收费服务。Compose 明确关闭 LangSmith 和 OpenTelemetry 导出；原模型供应商与 ContextDB 仍使用已有账号，原有调用费用规则不变。

## 固定版本兼容层

镜像构建会执行 `deployment/async-agent/compat.py`，先核对固定 Aegra 源文件的 SHA256，再作以下定点适配；源码不匹配时构建失败，升级版本必须重新审查：

- Aegra `0.11.0` 原 HITL 暂停写成 `run=interrupted`、`thread=interrupted`。Deep Agents `0.7.35` 用 `run=interrupted` 表示真实取消，而 waiting 要求 `run=success`、`thread=interrupted`。补丁只修改 HITL 完结状态和对应结束信号，真实取消路径保留 `interrupted`。实测直接调用 SDK `_aobserve`/`_task_status` 得到 waiting，`_pending_interrupts` 能读取真实审批 ID。
- 补充 Thread 模型与 `GET /threads/{id}` 的 `values`、`interrupts`，使 SDK 可读取完成结果及待响应内容；可信 factory 从数据库校验授权，避免在 Thread GET 查询 graph 状态时递归调用自身。
- `deployment/async-agent/multitask_compat.py` 补齐 `interrupt`、`enqueue`、`reject` 策略，复用 Aegra 既有 PostgreSQL 运行记录与官方 worker/lease 执行路径。独立 admission 锁串行接收，同线程 execution 锁覆盖原 worker 生命周期；等待任务返回原 Valkey 队列。已实测同线程串行、异线程并行、忙时拒绝和真实中断；没有另建执行器或运行状态库。

平台还在实际资源入口校验 owner、父会话、子代理及原始 delegation 绑定，不把上游返回的授权 filter 当作所有 endpoint 已完成过滤的保证。

## 本机启动

本机部署已执行，以下命令供重现与维护。先启动已有的 `compose.postgres.yml`；bootstrap 只为运行服务创建新的 `showdoc_async_agent` 数据库和 `showdoc_async_agent_app` 受限登录角色，不迁移或删除现有平台及 Agent 数据。

```bash
.venv/bin/python deployment/async-agent/bootstrap.py
docker compose --env-file .runtime/async-agent.env -f compose.agent-runtime.yml up -d --build
docker compose --env-file .runtime/async-agent.env -f compose.agent-runtime.yml ps
curl --fail http://127.0.0.1:2026/health
```

bootstrap 从本机 `.env` 读取已有的受限应用凭据与引导管理员密码，仅将运行所需的白名单配置写入 `.runtime/async-agent.env`。该文件权限为 `0600`、目录为 `0700`，两者凭据不可公开。再次运行会保留原生成密码与签名密钥，不重置数据库角色。

此 Compose 面向 Docker Desktop：容器通过 `host.docker.internal:55432` 访问现有本机 PostgreSQL，API 仅绑定 `127.0.0.1:2026`。Valkey 不发布宿主机端口，并将 AOF 写入独立命名卷；停止服务使用 `docker compose --env-file .runtime/async-agent.env -f compose.agent-runtime.yml down`，保留命名卷。

`--env-file` 同时为 Compose 解析技能目录挂载路径，不能省略。bootstrap 将原有 `GOVERNANCE_DATA_DIR`（默认项目内 `downloads`）解析为绝对路径，只为 `<GOVERNANCE_DATA_DIR>/skill-bundles` 创建同路径只读挂载。该例外用于读取数据库记录引用的旧 Skill 归档绝对路径；不会挂载整个 `downloads`，也不会更改归档内容或权限。

## 配置边界

- Aegra 的 `DATABASE_URL` 仅指向新运行服务库，保存该服务的线程、运行和官方 checkpoint/store 表；启动时自动执行官方 Alembic 迁移。
- `PLATFORM_DATABASE_URL` 和 `AGENT_DATABASE_URL` 分别使用原有的受限平台及 Agent 账号，供可信 graph factory 读取用户配置、凭据与父会话状态。运行服务账号不能连接这两个原库。
- `AEGRA_CONFIG` 指向 `deployment/async-agent/aegra.json`；graph 配置使用相对文件入口 `../../agent/async_service.py:graph`，认证入口使用 `agent.async_service:auth`。Aegra `0.11.0` 的 graph loader 要求文件路径，不能把 Python 模块名当作该路径。
- `REDIS_BROKER_ENABLED=true` 使用 Valkey 队列、worker lease 和 reaper，不使用进程内开发任务模式。当前运行 `1 × 4` 并发 worker 任务，未启用定时任务。
- `ASYNC_AGENT_RUNTIME_SIGNING_KEY` 是平台与运行服务的共享签名密钥。请求使用用户、父会话及子代理范围绑定的服务令牌；不将此密钥放入浏览器或沙箱。
- `ASYNC_AGENT_RUNTIME_ENABLED` 首次 bootstrap 默认写为 `0`，再次执行保留现值。主应用通过真实执行链、身份隔离、恢复与策略门禁后才启用入口；单独的 `/health` 成功不足以证明这条调用链可用。

容器启动脚本会先验证自定义 `Auth` 实例、graph factory 与签名密钥存在，避免 Aegra 的可选认证加载失败后退回匿名身份。镜像构建只复制应用 Python 模块、固定依赖、启动脚本与 Aegra 配置；Dockerfile 专用白名单排除 `.env`、`.git`、`downloads` 和其他宿主机文件。

### 启用主应用入口

这是已部署服务的功能门禁，不是要求用户重新部署。本次门禁已通过并已将开关设为 `1`。下面是维护时的同等启用操作，仅修改私有 env 中这一项：

```bash
# 所有门禁通过后执行；不打印或重写其他凭据
.venv/bin/python -c "from dotenv import set_key; set_key('.runtime/async-agent.env', 'ASYNC_AGENT_RUNTIME_ENABLED', '1')"
```

主应用优先读取进程环境，未显式配置时再读取 `.runtime/async-agent.env`。若启动环境显式设为 `0`，需同步修改该启动配置并重启主 API；仅改私有文件不能覆盖它。此开关无需重建运行镜像。随后刷新部署能力接口及前端页面，确认 `agents.async.supported=true`，再创建显式异步子代理；关闭开关不会撤销已经提交到远端的任务。

主会话请求断开会结束本次同步请求；已提交的 AsyncSubAgent 在独立服务中继续。父会话停止与后台任务取消是不同操作，后台任务必须通过所属任务的取消入口处理。远端完成不自动唤醒父会话，用户可从现有后台任务入口查看已完成结果、发送更新或响应原生中断。历史 Shell 行保持只读。

## 已执行的真实验收

2026-11-17 已确认两服务 healthy、`/health` 返回 200、`pip check` 通过，Redis worker 与 lease reaper 已启动。无令牌及伪造令牌被拒绝；36 项真实 HTTP 范围检查全部通过，拒绝请求未新增 run，见[身份范围证据](../../output/verification/deepagents-native-implementation-20261117/async-scope.json)。Skill 挂载实际只读，镜像不含宿主私有文件；Valkey 正常重启后保留临时测试键，测试键已删除。

独立 opt-in 脚本不依赖 pytest 全局 fixture，只创建本次唯一模型与会话，调用本机 HTTP 假模型，不产生收费模型调用：

```bash
.venv/bin/python scripts/verify_async_agent_runtime.py --run
```

[审批与更新证据](../../output/verification/async-approval-acceptance.json)记录 5 个场景全部通过：edit 恢复（含 SDK 原生 waiting/interrupt ID 和三种非法响应拒绝）、approve 恢复、完成后更新、waiting 时 enqueue 更新不执行旧待批写入、waiting 取消。共 8 次本机假模型请求，4 个临时父会话、所属远端资源和临时模型已清理。另已实测远端 `ask_user` 的 `false`、`null` 响应，恢复后的真实 ToolMessage 保留原 JSON 值。

[取消与崩溃恢复证据](../../output/verification/deepagents-native-implementation-20261117/async-recovery.json)记录真实 Shell 取消前后 tick 数为 `16 → 16`、排队 run 一并取消；服务被 `SIGKILL` 后，同一 thread、同一 run 恢复为 success，两个临时会话已清理。该取消与 SIGKILL 恢复已在包含最终 multitask 补丁的镜像上复验通过。

[真实并发策略证据](../../output/verification/deepagents-native-implementation-20261117/async-multitask.json)：busy reject 返回 409；4 个 enqueue 按 FIFO 执行，本机假模型实际最大并发为 1；不同线程实际重叠 3 秒；interrupt 的旧连接先断开且 lease 释放后，新运行成功。复现：`.venv/bin/python scripts/verify_async_multitask.py`。这些任务使用真实 REST、DeepAgents、PostgreSQL 与 Valkey，只有模型提供方为本机替身。

[跨进程锁崩溃证据](../../output/verification/deepagents-native-implementation-20261117/async-lock-crash.json)：独立进程持有实际部署的 PostgreSQL 锁，另一进程无法取得；仅 SIGKILL 该 probe 子进程后自动释放，未重启服务。未启动第二个 Aegra 实例。

服务离线时的清理请求保留父会话与原授权；服务恢复后对精确临时 ID 重试清理成功，见[失败保留与重试证据](../../output/verification/deepagents-native-implementation-20261117/async-offline-cleanup.json)。

## 维护与限制

```bash
docker compose --env-file .runtime/async-agent.env -f compose.agent-runtime.yml logs --tail=100 agent-runtime
docker compose --env-file .runtime/async-agent.env -f compose.agent-runtime.yml exec valkey valkey-cli ping
docker compose --env-file .runtime/async-agent.env -f compose.agent-runtime.yml exec agent-runtime pip check
.venv/bin/python deployment/async-agent/test_start.py
```

不要把 `docker compose config` 的完整输出或容器环境发到公共日志，它们包含私有凭据。备份需要同时覆盖独立 PostgreSQL 数据库、Valkey 命名卷与私有 env 文件。

当前是单机、非 HA 配置。Valkey AOF `everysec` 存在尚未落盘的丢失窗口，不是零丢失保证；主 API 仍为单进程。checkpoint 恢复不保证外部工具或服务副作用 exactly-once，业务写入仍需相应的幂等与核对；取消也不回滚已完成的副作用。本配置未部署公网 HTTPS、外部监控或托管云账号。
