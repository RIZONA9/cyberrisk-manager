from datetime import timedelta

from flask import current_app
from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert

from extensions import db
from models import Incident, IncidentHistory, ResponseAction, Simulation, SimulationEvent
from models.response import RESPONSE_STAGES
from models.timestamps import utc_now
from modules.risk_engine import build_assessment
from modules.scenarios import SCENARIO_DETAILS


STALE_AFTER = timedelta(minutes=5)


def add_event(simulation, event_type, description, status="Recorded"):
    simulation.events.append(SimulationEvent(
        event_type=event_type, description=description, status=status, occurred_at=utc_now(),
    ))


def populate_run(simulation, actor):
    scenario = SCENARIO_DETAILS[simulation.scenario_type]
    initial = build_assessment("Initial", *scenario.initial, assessed_at=utc_now())
    incident = Incident(
        title=f"Simulation · {simulation.scenario_type}",
        description=f"Educational simulation. {scenario.description}",
        incident_type=simulation.scenario_type,
        severity=initial.level, status="Closed", detected_at=simulation.started_at,
        reported_by="Simulation engine", affected_asset=scenario.asset,
        assigned_to=actor, resolution_notes="Completed all six simulated response stages.",
    )
    simulation.incident = incident
    incident.assessments.append(initial)
    incident.history.append(IncidentHistory(
        event="Simulated", actor=actor, details="Incident created through an educational simulation.",
    ))
    for stage, description in zip(RESPONSE_STAGES, scenario.actions, strict=True):
        message = f"Simulated: {description}"
        incident.response_actions.append(ResponseAction(
            stage=stage, description=message, responsible_person=actor, action_at=utc_now(),
        ))
        add_event(simulation, stage, message)
        if stage == "Detection and Analysis":
            add_event(simulation, "Initial risk", f"Initial risk recorded at {initial.score} ({initial.level}).")

    residual = build_assessment(
        "Residual", *scenario.residual, assessed_at=utc_now(),
        mitigation_actions=f"Simulated: {scenario.actions[2]}",
        control_description=f"Simulated: {scenario.actions[3]} {scenario.actions[4]}",
        mitigation_at=utc_now(), responsible_person=actor, notes="Synthetic training data.",
    )
    incident.assessments.append(residual)
    simulation.ended_at = utc_now()
    simulation.result_summary = (
        f"Educational simulation completed all six response stages. "
        f"Initial risk {initial.score} ({initial.level}); residual risk {residual.score} ({residual.level})."
    )
    add_event(simulation, "Residual risk", f"Residual risk recorded at {residual.score} ({residual.level}).")
    add_event(simulation, "Completed", "Educational exercise completed.", "Completed")


def run_simulation(scenario_name, request_key, actor):
    if scenario_name not in SCENARIO_DETAILS:
        raise ValueError("Unknown simulation scenario.")
    now = utc_now()
    db.session.execute(insert(Simulation).values(
        scenario_type=scenario_name, request_key=request_key, status="Pending", created_at=now,
    ).on_conflict_do_nothing(index_elements=["request_key"]))
    simulation_id, status = db.session.execute(
        select(Simulation.id, Simulation.status).where(Simulation.request_key == request_key)
    ).one()
    claim = db.session.execute(
        update(Simulation).where(Simulation.id == simulation_id, Simulation.status == "Pending")
        .values(status="Running", started_at=now)
    ) if status == "Pending" else None
    db.session.commit()
    if claim is None or claim.rowcount != 1:
        return simulation_id

    try:
        # Claim the final write before generating records. A rollback removes the
        # entire incident, including its assessments, actions, and simulation events.
        result = db.session.execute(
            update(Simulation).where(Simulation.id == simulation_id, Simulation.status == "Running")
            .values(status="Completed")
        )
        if result.rowcount == 1:
            populate_run(db.session.get(Simulation, simulation_id), actor)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Simulation %s failed", simulation_id)
        mark_failed(simulation_id, "The simulation could not complete. Start a new run to retry.")
        db.session.commit()
    return simulation_id


def mark_failed(simulation_id, message, *, cutoff=None):
    now = utc_now()
    statement = update(Simulation).where(
        Simulation.id == simulation_id, Simulation.status.in_(("Pending", "Running")),
    )
    if cutoff is not None:
        statement = statement.where(db.func.coalesce(Simulation.started_at, Simulation.created_at) <= cutoff)
    result = db.session.execute(statement.values(
        status="Failed", started_at=db.func.coalesce(Simulation.started_at, now),
        ended_at=now, result_summary=message,
    ))
    if result.rowcount:
        add_event(db.session.get(Simulation, simulation_id), "Failed", message, "Failed")
    return result.rowcount


def recover_interrupted_runs():
    cutoff = utc_now() - STALE_AFTER
    ids = db.session.scalars(select(Simulation.id).where(
        Simulation.status.in_(("Pending", "Running")),
        db.func.coalesce(Simulation.started_at, Simulation.created_at) <= cutoff,
    )).all()
    recovered = sum(
        mark_failed(item, "Simulation interrupted before completion.", cutoff=cutoff) for item in ids
    )
    db.session.commit()
    return recovered
