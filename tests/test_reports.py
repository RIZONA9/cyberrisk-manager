from io import BytesIO
from uuid import uuid4

import pytest
from openpyxl import load_workbook
from pypdf import PdfReader

from extensions import db
from models import Simulation
from modules.report_data import REPORTS
from modules.simulation_engine import run_simulation


REPORT_MARKERS = [
    ("incidents", "Phishing Attack"), ("initial-risk", "Critical"),
    ("residual-risk", "Medium"), ("risk-comparison", "Residual score"),
    ("risk-register", "RISK-"), ("simulations", "Lessons Learned"),
    ("responses", "Containment"), ("summary", "Medium current risks"),
]


@pytest.fixture
def populated_client(app, signed_in):
    with app.app_context():
        run_id = run_simulation("Phishing Attack", uuid4().hex, "admin")
        db.session.get(Simulation, run_id).incident.title = "=TRAINING()"
        db.session.commit()
    return signed_in


@pytest.mark.parametrize(("slug", "marker"), REPORT_MARKERS)
def test_pdf_and_excel_downloads_include_data(populated_client, slug, marker):
    assert {slug for slug, _ in REPORT_MARKERS} == set(REPORTS)
    pdf = populated_client.get(f"/reports/{slug}.pdf")
    assert pdf.status_code == 200 and pdf.mimetype == "application/pdf"
    assert f"cyberrisk-{slug}.pdf" in pdf.headers["Content-Disposition"]
    assert "no-store" in pdf.headers["Cache-Control"]
    document = PdfReader(BytesIO(pdf.data))
    assert marker in " ".join(" ".join(page.extract_text().split()) for page in document.pages)

    excel = populated_client.get(f"/reports/{slug}.xlsx")
    assert excel.status_code == 200 and excel.mimetype.endswith("spreadsheetml.sheet")
    workbook = load_workbook(BytesIO(excel.data))
    cells = [cell for sheet in workbook for row in sheet.iter_rows() for cell in row]
    assert any(marker in str(cell.value) for cell in cells)
    assert all(cell.data_type != "f" for cell in cells)
    if slug == "incidents":
        assert any(cell.value == "=TRAINING()" and cell.data_type == "s" for cell in cells)
    assert all(sheet.freeze_panes == "A2" for sheet in workbook)
    workbook.close()


def test_report_routes_are_protected(client, signed_in):
    assert client.application.test_client().get("/reports/summary.pdf").status_code == 302
    assert signed_in.get("/reports/").status_code == 200
    assert signed_in.get("/reports/unknown.pdf").status_code == 404
