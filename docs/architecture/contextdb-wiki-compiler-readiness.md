# Wiki 编译器接管准入核查

核查日期：2026-11-14（Asia/Shanghai）。独立临时库试验及 [JSON 准入报告](contextdb-wiki-compiler-readiness.json)基于此前 0.0.8 文档，保留为历史证据；本页已依据 0.0.9 修正文档公开范围。此次 0.0.9 复核只读取业务库，没有写入业务知识库或调整编译策略。当前界面接入能力见 [Wiki 支持说明](contextdb-wiki-support.md)。

## 结果

**准入未通过，继续由 ContextDB 编译 Wiki。** 本轮不添加本地 Wiki 编译器、不增加 Worker 编译阶段或另一套 Wiki 正文存储。只有以下五项均取得可验证的官方契约并通过实测，才允许接管。

| 条件 | 本轮状态 | 证据和限制 |
| --- | --- | --- |
| 完整有效来源切片及版本标识 | available | 独立文档入库成功后，以 `limit=1` 分页读回 13/13 个非空、唯一切片；读取前后的文档 ID、`updated_at` 一致。这只证明本次有界读取，不代表跨接口事务快照。 |
| 可靠定位受影响主题页及来源 | unconfirmed | 0.0.9 已提供分组索引、根层/子目录树及官方游标，页面枚举不再依赖最多 50 条搜索。页面详情可读来源，但第三方增量编译所需的完整受影响主题及来源映射尚未验证；并非每次增量都需要全库扫描。 |
| 保存编译正文、来源、目录和链接 | unconfirmed | 正文创建、版本更新已有独立实测；0.0.9 也公开目录和页面整理。尚未确认第三方提交来源切片及页面链接等完整编译信息的写入契约，不向正文接口发送猜测字段。 |
| 页面并发保护及写后核对 | available | 更新返回版本 2；使用旧版本 1 再写被拒绝；在最多 10 秒有界重读内，新正文与版本 2 均核对一致。 |
| 隔离云端自动编译 | unconfirmed | 0.0.9 公开 pause/resume，但 pause 只阻止新摄取发起编译，不停止在途任务；resume 不补派积压。尚未建立第三方写入期间的可靠隔离保证，未对业务库调用这些动作。 |

历史 JSON 的 `ready=false`、`decision=retain_contextdb_compiler` 结论继续适用，但其中对旧文档公开范围的描述不代表当前接口目录。`unconfirmed` 表示接管所需契约和验证尚不完整，不表示服务内部绝对不存在该能力。新增阅读、整理、问题处理和编译控制接口本身不能证明可接管编译。

## 官方依据与实测边界

- 此前独立试验下载的是 [0.0.8 文档](https://g.alicdn.com/rdsai/contextdb-doc/0.0.8/contextdb-documentation.html)，SHA256 为 `beb049f44247f13b5980987f51c73259dc64bdf981a2a32c0e1d86dcdff6d34f`。其中没有 Wiki API 章节是旧版材料的事实，不能据此否定 0.0.9 接口。
- [0.0.9 Wiki 阅读](https://g.alicdn.com/rdsai/contextdb-doc/0.0.9/contextdb-documentation.html#/api-kb-wiki-read)公开索引、树、详情和摘要；本轮已对真实业务库只读验证索引、树、详情、修订差异及编译记录成功，未验证全库受影响主题的增量定位。
- [0.0.9 Wiki 编辑](https://g.alicdn.com/rdsai/contextdb-doc/0.0.9/contextdb-documentation.html#/api-kb-wiki-edit)和[目录整理](https://g.alicdn.com/rdsai/contextdb-doc/0.0.9/contextdb-documentation.html#/api-kb-wiki-organize)提供人工维护操作；人工创建页仍可被后续自动编译更新，不是第三方编译元数据的完整写入口。
- [0.0.9 编译控制](https://g.alicdn.com/rdsai/contextdb-doc/0.0.9/contextdb-documentation.html#/api-kb-wiki-compile)明确 pause 不终止已派发任务。不能把库的暂停状态当成隔离已完成的证明。
- 旧报告通过官方 MCP SDK 验证工具目录，当时 Wiki 专用工具只有 `knowledge.wiki_search`；MCP 与 DATA API 能力面不同，不能用 MCP 无工具断言 DATA API 无接口。此次没有新增 Agent 工具、修改其 Schema 或以 REST 包装替代 Agent 知识工具。

首次即时读回曾返回新版本号和旧正文；增加有界重读后，新正文验证通过。因此不能仅凭更新响应或版本号判断正文已经可读。另在独立资料上传后观察到官方编译继续合并同库页面内容；这不能证明所有页面的行为，但足以说明不能假设人工创建的页面天然隔离于云端编译。

临时知识库包含文档时，删除库会被拒绝。探测脚本只删除本次创建的文档，等待异步删除完成后再删除临时库，并从完整可读库列表确认其消失。本轮三次诊断涉及的独立库均已清理，最后核对剩余资源为 0。

## 复现

以下脚本仍固定读取 0.0.8 文档，用于复现旧报告流程，不覆盖 0.0.9 全部契约；更新脚本前不要把新输出当成当前完整能力报告。默认只读，不创建云端资源：

```bash
.venv/bin/python -m scripts.contextdb_probe --wiki-compiler
```

显式创建并清理独立测试资源，验证切片和页面读写：

```bash
.venv/bin/python -m scripts.contextdb_probe --wiki-compiler --write
```

默认输出本专项 JSON，不覆盖既有 `contextdb-capabilities.json`。报告只保存能力状态、计数、文档摘要和清理标识，不保存密钥、源文正文或预签名下载地址。

默认无云端请求的回归验证：

```bash
.venv/bin/pytest -q tests/test_contextdb_probe.py
```

历史专项 13 项通过，覆盖只读不写、正文 CAS 不能单独授权接管、异步读回、完整分页、重复切片、来源中途变化、待审不编译、错误脱敏和异步资源清理。本轮原生 Wiki 后端回归 81 项也包含这些检查；0.0.9 的隔离读写验证见 [Wiki 支持说明](contextdb-wiki-support.md)。未测试本地 Wiki 生成质量或 Worker 编译恢复，因为接管前提尚未成立。
