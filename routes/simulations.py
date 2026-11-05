from uuid import uuid4

import click
from flask import Blueprint, abort, redirect, render_template, request, url_for
from flask.cli import with_appcontext
from flask_login import current_user, login_required
from sqlalchemy import select

from extensions import db
from forms.simulation_forms import SimulationForm
from models import Simulation
from modules.scenarios import SCENARIO_DETAILS
from modules.simulation_engine import recover_interrupted_runs, run_simulation

bp = Blueprint("simulations", __name__, url_prefix="/simulations")


@click.command("recover-simulations")
@with_appcontext
def recover_simulations():
    """Mark interrupted simulation runs as failed."""
    click.echo(f"Recovered {recover_interrupted_runs()} interrupted simulation(s).")


@bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST" and current_user.role not in ("admin", "analyst"):
        abort(403)
    form = SimulationForm(request_key=uuid4().hex)
    if form.validate_on_submit():
        recover_interrupted_runs()
        simulation_id = run_simulation(form.scenario.data, form.request_key.data, current_user.username)
        return redirect(url_for("simulations.detail", simulation_id=simulation_id))
    recent = db.session.scalars(
        select(Simulation).order_by(Simulation.created_at.desc(), Simulation.id.desc()).limit(20)
    ).all()
    return render_template("simulation.html", form=form, recent=recent,
                           scenarios={key: item.description for key, item in SCENARIO_DETAILS.items()})


@bp.get("/<int:simulation_id>")
@login_required
def detail(simulation_id):
    simulation = db.get_or_404(Simulation, simulation_id)
    incident = simulation.incident
    # Each run creates a new incident. Its first residual belongs to the run.
    residual = next((risk for risk in incident.assessments if risk.kind == "Residual"), None) if incident else None
    return render_template("simulation_results.html", simulation=simulation, residual=residual)
