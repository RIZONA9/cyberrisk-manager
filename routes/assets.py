from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from extensions import db
from forms.asset_forms import AssetForm
from models import Asset, Incident
from modules.access import audit, editor_required

bp = Blueprint("assets", __name__, url_prefix="/assets")


@bp.get("/")
@login_required
def index():
    query = request.args.get("q", "").strip()[:200]
    statement = select(Asset).order_by(Asset.name, Asset.id)
    if query:
        statement = statement.where(or_(
            Asset.name.icontains(query, autoescape=True),
            Asset.identifier.icontains(query, autoescape=True),
            Asset.owner.icontains(query, autoescape=True),
        ))
    return render_template("assets.html", q=query, page=db.paginate(statement, per_page=20, max_per_page=20))


@bp.get("/<int:asset_id>")
@login_required
def detail(asset_id):
    asset = db.get_or_404(Asset, asset_id)
    page = db.paginate(select(Incident).where(Incident.asset_id == asset_id)
                       .order_by(Incident.detected_at.desc(), Incident.id.desc()),
                       per_page=20, max_per_page=20)
    return render_template("asset_detail.html", asset=asset, page=page)


@bp.route("/new", methods=["GET", "POST"])
@bp.route("/<int:asset_id>/edit", methods=["GET", "POST"])
@editor_required
def edit(asset_id=None):
    asset = db.get_or_404(Asset, asset_id) if asset_id else Asset()
    form = AssetForm(obj=asset)
    if form.validate_on_submit():
        form.populate_obj(asset)
        asset.identifier = asset.identifier.lower()
        db.session.add(asset)
        try:
            db.session.flush()
            audit("Edited asset" if asset_id else "Created asset", f"ASSET-{asset.id}", after=asset.criticality)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            form.identifier.errors.append("This identifier already exists.")
        else:
            flash("Asset saved.", "success")
            return redirect(url_for("assets.detail", asset_id=asset.id))
    return render_template("workspace_form.html", form=form, heading="Edit asset" if asset_id else "Add asset",
                           label="ASSET MANAGEMENT", submit="Save asset", back=url_for("assets.index"))
