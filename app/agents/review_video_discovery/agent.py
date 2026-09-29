import os

import aiosqlite
from langchain.agents import create_agent
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.utils import init_chat_model
from app.utils.context import AgentContext
from .prompt import REVIEW_VIDEO_DISCOVERY_PROMPT
from .tools import tools_review_video_discovery

AGENT_METADATA = {
    "name": "review_video_discovery",
    "description": "귀곰 공식 리뷰 채널에서 물품 계열과 관련된 영상 후보와 출처를 조사하는 전문 에이전트",
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
        tools=tools_review_video_discovery,
        system_prompt=REVIEW_VIDEO_DISCOVERY_PROMPT,
        checkpointer=checkpointer,
        context_schema=AgentContext,
    )