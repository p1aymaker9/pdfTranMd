from __future__ import annotations

import os

import fitz
import markdown

from pdf_tran_md.core.text import split_inline_ordered_lists_for_preview
from pdf_tran_md.ui.styles import get_markdown_css


PAGE_WIDTH = 595
PAGE_HEIGHT = 842
PAGE_MARGIN = 42
PDF_BODY_CSS = """
@page { size: A4 portrait; margin: 0; }
body { margin: 0; }
"""


def markdown_to_html(markdown_text: str, dark_mode: bool = False) -> str:
    preview_text = split_inline_ordered_lists_for_preview(markdown_text)
    body = markdown.markdown(preview_text, extensions=["extra", "tables", "fenced_code", "toc"])
    css = get_markdown_css(dark_mode)
    return f"<html><head><meta charset='utf-8'><style>{css}</style></head><body>{body}</body></html>"


def load_markdown_html(markdown_path: str, dark_mode: bool = False) -> str:
    with open(markdown_path, "r", encoding="utf-8") as file:
        return markdown_to_html(file.read(), dark_mode=dark_mode)


def export_markdown_to_pdf(markdown_path: str, pdf_path: str) -> None:
    if not os.path.exists(markdown_path):
        raise FileNotFoundError(f"Markdown 文件不存在：{markdown_path}")

    html = load_markdown_html(markdown_path, dark_mode=False)
    story = fitz.Story(html=html, user_css=PDF_BODY_CSS)
    page_rect = fitz.Rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT)
    content_rect = fitz.Rect(
        PAGE_MARGIN,
        PAGE_MARGIN,
        PAGE_WIDTH - PAGE_MARGIN,
        PAGE_HEIGHT - PAGE_MARGIN,
    )

    def rect_function(page_number: int, filled):  # noqa: ANN001
        return page_rect, content_rect, None

    pdf = story.write_with_links(rect_function)
    try:
        os.makedirs(os.path.dirname(pdf_path) or ".", exist_ok=True)
        pdf.save(pdf_path)
    finally:
        pdf.close()
