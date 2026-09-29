import os

import aiosqlite
from langchain.agents import create_agent
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.utils import init_chat_model
from app.utils.context import AgentContext
from .prompt import PRICE_RESEARCHER_PROMPT
from .tools import tools_price_researcher

AGENT_METADATA = {
    "name": "price_researcher",
    "description": "정확한 상품 모델을 기준으로 네이버쇼핑·다나와 등의 가격과 구매 조건을 검증하는 전문 에이전트",
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
        tools=tools_price_researcher,
        system_prompt=PRICE_RESEARCHER_PROMPT,
        checkpointer=checkpointer,
        context_schema=AgentContext,
    )