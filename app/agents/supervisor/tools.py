"""
Supervisor Agent Tools (Trainee Mission 03 & 04)
===============================================================================
하위 전문 에이전트(Scraper 등)를 호출하는 invoke_sub_agent 도구 및
Supervisor가 사용하는 전체 도구 목록(tools_supervisor)을 정의합니다.
===============================================================================
"""

import asyncio
from typing import List
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage


from app.tools import supervisor_tools
from app.tools.plan import enter_plan, exit_plan, task_create, task_list, task_update
from app.tools.common import file_read, file_writer, glob_search, grep_search, file_edit, web_search
from app.agents.scraper import create_agent_executor as create_scraper_executor
from app.utils.message_utils import normalize_content

# =============================================================================
# 1. invoke_sub_agent Pydantic 스키마 및 도구 정의 (Mission 03)
# =============================================================================
# TODO: missions/03_missions.md [2단계]를 참고하여
#       InvokeSubAgentInput 스키마와 invoke_sub_agent 도구를 구현하세요.
#
class InvokeSubAgentInput(BaseModel):
    task_instruction: str = Field(
        description="하위 에이전트에게 내릴 명확하고 구체적인 작업 지시문"
    )
    target_file_list: List[str] = Field(
        default_factory=list, 
        description="하위 에이전트가 참조하거나 생성할 대상 파일 경로 목록"
    )
    subagent_role: str = Field(
        default="scraper", 
        description="작업을 수행할 전문 에이전트 역할 (기본값: 'scraper')"
    )

@tool(args_schema=InvokeSubAgentInput)
async def invoke_sub_agent_mission_3(task_instruction: str, target_file_list: List[str] = [], subagent_role: str = "scraper") -> str:
    """Forks an isolated, sandboxed sub-agent with a dedicated worker persona to execute focused web scraping, discovery, or data analysis tasks.

    The sub-agent operates in an isolated ReAct loop, writes detailed artifacts directly to disk, and returns only a concise 5-line summary report.

    Args:
        task_instruction: Specific task directive for the sub-agent.
        target_file_list: List of file paths for the sub-agent to inspect or write.
        subagent_role: Role persona assigned to the sub-agent.

    Returns:
        A formatted `[TASK REPORT]` string containing Status (SUCCESS/BLOCKER), Target files, Artifacts Created, Summary, and Issues.
    """

    scraper = await create_scraper_executor()

    file_list_str = ", ".join(target_file_list) if target_file_list else "None"

    # 🌟 [3-Layer Architecture] 범용 Sub-Agent Protocol Overlay 주입
    prompt = f"""[SUB-AGENT MODE - STRICT PROTOCOL]
You are operating as a sub-agent under a Main Agent. You MUST follow these rules:
1. NO greetings or conversational responses. Execute the task immediately.
2. Context & Plan: If a plan is shared, refer to it to understand the broader context.
   Do NOT modify the plan yourself. If adjustments are needed, propose them in your report.
3. On ANY blocker (site blocked / selector failure / access denied):
   STOP immediately and return EXACTLY:
   [BLOCKER: <concise reason>]
4. On success: write all detailed results to disk first, then return EXACTLY:
   [TASK REPORT]
   - Status: SUCCESS
   - Target Files: {file_list_str}
   - Artifacts Created: <created file paths>
   - Summary: <1-2 sentence core finding>
   - Issues: None (or proposed plan adjustments)
══════════════════════════════════════════════════════════
Target Files: {file_list_str}
Instruction: {task_instruction}"""
    
    config = {"configurable": {"thread_id": f"sub_{int(asyncio.get_event_loop().time() * 1000)}"}}
    
    res = await scraper.ainvoke(
        {"messages": [HumanMessage(content=prompt)]},
        config=config
    )

    
    return normalize_content(res["messages"][-1].content)


# =============================================================================
# 2. Supervisor 도구 바인딩 목록 (tools_supervisor)
# =============================================================================
# TODO: invoke_sub_agent 도구를 구현한 후 아래 리스트에 추가하세요.
#       (Mission 04에서는 app.tools.supervisor_tools의 프로덕션 비동기 도구로 교체할 수 있습니다.)

tools_supervisor = [
    # Planning & Task Board (5종)
    enter_plan, exit_plan, task_create, task_list, task_update,
    # 공용 파일/검색 도구 (6종)
    file_read, file_writer, file_edit, glob_search, grep_search, web_search,
    # 구현한 sub_agent_as_tool
    # invoke_sub_agent,
    supervisor_tools.invoke_sub_agent,
    supervisor_tools.list_sub_agents,
    supervisor_tools.get_sub_agent_job_status,
]

__all__ = ["tools_supervisor"]
