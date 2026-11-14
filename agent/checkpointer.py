"""Official LangGraph PostgreSQL persistence; checkpoints are not knowledge documents."""
import os

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver


def make_checkpointer():
    return PostgresSaver.from_conn_string(os.environ['DATABASE_URL'])


def async_checkpointer():
    return AsyncPostgresSaver.from_conn_string(os.environ['DATABASE_URL'])


def initialize_checkpoints():
    with make_checkpointer() as saver:
        saver.setup()
