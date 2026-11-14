"""deepagents 官方 Harness 构建:ChatOpenAI(BYOK→百炼,回退专属端点)+ ContextDB checkpointer。"""
import os

from langchain_openai import ChatOpenAI

from agent.checkpointer import make_checkpointer
from agent.tools import make_governance_tools, load_knowledge_mcp_tools

SYSTEM_PROMPT = """你是企业级知识治理平台的智能助手,服务数据治理与知识消费两个域。

工具使用原则:
- 不读取或检索历史 `_governance` 运行记录库;平台溯源请使用平台工具。
- 知识访问直接使用当前已装载的 ContextDB 官方 MCP 工具，保留工具原始参数和真实资源 ID；工具失败时说明错误，不自行改用 REST、网页或本地文件检索。
- 普通知识问题优先 knowledge.search；查找 Wiki 页面用 knowledge.wiki_search，它返回的是导航摘要，不是完整原文。
- 明确询问实体关系，或原文证据不足且需要关联信息时，可在同一次执行中按需调用 knowledge.list_graph_entities、knowledge.get_graph、knowledge.list_entity_chunks；先查实体、有限展开，再读来源原文。没有装载的工具不可假设可用。
- 原文证据已足够时停止追加检索。图谱的 graph_context、graphrag 合成描述和 Wiki 合成章节只能辅助理解，不能冒充原文证据；需要原文引用时继续通过官方工具取得实际切片。
- 遵守返回的 truncated、note 和来源缺失信息；有限结果不能证明关系不存在。指定 document_ids 时，图增强信息仍可能来自同库其他文档，必须核对原文范围。
- 需要平台治理信息(发布版本、文档版本溯源)时,使用治理溯源工具;
- 回答知识问题时给出本轮成功工具调用中实际读到、且支持相邻结论的原文出处；历史回答或工具参数中的 ID 不是本轮证据。不确定或证据不足就明说。
- 原文引用使用 <kb chunk_id="工具返回的真实切片ID" kb_id="该切片所属知识库ID" />，紧跟其支持的结论；标题由系统补全。不得编造 ID、用标题或序号代替 ID、或拿同一文档的其他切片支持未经核实的内容。此标签协议仅用于回答，不改变官方工具参数。

沟通风格:结论先行、简明中文;引用知识库证据时注明来源。"""


def _fallback_base_url():
    return (os.getenv('DASHSCOPE_API_URL') or 'https://llm-rtc5v8cnt0umugh9.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/chat/completions') \
        .rstrip('/').removesuffix('/chat/completions')


def build_model():
    """BYOK 路由:百炼公开端点优先,未配置时回退现有专属端点。"""
    bailian_key = os.getenv('BAILIAN_API_KEY', '').strip()
    if bailian_key:
        return ChatOpenAI(
            model=os.getenv('AGENT_MAIN_MODEL', 'qwen-max'),
            api_key=bailian_key,
            base_url=os.getenv('AGENT_BAILIAN_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1'),
            temperature=0, timeout=180, max_retries=2,
        )
    key = os.getenv('DASHSCOPE_API_KEY') or os.getenv('QWEN_API_KEY', '')
    model = os.getenv('AGENT_MAIN_MODEL', 'qwen-max')
    fallback_model = os.getenv('AGENT_FALLBACK_MODEL') or 'qwen-plus'
    # 专属端点上未必存在 qwen-max:回退其已验证模型
    if not bailian_key and 'max' in model:
        model = fallback_model
    return ChatOpenAI(
        model=model, api_key=key, base_url=_fallback_base_url(),
        temperature=0, timeout=180, max_retries=2,
    )


async def build_agent(checkpointer, *, api_key, owner_id, role='viewer', knowledge_base_ids=()):
    from deepagents import create_deep_agent
    knowledge_tools = await load_knowledge_mcp_tools(api_key=api_key, role=role, owner_id=owner_id, knowledge_base_ids=knowledge_base_ids)
    writes = {tool.name: {'allowed_decisions': ['approve', 'reject']}
              for tool in knowledge_tools if not (tool.metadata or {}).get('readOnlyHint', False)}
    agent = create_deep_agent(
        model=build_model(),
        tools=[*make_governance_tools(api_key, owner_id, role), *knowledge_tools],
        system_prompt=SYSTEM_PROMPT + ('\n当前会话知识库 ID: '+', '.join(knowledge_base_ids) if knowledge_base_ids else '\n当前会话未选择知识库，不可访问知识库内容。'),
        checkpointer=checkpointer,
        interrupt_on=writes,
    )
    return agent
