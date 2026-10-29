"""Зібрати PDF першої лабораторної з Markdown-оригіналу.

Використання: python tools/build_report.py --font-dir /path/to/fonts
Файли Times New Roman мають бути встановлені користувачем із правом використання.
"""

from argparse import ArgumentParser
from html import escape
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, KeepTogether, PageBreak, PageTemplate,
    Paragraph, Spacer,
)


ROOT = Path(__file__).resolve().parents[1]


class Architecture(Flowable):
    """Векторна блок-схема з п'ятьма обов'язковими компонентами."""

    def __init__(self):
        super().__init__()
        self.width = 165 * mm
        self.height = 370

    def draw(self):
        canvas = self.canv
        canvas.setLineWidth(0.7)

        def box(x, y, width, lines, height=52, fill=False):
            canvas.setFillColor(colors.HexColor("#f4f4f4") if fill else colors.white)
            canvas.rect(x, y, width, height, fill=1)
            canvas.setFillColor(colors.black)
            canvas.setFont("TNR", 14)
            for number, text in enumerate(lines):
                canvas.drawCentredString(x + width / 2, y + height - 19 - number * 18, text)

        def arrow(points):
            path = canvas.beginPath()
            path.moveTo(*points[0])
            for point in points[1:]:
                path.lineTo(*point)
            canvas.drawPath(path)
            x, y = points[-1]
            x0, y0 = points[-2]
            dx, dy = x - x0, y - y0
            length = (dx * dx + dy * dy) ** 0.5
            ux, uy = dx / length, dy / length
            tip = canvas.beginPath()
            tip.moveTo(x, y)
            tip.lineTo(x - ux * 6 - uy * 3, y - uy * 6 + ux * 3)
            tip.lineTo(x - ux * 6 + uy * 3, y - uy * 6 - ux * 3)
            tip.close()
            canvas.setFillColor(colors.black)
            canvas.drawPath(tip, fill=1)

        box(10, 310, 215, ["Джерело даних", "Simple English Wikipedia"])
        box(275, 310, 175, ["Користувач"])
        box(10, 225, 215, ["1. Ingestion", "очищення й чанкування"], fill=True)
        box(275, 225, 175, ["5. CLI", "оркестрація"], fill=True)
        box(10, 133, 215, ["2. Векторний індекс", "Chroma та MiniLM"], fill=True)
        box(275, 133, 175, ["3. Ретривер", "dense, BM25, RRF"], fill=True)
        box(275, 38, 175, ["4. Генерація", "Ollama, Llama 3.2 3B"], fill=True)
        box(10, 38, 215, ["Валідатор", "перевірка цитат"])
        arrow([(117, 310), (117, 277)])
        arrow([(352, 310), (352, 277)])
        arrow([(404, 277), (404, 310)])
        arrow([(117, 225), (117, 185)])
        arrow([(352, 225), (352, 185)])
        arrow([(225, 159), (275, 159)])
        arrow([(352, 133), (352, 90)])
        arrow([(275, 64), (225, 64)])
        arrow([(117, 38), (117, 10), (463, 10), (463, 251), (450, 251)])
        canvas.setFont("TNR", 14)
        canvas.drawCentredString(177, 203, "ембединги")
        canvas.drawCentredString(406, 111, "до 5 чанків")


def register_fonts(directory):
    files = {path.name.casefold(): path for path in directory.iterdir() if path.is_file()}
    for name, candidates in (
        ("TNR", ("times.ttf", "timesnewroman.ttf")),
        ("TNR-Bold", ("timesbd.ttf", "timesnewromanbold.ttf")),
    ):
        path = next((files[x] for x in candidates if x in files), None)
        if path is None:
            raise SystemExit(f"Немає шрифту {name} у {directory}; очікується {candidates[0]}")
        pdfmetrics.registerFont(TTFont(name, str(path)))
    pdfmetrics.registerFontFamily("TNR", normal="TNR", bold="TNR-Bold")


