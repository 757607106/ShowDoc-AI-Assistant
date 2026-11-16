# PostgreSQL 双库与应用账号隔离

沿用现有 PostgreSQL 服务，不引入其他数据库。
`DATABASE_URL` 指向平台库和专用平台账号；`AGENT_DATABASE_URL` 指向独立 Agent 库和另一个专用账号。
两个应用账号均不是管理员，不具备 superuser、createdb、createrole、replication、bypassrls 或其他角色成员资格。
bootstrap 管理员保留数据库与 schema 运维权限，不作为应用连接账号。

全新安装时，由引导管理员先创建这两个独立数据库和受限登录账号，撤销 PUBLIC CONNECT，分别授予本库 CONNECT 及 public schema USAGE/CREATE；然后用各自应用 DSN 运行项目初始化。Compose 创建的 `showdoc` 是引导管理员，不可直接填作应用账号。下述复制工具用于已有共享库的迁移，要求现有平台九表和官方 Agent 六表完整，不用于凭空创建业务数据。

## 先审查，后切换

先停止 API、治理 Worker 及其他写入进程，备份现有数据库、产物目录和加密密钥。
在受控配置中准备两条应用 DSN，密码会用于创建尚不存在的角色；工具不改写 `.env`、不输出 DSN 或密码。
管理员 DSN 通过 `--admin-url` 单独提供，勿将其留作运行配置。

```bash
.venv/bin/python -m scripts.isolate_agent_postgres --admin-url "$ISOLATION_ADMIN_URL"
```

默认仅以只读事务盘点。核对库名、角色、平台九表行数、官方 Agent 六表行数和内容校验和及准备计划。
当前只支持项目已用的 public schema：官方 Saver 四表，以及无向量索引的 Store 两表。
遇到额外表、不同 SDK schema、向量 Store、历史第三方表授权或已存在的高权限账号会拒绝，需人工核对，不能丢弃未知数据。

经独立审查并明确批准生产切换后，才执行：

```bash
.venv/bin/python -m scripts.isolate_agent_postgres --admin-url "$ISOLATION_ADMIN_URL" --apply
```

apply 创建或检查两个专用账号、创建 Agent 库，撤销两库的 PUBLIC CONNECT 和交叉账号权限，
将平台九表及其序列权限交给平台账号；旧 Agent 原件归 bootstrap 管理员保管。
Agent 目标使用官方 `PostgresSaver.setup()`、`PostgresStore.setup()` 初始化。
checkpoint、blob、pending writes 和 Store 数据通过 psycopg 原生二进制 COPY 复制，不重建或重放 Agent。
复制后在同一目标事务中逐表核对行数和内容；非空目标不同则拒绝，不覆盖或清空。
源 Agent 数据不删除。重复执行仅允许空目标或完全一致的目标。

角色、数据库和 SDK schema 准备会先提交，不能与 CREATE DATABASE 放在一个事务内。
复制失败只回滚目标数据事务；失败报告明确列出已完成的准备步骤，不能把失败当作已切换。
修正问题后可重新盘点，再决定是否继续。不要在应用产生新目标状态后用旧源覆盖它。

启动新版本后核对账号登录、采集任务、聊天历史、待审批恢复和文件记忆。
工具会实测两应用账号本库读取成功、双向跨库 CONNECT 被拒绝，以及平台账号不能读取旧 checkpoint。
两业务库之外的维护库或其他数据库不在本工具的授权范围；
若要求整个集群只允许账号登录指定库，还需运维统一配置 pg_hba 或集群 CONNECT 权限基线。

**原库 checkpoint/Store 表仅作为管理员归档保留。物理清理必须在备份、切换验收和最终人工审查后单独进行；本工具不 DROP 源表。**
