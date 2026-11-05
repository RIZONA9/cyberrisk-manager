import re
from datetime import date, datetime
from io import BytesIO
from xml.sax.saxutils import escape

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

from models.timestamps import utc_now


INVALID_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")
NAVY = "#162640"
BLUE = "#086B92"
INK = "#17253B"
PALE = "#EEF4FA"


def display_value(value):
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    if value is None:
        return ""
    return INVALID_XML.sub("", str(value))


def pdf_report(title, sections):
    output = BytesIO()
    document = SimpleDocTemplate(
        output, pagesize=landscape(A4), leftMargin=32, rightMargin=32,
        topMargin=48, bottomMargin=42, title=title, author="CyberRisk Manager",
    )
    cell = ParagraphStyle("Cell", fontName="Helvetica", fontSize=8, leading=10, textColor=colors.HexColor(INK))
    header = ParagraphStyle("Column", parent=cell, fontName="Helvetica-Bold", textColor=colors.white)
    heading = ParagraphStyle("Report", parent=cell, fontName="Helvetica-Bold", fontSize=22, leading=26)
    section_heading = ParagraphStyle(
        "Section", parent=cell, fontName="Helvetica-Bold", fontSize=13,
        leading=17, spaceBefore=12, spaceAfter=6, keepWithNext=True,
    )

    def paragraph(value, style=cell):
        return Paragraph(escape(display_value(value) or "-").replace("\n", "<br/>"), style)

    generated = utc_now().strftime("%Y-%m-%d %H:%M UTC")

    def decorate(canvas, doc):
        width, height = doc.pagesize
        canvas.setFillColor(colors.HexColor(NAVY))
        canvas.rect(0, height - 34, width, 34, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(34, height - 22, "CYBERRISK MANAGER  /  SECURITY REPORTS")
        canvas.setFont("Helvetica", 9)
        canvas.drawRightString(width - 34, height - 22, generated)
        canvas.setFillColor(colors.HexColor(BLUE))
        canvas.line(34, 31, width - 34, 31)
        canvas.drawString(34, 18, title)
        canvas.drawRightString(width - 34, 18, f"Page {doc.page}")

    story = [paragraph(title, heading), Spacer(1, 6)]
    for section in sections:
        story.append(paragraph(section.title, section_heading))
        if not section.rows:
            story.append(paragraph("No records available."))
            continue
        rows = [[paragraph(label, header) for label in section.headings]]
        rows.extend([[paragraph(value) for value in row] for row in section.rows])
        wider = {"Title", "Action", "Description", "Mitigation", "Notes", "Result", "Metric"}
        weights = [2.1 if label in wider else 1.0 for label in section.headings]
        table = LongTable(
            rows, colWidths=[(document.width - 12) * weight / sum(weights) for weight in weights],
            repeatRows=1, splitInRow=1,
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(NAVY)),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(PALE)]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor(BLUE)),
            ]),
        )
        story.append(table)
    document.build(story, onFirstPage=decorate, onLaterPages=decorate)
    output.seek(0)
    return output


def excel_report(title, sections):
    workbook = Workbook()
    workbook.remove(workbook.active)
    workbook.properties.title = title
    workbook.properties.creator = "CyberRisk Manager"
    for section in sections:
        sheet = workbook.create_sheet(section.title[:31])
        sheet.append(section.headings)
        for row in section.rows:
            sheet.append([value if type(value) is int else display_value(value) for value in row])
            for cell in sheet[sheet.max_row]:
                if isinstance(cell.value, str):
                    # Text from incidents and notes must never become a formula.
                    cell.data_type = "s"
                    cell.alignment = Alignment(vertical="top", wrap_text=True)
        for cell in sheet[1]:
            cell.fill = PatternFill("solid", fgColor="162640")
            cell.font = Font(color="FFFFFF", bold=True)
            cell.alignment = Alignment(vertical="center")
        sheet.row_dimensions[1].height = 24
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        for index, column in enumerate(sheet.columns, start=1):
            width = max(len(str(cell.value or "")) for cell in column) + 3
            sheet.column_dimensions[get_column_letter(index)].width = min(55, max(12, width))
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output
