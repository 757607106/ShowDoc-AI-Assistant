# ContextDB 操作边界

开发使用官方 `ctxdb 1.1.0`，配置档为 `codex`：

```bash
ctxdb status --agent=codex --json
ctxdb ping --agent=codex
ctxdb kb --help
```

已完成官方 CLI setup 与 Codex HTTP MCP 配置，配置前备份保存在 `downloads/dev-setup-backup/`。开发 MCP 仅启用知识读取工具；Codex 重启后加载。自动采集、召回和 Skill 演进已关闭，Hook 信任没有自动开启。

平台后端使用成员自己的服务端加密凭据调用官方 REST；deepagents 的知识工具只通过官方 MCP 装载。CLI 不参与运行时。`user_id` 等业务标识不会切换 ContextDB 成员，成员身份始终由其密钥确定。

当前契约与未开放能力见 [架构清单](../architecture/agent-platform.md) 和 [机器可读验证](../architecture/reports/contextdb-capabilities.json)。旧版文档中的云端任务/checkpoint 与猜测 Wiki 版本方式已废弃。

排查任务应检查 Docker PostgreSQL 和 Worker；排查知识处理应查看官方文档详情、评审详情和事件 ID；不要删除旧 `_governance` 或切换工作空间权限模式来修复平台任务。
