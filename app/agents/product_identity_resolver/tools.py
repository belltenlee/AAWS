from app.tools.common import file_read, file_writer, web_fetch, web_search

tools_product_identity_resolver = [file_read, file_writer, web_search, web_fetch]

__all__ = ["tools_product_identity_resolver"]