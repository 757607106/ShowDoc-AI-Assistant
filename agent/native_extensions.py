"""Trusted Python registrations for SDK options that cannot be sent as JSON.

Factories may supply native middleware (including RubricMiddleware) and compiled
subagents. Beta profiles use deepagents.profiles.register_harness_profile and
register_provider_profile in trusted server startup code, not config uploads.
"""
import re

from deepagents import DeepAgentState

from governance.store import StoreError

_factories = {}
_OPTIONS = {'subagents', 'middleware', 'state_schema', 'context_schema', 'cache', 'debug', 'name', 'response_format'}


def register_native_extension(name, factory):
    """Register trusted code that enforces context identity, authorization and policy.

    Compiled runnables own their HITL/permissions; caches must be scoped to the
    supplied owner and authorization context. Neither is inherited automatically.
    """
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', name) or not callable(factory):
        raise ValueError('Native extension requires a name and a callable factory')
    if name in _factories:
        raise ValueError('Native extension is already registered')
    _factories[name] = factory


def native_options(name, context):
    if name is None:
        return {}
    if name not in _factories:
        raise StoreError('原生服务端扩展未注册', 400)
    value = _factories[name](context)
    if not isinstance(value, dict) or set(value) - _OPTIONS:
        raise StoreError('原生扩展不能替换身份、工具、后端或持久化配置', 400)
    schema = value.get('state_schema')
    if schema is not None:
        fields = getattr(schema, '__annotations__', {})
        if any(fields.get(key) != field for key, field in DeepAgentState.__annotations__.items()):
            raise StoreError('state_schema 必须继承 DeepAgentState 并保留原生通道', 400)
    for child in value.get('subagents', []):
        if not isinstance(child, dict) or 'runnable' not in child or 'graph_id' in child:
            raise StoreError('服务端子代理扩展仅接收已按当前策略编译的 runnable；异步服务尚未通过部署验收', 501)
    return dict(value)
