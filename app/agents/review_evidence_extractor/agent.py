import os

import aiosqlite
from langchain.agents import create_agent
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.utils import init_chat_model
from app.utils.context import AgentContext
from .prompt import REVIEW_EVIDENCE_EXTRACTOR_PROMPT
from .tools import tools_review_evidence_extractor

AGENT_METADATA = {
    "name": "review_evidence_extractor",
    "description": "귀곰 리뷰의 자막과 공개 근거에서 제품, 순위, 추천 이유를 출처와 함께 추출하는 전문 에이전트",
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
        tools=tools_review_evidence_extractor,
        system_prompt=REVIEW_EVIDENCE_EXTRACTOR_PROMPT,
        checkpointer=checkpointer,
        context_schema=AgentContext,
    )