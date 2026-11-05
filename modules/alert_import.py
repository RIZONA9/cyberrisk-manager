import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert

from extensions import db
from models import Alert, Asset


ALERT_FILE_LIMIT = 128 * 1024
MAX_ALERTS = 250


def required_text(value, limit):
    if type(value) not in (str, int) or not 1 <= len(str(value).strip()) <= limit:
        raise ValueError("Missing or invalid alert field.")
    return str(value).strip()


def parse_alert(item):
    rule, agent = item["rule"], item["agent"]
    timestamp = datetime.fromisoformat(required_text(item["timestamp"], 40).replace("Z", "+00:00"))
    if timestamp.utcoffset() is None:
        raise ValueError("Timestamps must include a UTC offset.")
    level = rule["level"]
    if type(level) is not int or not 0 <= level <= 15:
        raise ValueError("Invalid Wazuh rule level.")
    return {
        "external_id": required_text(item["id"], 120),
        "rule_id": required_text(rule["id"], 80),
        "level": level,
        "description": required_text(rule["description"], 1000),
        "agent_name": required_text(agent["name"], 120),
        "occurred_at": timestamp.astimezone(timezone.utc).replace(tzinfo=None),
    }


def read_alerts(raw):
    if len(raw) > ALERT_FILE_LIMIT:
        raise ValueError("The alert file must be 128 KiB or smaller.")
    try:
        content = raw.decode("utf-8-sig")
        try:
            records = json.loads(content)
        except json.JSONDecodeError:
            records = [json.loads(line) for line in content.splitlines() if line.strip()]
    except (ValueError, RecursionError) as error:
        raise ValueError("Upload UTF-8 JSON or newline-delimited JSON.") from error
    if isinstance(records, dict):
        records = [records]
    if not isinstance(records, list) or not 1 <= len(records) <= MAX_ALERTS:
        raise ValueError("Provide between 1 and 250 Wazuh alerts.")
    alerts = []
    for index, item in enumerate(records, 1):
        try:
            alerts.append(parse_alert(item))
        except (KeyError, TypeError, ValueError, OverflowError) as error:
            raise ValueError(f"Alert {index} needs an ID, timestamp with offset, rule, and agent name.") from error
    return alerts


def import_alerts(source, alerts):
    identifiers = {alert["agent_name"].lower() for alert in alerts}
    assets = dict(db.session.execute(select(Asset.identifier, Asset.id)
                                     .where(Asset.identifier.in_(identifiers))).all())
    added = 0
    for alert in alerts:
        result = db.session.execute(
            insert(Alert).values(source=source.lower(), **alert,
                                 asset_id=assets.get(alert["agent_name"].lower()))
            .on_conflict_do_nothing(index_elements=["source", "external_id"])
        )
        added += result.rowcount
    return added, len(alerts) - added


def severity_for_level(level):
    if level >= 12:
        return "Critical"
    if level >= 8:
        return "High"
    if level >= 4:
        return "Medium"
    return "Low"
