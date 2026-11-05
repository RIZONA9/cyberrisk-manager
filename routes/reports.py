from flask import Blueprint, abort, render_template, send_file
from flask_login import login_required

from modules.report_data import REPORTS
from modules.report_engine import excel_report, pdf_report

bp = Blueprint("reports", __name__, url_prefix="/reports")
FORMATS = {
    "pdf": (pdf_report, "application/pdf"),
    "xlsx": (excel_report, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
}


@bp.get("/")
@login_required
def index():
    return render_template("reports.html", reports=REPORTS)


@bp.get("/<slug>.<extension>")
@login_required
def download(slug, extension):
    if slug not in REPORTS or extension not in FORMATS:
        abort(404)
    title, fetch = REPORTS[slug]
    generate, mimetype = FORMATS[extension]
    response = send_file(
        generate(title, fetch()), mimetype=mimetype, as_attachment=True,
        download_name=f"cyberrisk-{slug}.{extension}",
    )
    response.cache_control.no_store = True
    return response
