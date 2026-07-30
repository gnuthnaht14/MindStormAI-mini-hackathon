from __future__ import annotations

import re
from pathlib import Path

import pymupdf


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "sample" / "demo_lesson.md"
OUTPUT = ROOT / "sample" / "demo.pdf"
FONT_PATH = Path(r"C:\Windows\Fonts\arial.ttf")


def markdown_sections(text: str) -> list[tuple[str, str]]:
    cleaned = text.replace("# AI20K Build Phase — Hướng dẫn onboarding", "").strip()
    sections: list[tuple[str, str]] = [("Tổng quan", cleaned.split("## ", 1)[0].strip())]
    for block in cleaned.split("## ")[1:]:
        title, _, body = block.partition("\n")
        sections.append((title.strip(), body.strip()))
    return sections


def build_demo_pdf() -> Path:
    source_text = SOURCE.read_text(encoding="utf-8")
    document = pymupdf.open()
    for index, (title, body) in enumerate(markdown_sections(source_text), start=1):
        page = document.new_page(width=960, height=600)
        page.draw_rect((0, 0, 960, 14), color=(0.44, 0.47, 1), fill=(0.44, 0.47, 1))
        page.insert_font(fontname="Arial", fontfile=str(FONT_PATH))
        page.insert_text((58, 55), f"STUDYFLOW AI · SLIDE {index}", fontname="Arial", fontsize=10, color=(0.44, 0.47, 1))
        page.insert_textbox((58, 82, 900, 145), title, fontname="Arial", fontsize=27, color=(0.08, 0.1, 0.17))
        readable_body = re.sub(r"^\d+\. ", "• ", body, flags=re.MULTILINE)
        page.insert_textbox(
            (58, 155, 900, 535),
            readable_body,
            fontname="Arial",
            fontsize=14,
            lineheight=1.5,
            color=(0.2, 0.23, 0.32),
        )
        page.insert_text((855, 570), str(index), fontname="Arial", fontsize=10, color=(0.5, 0.52, 0.6))
    document.set_metadata({"title": "AI20K Build Phase — Hướng dẫn onboarding", "author": "StudyFlow AI"})
    document.save(OUTPUT, garbage=4, deflate=True)
    document.close()
    return OUTPUT


if __name__ == "__main__":
    print(build_demo_pdf())
