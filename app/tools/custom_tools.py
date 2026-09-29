"""
custom_tools.py — 사용자 커스텀 도구 모음

이 파일은 교육생 여러분이 직접 도구를 작성하는 공간입니다.
미션 가이드(missions/01_missions.md)를 참고하여 이곳에 read_user_memory 및 update_user_memory 도구를 구현하세요.
"""

import os
from langchain_core.tools import tool

USER_MD_PATH = os.path.abspath("app/database/USER.md")

@tool(parse_docstring=True)
def read_user_memory(section: str = "profile") -> str:
    """사용자의 프로필, 직업, 전문 분야, 선호 스타일, 취미 등이 기록된 USER.md 파일을 읽어옵니다.
    사용자와의 첫 인사나 개인화된 정보 조회가 필요할 때 호출하세요.

    Args:
        section: 읽을 사용자 정보 섹션입니다. 기본값은 "profile"이며, 전체 프로필을 읽을 때는 "profile" 또는 "all"을 사용하세요.
    """
    if not os.path.exists(USER_MD_PATH):
        return "[알림] 사용자 프로필(USER.md) 파일이 존재하지 않습니다."

    if section and section.lower() not in {"all", "profile"}:
        return f"[알림] '{section}' 섹션은 지원하지 않습니다. 'profile' 또는 'all'을 사용하세요."

    with open(USER_MD_PATH, "r", encoding="utf-8") as f:
        return f.read()


@tool(parse_docstring=True)
def update_user_memory(content: str) -> str:
    """사용자의 최신 프로필 정보(이름, 직업, 전문 분야, 취미, 선호 스타일 등)로 USER.md 파일을 전체 갱신(업데이트)합니다.
    
    사용자와의 대화 중 기존 정보가 변경되거나 새로운 정보가 추가되었을 때,
    기존 프로필 내용과 새로운 사실을 깔끔하게 통합하여 마크다운 텍스트로 전달하세요.

    Args:
        content: 최신 상태로 통합 정리된 전체 사용자 프로필 마크다운 텍스트
    """
    os.makedirs(os.path.dirname(USER_MD_PATH), exist_ok=True)
    
    with open(USER_MD_PATH, "w", encoding="utf-8") as f:
        f.write(content.strip())
        
    return "✅ 사용자 프로필(USER.md)이 최신 정보로 성공적으로 업데이트되었습니다."
