# 采集治理运行

当前平台的安装、Docker PostgreSQL、账号初始化、采集发布、双库同步及迁移命令统一见 [项目 README](../../README.md)。

任务、来源映射、会话和 checkpoint 保存在 PostgreSQL；知识评审、Wiki 和图谱保存在 ContextDB。平台不再提供长期记忆、记忆整理或记忆晋升；Worker 不再写入 `_governance`，也不在本地解析、切片或执行语义评分。

任务状态区分采集完成、双库上传已提交、部分失败。知识何时生效必须查看官方评审/入库状态；图谱构建单独显示，Wiki 编译未返回状态时不推断完成。

图谱启用后，历史文档不会自动补建。在知识库“治理进度”中对已入库但未构建的来源执行“构建图谱”；失败时执行“重试图谱构建”。提取事件成功后，可在图谱页使用“更新全库图谱”归并已有提取结果。全库更新需要写权限，受理后跟踪官方事件；未派发通常表示已有任务或暂无可处理结果，不能重复提交来加速。此链路直接调用 ContextDB，不依赖本地采集 Worker。Wiki 与图谱前端复用及接口差异见 [对照说明](../architecture/contextdb-weknora-ui.md)。

爬虫和文件上传在完整采集成功后自动提交 ContextDB；采集不完整先重试，自动提交失败时在资料任务中补交。旧任务不会因升级被批量自动提交。知识库默认打开 Wiki，知识评审默认打开评审队列；“来源资料”独立入口已移除，本地原件和历史快照仍供恢复与追溯。

官方流程是来源文档进入 Wiki 模式知识库，按格式及评审设置完成评审、入库，再编译主题页；这些步骤各有独立状态。Wiki 页编辑维护主题内容，源资料修订通过知识评审或文档更新接口提交，两者不会互相回写。[官方 Wiki 指南](https://g.alicdn.com/rdsai/contextdb-doc/0.0.8/contextdb-documentation.html#/knowledge-wiki)与[知识评审指南](https://g.alicdn.com/rdsai/contextdb-doc/0.0.8/contextdb-documentation.html#/knowledge-review)分别说明这两个阶段。

生产迁移前备份 PostgreSQL、`.env` 加密密钥与产物目录。旧 `_governance` 在迁移核对后继续只读保留。
