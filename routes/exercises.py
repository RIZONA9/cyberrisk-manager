from flask import Blueprint, abort, redirect, render_template, url_for
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from sqlalchemy import select, update
from wtforms import HiddenField, SelectField
from wtforms.validators import InputRequired

from extensions import db
from forms import text_field
from models.exercise import ExerciseDecision, ExerciseRun
from models.timestamps import utc_now
from modules.access import editor_required
from modules.exercises import EXERCISES

bp = Blueprint("exercises", __name__, url_prefix="/exercises")


class StartForm(FlaskForm):
    scenario = SelectField("Scenario", choices=list(EXERCISES), validators=[InputRequired()])


class DecisionForm(FlaskForm):
    step_number = HiddenField(validators=[InputRequired()])
    choice = SelectField("Decision", coerce=int, validators=[InputRequired()])
    evidence = text_field("Evidence and reasoning", 2000, required=False, multiline=True)


@bp.get("/")
@login_required
def index():
    page = db.paginate(
        select(ExerciseRun).where(ExerciseRun.user_id == current_user.id).order_by(ExerciseRun.id.desc()),
        per_page=20, max_per_page=20,
    )
    return render_template("exercises.html", form=StartForm(), page=page)


@bp.post("/start")
@editor_required
def start():
    form = StartForm()
    if not form.validate_on_submit():
        abort(400, "Select an exercise scenario.")
    run = ExerciseRun(user_id=current_user.id, scenario=form.scenario.data)
    db.session.add(run)
    db.session.commit()
    return redirect(url_for("exercises.detail", run_id=run.id))


@bp.get("/<int:run_id>")
@login_required
def detail(run_id):
    run = owned_run(run_id)
    checkpoints = EXERCISES[run.scenario]
    if run.ended_at:
        return render_template("exercise_run.html", run=run, maximum=2 * len(checkpoints),
                               score=sum(item.points for item in run.decisions),
                               evidenced=sum(bool(item.evidence) for item in run.decisions))
    checkpoint = checkpoints[run.step]
    form = decision_form(run, checkpoint)
    return render_stage(run, checkpoints, checkpoint, form)


@bp.post("/<int:run_id>")
@editor_required
def decide(run_id):
    run = owned_run(run_id)
    checkpoints = EXERCISES[run.scenario]
    if run.ended_at:
        return redirect(url_for("exercises.detail", run_id=run.id))
    step = run.step
    checkpoint = checkpoints[step]
    form = decision_form(run, checkpoint)
    if form.step_number.data != str(step):
        return redirect(url_for("exercises.detail", run_id=run.id))
    if not form.validate_on_submit():
        return render_stage(run, checkpoints, checkpoint, form)
    option = checkpoint.options[form.choice.data]
    now = utc_now()
    started = run.decisions[-1].decided_at if run.decisions else run.started_at
    changed = db.session.execute(
        update(ExerciseRun).where(ExerciseRun.id == run.id, ExerciseRun.step == step)
        .values(step=step + 1, ended_at=now if step + 1 == len(checkpoints) else None)
    )
    if changed.rowcount != 1:
        db.session.rollback()
        return redirect(url_for("exercises.detail", run_id=run_id))
    db.session.add(ExerciseDecision(
        run_id=run_id, step=step, choice=option.label, feedback=option.feedback,
        points=option.points, evidence=form.evidence.data or None,
        seconds=max(0, int((now - started).total_seconds())), decided_at=now,
    ))
    db.session.commit()
    return redirect(url_for("exercises.detail", run_id=run_id))


def owned_run(run_id):
    return db.one_or_404(select(ExerciseRun).where(
        ExerciseRun.id == run_id, ExerciseRun.user_id == current_user.id,
    ))


def decision_form(run, checkpoint):
    form = DecisionForm(step_number=str(run.step))
    form.choice.choices = [(index, option.label) for index, option in enumerate(checkpoint.options)]
    return form


def render_stage(run, checkpoints, checkpoint, form):
    evidence = checkpoint.evidence
    if checkpoint.changed_evidence and run.decisions and run.decisions[-1].points == 0:
        evidence = checkpoint.changed_evidence
    return render_template("exercise_run.html", run=run, checkpoint=checkpoint,
                           evidence=evidence, total_steps=len(checkpoints), form=form)
