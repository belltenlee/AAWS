import os

import aiosqlite
from langchain.agents import create_agent
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.utils import init_chat_model
from app.utils.context import AgentContext
from .prompt import REVIEW_CATALOG_BUILDER_PROMPT
from .tools import tools_review_catalog_builder

AGENT_METADATA = {
    "name": "review_catalog_builder",
    "description": "YouTube Data API로 귀곰 채널의 영상 제목을 수집하고 제품군 카탈로그를 만드는 전문 에이전트",
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
        tools=tools_review_catalog_builder,
        system_prompt=REVIEW_CATALOG_BUILDER_PROMPT,
        checkpointer=checkpointer,
        context_schema=AgentContext,
    )