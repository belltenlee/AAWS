import os

import aiosqlite
from langchain.agents import create_agent
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.utils import init_chat_model
from app.utils.context import AgentContext
from .prompt import PRODUCT_IDENTITY_RESOLVER_PROMPT
from .tools import tools_product_identity_resolver

AGENT_METADATA = {
    "name": "product_identity_resolver",
    "description": "리뷰의 제품명과 제조사·판매 모델 및 옵션을 근거 기반으로 대응하는 전문 에이전트",
}


async def create_agent_executor():
    llm = init_chat_model(model="gemini-3.8-flash", temperature=0.0)

    db_dir = "app/database"
    os.makedirs(db_dir, exist_ok=True)
    checkpoints_path = os.path.join(db_dir, "checkpoints.db")

    conn = await aiosqlite.connect(checkpoints_path, check_same_thread=False)
    checkpointer = AsyncSqliteSaver(conn)
    await checkpointer.setup()

    return create_agent(
        model=llm,
        tools=tools_product_identity_resolver,
        system_prompt=PRODUCT_IDENTITY_RESOLVER_PROMPT,
        checkpointer=checkpointer,
        context_schema=AgentContext,
    )