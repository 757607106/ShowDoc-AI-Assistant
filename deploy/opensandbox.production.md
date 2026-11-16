# OpenSandbox 生产部署与待验收清单

2026-11-16：用户确认暂未提供 Linux/Kata 或 Kubernetes 环境，本轮交付部署路线与验收条件，不将本机 runc 测试计为生产安全验收。

## 官方原生部署路线

沿用 OpenSandbox `release-1.2.1`、官方 Python SDK 及项目锁定的 Deep Agents 适配器；使用官方 Kubernetes controller、Lifecycle Server 与 ingress gateway，选择已安装 Kata 的节点和 `kata-qemu` RuntimeClass。所有文件解析与 Agent 执行指向同一受控服务，不挂载宿主目录、Docker socket 或平台凭据，不改用宿主 Shell。

按该版本[官方 Kubernetes 部署示例](https://github.com/opensandbox-group/OpenSandbox/blob/release-1.2.1/docs/guides/secure-container.md#multiple-runtime-profiles-on-kubernetes)安装 CRD/controller、Lifecycle Server 和独立 Gateway chart。不能仅设置 `server.gateway.enabled=true` 就认为 Gateway 已部署。配置中的 workload namespace、Gateway 目标 namespace 和客户端实际可达地址必须一致；TLS、API key、签名密钥均使用集群 Secret。

在官方 Server chart 的 `configToml` 中使用以下原生配置段，其他参数按该版本官方示例补齐：

```toml
[runtime]
type = "kubernetes"
execd_image = "opensandbox/execd:release-1.2.1"

[secure_runtime]
type = "kata"
k8s_runtime_class = "kata-qemu"

[egress]
image = "opensandbox/egress:release-1.2.1"
mode = "dns+nft"

[store]
type = "postgresql"
```

控制服务通过官方 `OPENSANDBOX_STORE_POSTGRESQL_DSN` 连接独立 control 数据库和受限账号，不复用平台或 Agent 账号。应用的 `DATABASE_URL` 与 `AGENT_DATABASE_URL` 仍分别指向平台与 Agent 专库。

Gateway 必须按[官方 secure access 指南](https://github.com/opensandbox-group/OpenSandbox/blob/release-1.2.1/docs/guides/secure-access.md)启用签名校验，限制执行端点直达；配置一致的 Server/Gateway signing key ring。应用 `OPEN_SANDBOX_DOMAIN` 指向 Lifecycle Server 地址，执行数据面由官方 Gateway 路由。生产接入前还须将当前开发用 `ConnectionConfigSync(use_server_proxy=True)` 改为官方 Gateway 数据面配置，并在 Agent 和附件沙箱 `create()` 传入 `secure_access=True`；该组合须在目标环境实测。不能将 Docker 后端不支持的参数偷偷忽略。

选择 Kata 是为了保留当前默认拒绝出网策略：此版本官方明确拒绝 `secure_runtime.type="gvisor"` 与请求 `network_policy` 并用，返回 HTTP 400；不能为运行成功去掉网络策略。若实际集群选择其他方案，必须重新按[官方运行时兼容说明](https://github.com/opensandbox-group/OpenSandbox/blob/release-1.2.1/docs/guides/secure-container.md)验收。

将本项目 `docker/attachment-parser.Dockerfile` 构建为受控私有镜像，预下载 OCR 模型，部署到集群节点可拉取的镜像仓库；当前代码固定使用 `showdoc-attachment-parser:local`，生产须在部署前将该固定镜像引用替换为已审查的仓库 digest，并同样锁定 Agent 执行镜像。不要添加供用户输入任意解析镜像或宿主路径的表单。

## 上线前必须通过

| 范围 | 验收行为与证据 | 通过条件 |
| --- | --- | --- |
| 运行时 | 查看实际 Pod `runtimeClassName`、节点 Kata 配置与执行环境 | 确认运行于 Kata；缺失 RuntimeClass/运行时必须拒绝启动，不能回退 runc |
| Gateway | 外部无签名、失效签名、过期 token、直连 Pod/execd 端口测试 | 全部拒绝；合法签名可执行，签名密钥不进入执行容器 |
| 宿主隔离 | 检查 Pod volumes、mounts、capabilities、privileged、service-account token | 无宿主目录/socket/平台凭据，非 privileged，无多余 capabilities；平台凭据和 PG 连接串在沙箱不可见 |
| 网络 | 沙箱访问公网、云元数据地址、平台 API、三类数据库与集群控制端口 | 默认拒绝；仅管理员审查的必要白名单例外可达；DNS/TCP/UDP 按实际 CNI 验证 |
| 文件与 Shell | 两用户两会话各写入随机路径，二进制往返，`execute` 与 PTY | 文件不串读；执行仅在对应环境；viewer/read_only 无执行权限；confirm 审批前无副作用 |
| 上传解析 | TXT、DOCX、PPTX、XLSX、文本/扫描 PDF、有效与损坏图片 | 固定非 root 镜像、离线解析；损坏文件明确失败；宿主无解析和执行回退 |
| 生命周期 | 正常结束、取消、SDK 错误、API 重启、TTL、节点重启后检查资源 | 临时解析环境销毁；会话环境按协议重连/销毁；过期实例按实测时钟回收，无孤儿资源 |
| 资源 | 内存、CPU、PID、输出大小、并发与配额压力 | 限额实际生效，超限明确失败，不拖垮控制服务或其他用户 |
| PostgreSQL | 本库读写、双向跨库连接、管理员权限与 checkpoint 恢复 | 应用账号无高权限，跨库拒绝；历史/待审批/Store 恢复一致 |
| 原前端 | 原版 Tool、Shell、审批、恢复、附件、错误状态 | 原 UI 能显示真实结果与失败；无自建控件或假完成状态 |

保留原始配置、镜像 digest、环境版本、测试命令、脱敏结果及资源清理证明。安全测试只覆盖实际部署及已测边界，不承诺绝对不存在逃逸。
