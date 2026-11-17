# 采集文件目录契约

核对日期：2026-11-17。依据 [ContextDB 0.0.9 官方文档](https://g.alicdn.com/rdsai/contextdb-doc/0.0.9/contextdb-documentation.html#/api-listKnowledgeNodes) 的文件与目录章节，按该契约完成了存量文件节点移动与前后核对。

- `GET /v1/knowledge/nodes` 按 `knowledge_base_id` 和可选 `parent_node_id` 分页，省略父节点时列根层。业务响应包含 `items`、`total`、`parent_node`、`breadcrumbs`、`tree_revision`。
- 节点类型为 `root`、`folder`、`file`。文件的 `document_id` 与文件树 `node_id` 不同。
- `POST /v1/knowledge/nodes` 接收 `knowledge_base_id`、`display_name` 和可选 `parent_node_id`。目录允许重名；创建不是幂等操作，来源根节点必须保存映射并串行创建。
- `POST /v1/knowledge/nodes/ensure` 只接收 `document_id`，为旧文档幂等建立文件节点。它保留文档 ID 与来源路径，不会按 `file_path` 创建目录。
- `PATCH /v1/knowledge/nodes` 接收 `node_id`、`expected_tree_version` 和目标 `parent_node_id` 或新 `display_name`。版本从当前节点读取，`0` 是合法值；移动到根层须传真实根节点 ID。
- 创建、确保节点及更新响应均为 `{node, tree_revision, sync_status}`。节点更新返回 HTTP 409 时应回读节点并核实位置，不能强制覆盖版本。
- 移动保留文档 ID；目录位置更新后，检索文本可能异步同步，不代表正文重新入库。文件目录节点与 Wiki 页面目录不是同一套资源。

官方移动说明没有明确承诺 `file_path` 是否变化；同步恢复应优先使用已有文档 ID 和来源标识，而不是从树路径重建逻辑键。

采集链路统一保存 `metadata.import_directory={root_name,path}`：ShowDoc 使用真实项目名，天通与云创业版使用平台名，通用网页使用域名，文件采集使用“上传文件”。相对目录由来源目录段组成，根页为空数组。普通上传页面直接提交的大文件不经过爬虫，仍保存到用户选择的位置。

平台保存账号、知识库、来源标识到根节点的映射；同名的不同来源不会合并，同来源重跑复用原节点。只有本次采集明确设置的根名可以改名，历史版本不能覆盖当前目录配置。文件修订继承原来源目录，Wiki 目录不参与同步。

存量整理使用 `scripts/repair_import_directories.py`。默认仅生成计划，`--apply` 执行节点移动，不重新上传或提交评审：

```sh
.venv/bin/python -m scripts.repair_import_directories \
  --owner-id <平台账号ID> --kb-id <知识库ID> \
  --report downloads/migrations/import-directories.json --apply
```

省略 `--kb-id` 时检查该账号所有已有同步映射，已删除的知识库只记录跳过，不重建。报告保留逐文档结果，并比对文档 ID、评审记录身份和 Wiki 目录。执行后还应回读真实文件树核对完整相对路径；目录移动不会替代入库或编译状态检查。
