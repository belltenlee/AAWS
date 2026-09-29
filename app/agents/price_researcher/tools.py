from app.tools.common import file_read, file_writer, web_fetch, web_search
from app.tools.navigator import (
    browse_web,
    extract_dom_skeleton,
    get_page_section,
    interact_page,
    verify_selectors,
)

tools_price_researcher = [
    file_read,
    file_writer,
    web_search,
    web_fetch,
    browse_web,
    extract_dom_skeleton,
    get_page_section,
    interact_page,
    verify_selectors,
]

__all__ = ["tools_price_researcher"]