def styles():
    base = dict(fontName="TNR", fontSize=14, leading=21, textColor=colors.black)
    return {
        "body": ParagraphStyle("Body", alignment=TA_JUSTIFY, firstLineIndent=12.5 * mm,
                               spaceAfter=0, **base),
        "h1": ParagraphStyle("Heading1", alignment=TA_CENTER, fontName="TNR-Bold",
                             fontSize=14, leading=21, spaceBefore=0, spaceAfter=12,
                             keepWithNext=True),
        "h2": ParagraphStyle("Heading2", alignment=TA_LEFT, fontName="TNR-Bold",
                             fontSize=14, leading=21, spaceBefore=12, spaceAfter=8,
                             keepWithNext=True),
        "center": ParagraphStyle("Center", alignment=TA_CENTER, **base),
        "right": ParagraphStyle("Right", alignment=TA_RIGHT, **base),
        "code": ParagraphStyle("Code", fontName="Courier", fontSize=12, leading=18,
                               leftIndent=12.5 * mm, spaceBefore=6, spaceAfter=6),
    }


def markup(text):
    # Текст джерел зберігається як текст; довгі URL переносяться за потреби.
    return escape(text).replace("\n", " ")


def title_page(title, style):
    lines = [block.strip() for block in title.split("\n\n") if block.strip()]
    story = []
    for number, line in enumerate(lines):
        if number == 3:
            story.append(Spacer(1, 70))
        if line.startswith("Виконав:"):
            story.append(Spacer(1, 55))
        if line == "Харків 2026":
            continue  # Рік і місто розміщуються біля нижнього поля титулу.
        alignment = "right" if line.startswith(("Виконав:", "Дідковський", "Перевірив:")) else "center"
        story.append(Paragraph(markup(line), style[alignment]))
    story.append(PageBreak())
    return story


def content(source, style):
    title, body = source.replace("<!-- title -->", "", 1).split("<!-- pagebreak -->", 1)
    story = title_page(title, style)
    for block in re.split(r"\n\s*\n", body.strip()):
        block = block.strip()
        if not block:
            continue
        if block == "<!-- pagebreak -->":
            story.append(PageBreak())
        elif block == "[[ARCHITECTURE]]":
            story.append(KeepTogether([Architecture(), Spacer(1, 8)]))
        elif block.startswith("# "):
            story.append(Paragraph(markup(block[2:]), style["h1"]))
        elif block.startswith("## "):
            story.append(Paragraph(markup(block[3:]), style["h2"]))
        elif block.startswith("```"):
            code = "\n".join(block.splitlines()[1:-1])
            story.append(Paragraph(escape(code).replace("\n", "<br/>"), style["code"]))
        elif block.startswith("Рисунок "):
            story.append(Paragraph(markup(block), style["center"]))
            story.append(Spacer(1, 8))
        else:
            story.append(Paragraph(markup(block), style["body"]))
    return story


def page_number(canvas, document):
    canvas.saveState()
    canvas.setFont("TNR", 14)
    if document.page == 1:
        canvas.drawCentredString((30 * mm + A4[0] - 15 * mm) / 2, 25 * mm, "Харків 2026")
    else:
        canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, str(document.page))
    canvas.restoreState()


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--font-dir", type=Path, required=True)
    parser.add_argument("--source", type=Path, default=ROOT / "reports/lab-1/report.md")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/lab-1/report.pdf")
    args = parser.parse_args()
    register_fonts(args.font_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(args.output), pagesize=A4, leftMargin=30 * mm, rightMargin=15 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
        title="Лабораторна робота № 1 Проєктування географічної RAG-системи",
        author="Олексій Дідковський", subject="ІПЗздм-26-1 Дашенков Д. С.",
        pageCompression=1,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates(PageTemplate(id="Report", frames=[frame], onPage=page_number))
    doc.build(content(args.source.read_text(encoding="utf-8"), styles()))
    print(args.output)


if __name__ == "__main__":
    main()
