from flask import Blueprint, abort, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import login_required
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from extensions import db
from forms import text_field
from models.vulnerability import Vulnerability
from modules.access import audit, editor_required
from modules.vulnerabilities import FILE_LIMIT, import_findings, priority_columns

bp = Blueprint("vulnerabilities", __name__, url_prefix="/vulnerabilities")


class ImportForm(FlaskForm):
    upload = FileField("Finding CSV", validators=[FileRequired()])


class FindingForm(FlaskForm):
    reason = text_field("Reason or remediation evidence", 2000, multiline=True)


@bp.get("/")
@login_required
def index():
    priority, reason = priority_columns()
    scope = request.args.get("scope", "Open")
    query = select(Vulnerability, priority.label("priority"), reason.label("reason")).join(Vulnerability.asset)
    page = db.paginate(select(Vulnerability).join(Vulnerability.asset)
                       .where(Vulnerability.status == scope if scope in ("Open", "Resolved") else True)
                       .options(joinedload(Vulnerability.asset)).order_by(priority, Vulnerability.id),
                       per_page=20, max_per_page=20)
    details = db.session.execute(query.where(Vulnerability.id.in_([item.id for item in page.items]))).all()
    rows = {item.id: (rank, explanation) for item, rank, explanation in details}
    return render_template("vulnerabilities.html", page=page, rows=rows, scope=scope)


@bp.get("/example")
@login_required
def example():
    return send_from_directory("examples", "vulnerability-findings.csv", as_attachment=True)


@bp.route("/import", methods=["GET", "POST"])
@editor_required
def upload():
    form = ImportForm()
    if form.validate_on_submit():
        try:
            added, skipped = import_findings(form.upload.data.stream.read(FILE_LIMIT + 1))
        except ValueError as error:
            form.upload.errors.append(str(error))
        else:
            audit("Imported vulnerabilities", "Finding batch", after=f"{added} new or updated, {skipped} skipped")
            db.session.commit()
            flash(f"Saved {added} findings. Skipped {skipped} duplicates or older observations.", "success")
            return redirect(url_for("vulnerabilities.index"))
    return render_template("workspace_form.html", form=form, label="VULNERABILITY MANAGEMENT",
                           heading="Import vulnerability findings", multipart=True, submit="Import",
                           description="Use the sample CSV headers and existing asset identifiers. Scores may be blank when unavailable.",
                           back=url_for("vulnerabilities.index"))


@bp.route("/<int:finding_id>/<any(resolve,reopen):action>", methods=["GET", "POST"])
@editor_required
def change_status(finding_id, action):
    finding = db.get_or_404(Vulnerability, finding_id)
    desired = "Resolved" if action == "resolve" else "Open"
    if finding.status == desired:
        abort(409, f"This finding is already {desired.lower()}.")
    form = FindingForm()
    if form.validate_on_submit():
        audit("Updated vulnerability", f"{finding.cve} · ASSET-{finding.asset_id}",
              before=finding.status, after=desired, reason=form.reason.data)
        finding.status = desired
        db.session.commit()
        return redirect(url_for("vulnerabilities.index"))
    return render_template("workspace_form.html", form=form, label="VULNERABILITY MANAGEMENT",
                           heading=f"{action.title()} {finding.cve}", submit="Save status",
                           back=url_for("vulnerabilities.index"))
