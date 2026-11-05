import csv
import io
import re
from datetime import date
from math import isfinite

from sqlalchemy import case, select
from sqlalchemy.dialects.sqlite import insert

from extensions import db
from models import Asset
from models.vulnerability import Vulnerability


FILE_LIMIT = 128 * 1024
HEADINGS = ("asset_identifier", "cve", "cvss", "epss", "kev", "source", "observed_on")


def score(text, maximum):
    if not text:
        return None
    value = float(text)
    if not isfinite(value) or not 0 <= value <= maximum:
        raise ValueError("Score out of range.")
    return value


def parse_record(row, assets):
    identifier = row["asset_identifier"].lower()
    cve = row["cve"].upper()
    if identifier not in assets or not re.fullmatch(r"CVE-[0-9]{4}-[0-9]{4,20}", cve):
        raise ValueError("Use a registered asset identifier and valid CVE ID.")
    if not 1 <= len(row["source"]) <= 200:
        raise ValueError("Provide a source of up to 200 characters.")
    return {
        "asset_id": assets[identifier], "cve": cve, "cvss": score(row["cvss"], 10),
        "epss": score(row["epss"], 1), "kev": {"yes": True, "no": False, "": None}[row["kev"].lower()],
        "source": row["source"], "observed_on": date.fromisoformat(row["observed_on"]),
    }


def import_findings(raw):
    if len(raw) > FILE_LIMIT:
        raise ValueError("The CSV must be 128 KiB or smaller.")
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), strict=True)
        if not reader.fieldnames or len(reader.fieldnames) != len(HEADINGS) or set(reader.fieldnames) != set(HEADINGS):
            raise ValueError("The CSV headings must match the provided template.")
        rows = list(reader)
    except (UnicodeError, csv.Error) as error:
        raise ValueError("Upload a valid UTF-8 CSV.") from error
    if not 1 <= len(rows) <= 250:
        raise ValueError("Provide between 1 and 250 findings.")
    assets = dict(db.session.execute(select(Asset.identifier, Asset.id)).all())
    records = []
    for index, row in enumerate(rows, start=2):
        try:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("Row has the wrong number of columns.")
            records.append(parse_record({key: value.strip() for key, value in row.items()}, assets))
        except (KeyError, ValueError) as error:
            raise ValueError(f"Invalid finding on CSV row {index}. Check asset, CVE, scores, KEV, source, and date.") from error
    updated = 0
    for record in records:
        statement = insert(Vulnerability).values(**record)
        result = db.session.execute(statement.on_conflict_do_update(
            index_elements=["asset_id", "cve"],
            set_={key: getattr(statement.excluded, key) for key in (
                "cvss", "epss", "kev", "source", "observed_on",
            )},
            where=Vulnerability.observed_on < statement.excluded.observed_on,
        ))
        updated += result.rowcount
    return updated, len(records) - updated


def priority_columns():
    known_exploited = Vulnerability.kev.is_(True)
    sensitive_asset = Asset.internet_exposed.is_(True) | (Asset.criticality == "Critical")
    high_signal = (Vulnerability.cvss >= 9) | (Vulnerability.epss >= 0.5)
    return (
        case((known_exploited, 1), (sensitive_asset & high_signal, 2), else_=3),
        case((known_exploited, "Known exploitation in CISA KEV"),
             (sensitive_asset & high_signal, "Critical or exposed asset with a high CVSS or EPSS signal"),
             else_="Standard review queue"),
    )
