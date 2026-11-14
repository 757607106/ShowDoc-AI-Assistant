"""Deterministic model for native SDK integration tests."""
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessageChunk
from langchain_core.outputs import ChatGenerationChunk


class StreamingModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self

    async def _astream(self, messages, stop=None, run_manager=None, **kwargs):
        message = self._generate(messages, stop=stop).generations[0].message
        yield ChatGenerationChunk(message=AIMessageChunk(content=message.content, tool_calls=message.tool_calls))


def call(name, args, identifier):
    return {'name': name, 'args': args, 'id': identifier, 'type': 'tool_call'}
