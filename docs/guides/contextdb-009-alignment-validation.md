# ContextDB 0.0.9 流程对齐验收

验收日期：2026-11-14（Asia/Shanghai）。本轮对齐 Wiki 关联恢复、原生库与业务空间入口、知识评审开关、批量评审和评审轮次口径。知识解析、评审、入库及 Wiki 编译继续由 ContextDB 执行。

## 实现

- 远端目标不存在、权限不足和连接状态未知分别展示；保留来源快照、历史提交和旧投递回执。
- 恢复支持关联有效的同模式库，或仅重建当前 Wiki 目标并重新投递最近已提交快照。`POST /api/kb/spaces/<scope>/submit` 可指定 `target_modes: ["wiki"]`，未指定时保持原有行为。
- 新目标尚未收到历史资料时显示待重新提交，不沿用旧回执宣称入库成功，也不向旧目标发起处理重试。
- 原生知识库入口复用同一知识工作区；关联库转入对应业务空间。当前 ID 优先于历史别名，历史归属有歧义时不任意重定向。
- 旧库书签保留空间归属；切换到重建后的库时清理旧页面、文档、目录和路径定位。当前有效库的深链保留定位参数。图谱文档使用 `target=graph`，避免读取 Wiki 库中的同名资料。
- 文档深链仅由嵌入文档列表负责预览，避免重复打开两个原文抽屉。
- 评审设置提供总开关，保存后回读；切库时拒绝迟到的设置响应。开关具备名称、状态、键盘焦点及空格/回车操作。
- 批量评审复用官方接口，限当前页 1～50 条，校验生命周期与权限；切库、筛选或翻页清空选择。请求受理后逐条回读官方状态，保留单项失败或结果待确认，不自动重试写请求。
- 切库后加载失败会清空旧评审行；旧请求迟到也不能恢复其他库的可操作数据。
- `max_rewrite_iterations` 展示为“最多评审轮次”，N 轮最多重写 N−1 次。Wiki 提示说明自动编译通常无需逐条批准，并要求核对正式正文。

## 真实默认空间恢复

使用当前管理员绑定的 ContextDB 成员身份，通过本地 HTTP API 创建仅 Wiki 的同步任务，再使用项目现有 Worker 执行一次任务。

| 项目 | 实际结果 |
| --- | --- |
| 旧 Wiki ID | `e42e30ad-607d-4b9b-93be-9ec1cbb18598`，官方返回不存在 |
| 恢复后 Wiki ID | `61055604-801a-4a28-9fcb-f8eb79d47f7e` |
| 同步任务 | `c5417911-2c88-4f81-8b21-6dbefb3301d8`，仅 Wiki |
| 重新投递 | 124 份，0 失败 |
| 官方入库终态 | 124 `succeeded` |
| 官方 Wiki 终态 | 124 `compiled` |
| Wiki 阅读 | 索引返回真实主题，成功打开“数据库连接池配置”的正式正文和来源 |
| 旧回执 | 124 条归档 |
| 图谱投递记录 | 124 条记录在恢复前后逐字段哈希一致 |

本轮恢复使用最近一次已提交快照，不包含之后新增但尚未提交的资料。保留原有 HTML/Markdown 投递格式；入库和 Wiki 编译成功不等于所有资料均经过文档评审。旧库独有、未保存到来源快照的人工主题修订无法由此重建。

## 真实评审与浏览器验证

新建独立临时零编译库 `alignment-009-5e83ca8c86`，与业务库隔离：

1. 关闭评审上传一份 Markdown：入库 `succeeded`，无评审记录。
2. 开启评审、关闭重写，初始评审轮次设为 1、自动通过阈值设为 1：另两份 Markdown 进入 `pending_review`，两条评审均为 `pending_human`。
3. 浏览器勾选两条记录，执行“批量通过原文”：逐项显示已受理，回读均为 `approved`；两份文档最终均 `succeeded`。
4. 浏览器验证评审总开关的鼠标、空格及回车操作，保存关闭并刷新确认；再开启保存，HTTP 回读为 `review_enabled=true`。
5. 设置三轮并保存，刷新及 HTTP 回读均为 `max_rewrite_iterations=3`，界面显示最多重写两次。
6. 原始旧 Wiki 链接及带失效页面定位的旧链接均到达恢复后的业务空间；旧定位被清理。
7. 当前图谱文档深链保留正确的库归属，并且只有一个原文预览。

该临时库的最终状态、清理结果和默认空间恢复的结构化证据见 [验收 JSON](../../downloads/evaluations/contextdb-009-alignment.json)。未对业务资料执行批量拒绝、删除或撤回回归。

浏览器截图位于 [验收目录](../../output/playwright/contextdb-009-alignment/)：`wiki-restored.jpg`、`wiki-page.jpg`、`batch-review.jpg`、`review-settings.jpg`、`graph-source.jpg`。

## 自动化验证

- 后端全量：323 passed、1 skipped；保留既有 Docling/numpy 的 56 条警告。
- 最终前端全量：2867 passed、1 skipped、0 failed。
- `npm run type-check`：通过。
- `npm run build-only`：通过，保留大 chunk 提示。
- `git diff --check`：通过。

新增回归覆盖目标失效恢复、定向提交、旧回执归档、历史 ID 归属、跨用户隔离、当前 ID 优先、历史歧义、旧资源定位清理、图谱来源归属、重复预览、批量逐项结果、权限/生命周期限制、切库失败和迟到响应，以及设置归属与键盘操作。

## 官方依据

- [知识库与编译模式](https://g.alicdn.com/rdsai/contextdb-doc/0.0.9/contextdb-documentation.html#/knowledge-bases)
- [知识评审动作与批量接口](https://g.alicdn.com/rdsai/contextdb-doc/0.0.9/contextdb-documentation.html#/api-review-decide)
- [知识库评审设置与轮次](https://g.alicdn.com/rdsai/contextdb-doc/0.0.9/contextdb-documentation.html#/api-review-policy)
- [Wiki 阅读、编译与正式修订](https://g.alicdn.com/rdsai/contextdb-doc/0.0.9/contextdb-documentation.html#/knowledge-wiki)
