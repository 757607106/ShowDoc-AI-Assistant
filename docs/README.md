> 当前平台入口：[安装与运行](../README.md) · [ContextDB + WeKnora 当前架构和验收边界](architecture/agent-platform.md)。早期 Docling/云端运行状态设计仅作为历史记录，见 [归档区](#归档)。

# 项目文档

文档按用途分组：现行架构与工程规范、操作指南、带日期的验证报告，以及不再指导当前实现的归档记录。

## 架构与边界

- [ContextDB + WeKnora 当前架构和验收边界（总览）](architecture/agent-platform.md)
- [ContextDB 官方能力与项目需求对照](architecture/contextdb-capability-fit.md)
- [Wiki 与 WeKnora 界面复用、图谱接口边界](architecture/contextdb-weknora-ui.md)
- [Wiki API 边界核查](architecture/contextdb-wiki-support.md)
- [Wiki 编译器接管准入与独立资源实测](architecture/contextdb-wiki-compiler-readiness.md)
- [多平台爬虫架构](architecture/multi-platform-crawler-refactor.md)

## 工程规范

- [工程结构与命名规范](engineering/project-structure.md)

## 操作指南

- [异步 Agent 运行服务（Aegra/Valkey）](guides/async-agent-runtime.md)
- [Agent Postgres 隔离迁移](guides/agent-postgres-isolation.md)
- [导入目录契约](guides/import-directory-contract.md)
- [ContextDB CLI 开发机操作](guides/contextdb-operations.md)
- [ShowDoc 验证码配置](guides/qwen-captcha.md)

## 带日期的验证报告

- [Agent 前后端精准修复与对齐记录（2026-11-17）](architecture/reports/agent-repair-alignment-20261117.md)
- [Deep Agents + ContextDB 最终方案及本轮精准修复（2026-11-17）](architecture/reports/deepagents-contextdb-final-plan-20261117.md)
- [架构整改总报告（2026-11-16）](architecture/reports/architecture-remediation-final-20261116.md)
- [设置接入审计（2026-11-17）](architecture/reports/settings-integration-audit-20261117.md)
- [知识库三模式与评审对齐记录（2026-11-16）](architecture/reports/contextdb-knowledge-alignment-20261116.md)

机器验证 JSON 快照已删除；报告正文保留事实与结论。

## 归档

早期设计、日期性验证日志与被取代的需求文档，仅作历史证据，不指导当前实现：

- [ShowDoc 初始需求](archive/initial-showdoc-requirements.md)
- [数据治理与质量管道需求](archive/data-quality-pipeline.md)
- [历史版 ShowDoc 说明](archive/showdoc-legacy-readme.md)
- [Agent 官方源码对齐审计（历史）](archive/agent-official-alignment-audit.md)
- [Agent 高级能力对齐记录（历史）](archive/agent-advanced-alignment.md)
- [Agent 真实环境验收记录（历史）](archive/agent-real-acceptance.md)
- [Agent 交互验证边界（历史）](archive/agent-interaction-validation.md)
- [ContextDB 0.0.9 对齐验收（历史）](archive/contextdb-009-alignment-validation.md)
- [ContextDB 阶段 0 集成笔记（历史）](archive/contextdb-integration-notes.md)
- [Docling 接入依据（历史）](archive/docling-governance.md)
- [治理验证日志（历史）](archive/governance-validation.md)

根目录 [README.md](../README.md) 只保留安装、启动、核心功能和常用命令。浏览器运行时的退役边界并入 [agent-platform](architecture/agent-platform.md)；治理运行与恢复的现行说明同样见该文档与根 README。
