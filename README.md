# CyberRisk Manager

CyberRisk Manager is an academic application for cybersecurity incident
management, risk assessment, and response exercises. It uses Flask and SQLite
with an English, responsive dashboard. Bootstrap and Chart.js are served
locally, so the application works offline after setup.

For GitHub publication and the free HTTPS deployment, see the
[deployment guide](docs/deployment.md).

## Run locally in PyCharm on Windows

Open this project folder in PyCharm. Use Python 3.10 or newer. If the
`venv` folder does not exist, create it from the PyCharm PowerShell terminal:

```powershell
python -m venv venv
```

In PyCharm's Python Interpreter settings, select the existing interpreter at
`venv\Scripts\python.exe`. For a fresh workspace, install dependencies and
prepare the database from the project terminal:

```powershell
.\venv\Scripts\Activate.ps1
python --version
pip install -r requirements.txt
flask --app app seed-demo
```

For everyday use, choose **CyberRisk Manager** in PyCharm's run configuration
menu and click **Run**. The configuration starts Flask on port 5000. Open
[the local application](http://localhost:5000/) in your browser. The address
`127.0.0.1` in PyCharm's Run console is the loopback address for this computer.
Use the same address or hostname throughout a browser session.

Sign in with the local
academic demonstration account `admin` and password `Admin@12345`. Change
the password in **Settings** when sharing the local workspace. Use a unique
account and password for an HTTPS deployment. Use **Stop** in the Run tool
window to shut down the development server. For a terminal run, use
`flask --app app run --debug` and press Ctrl+C to stop it.

The seed command applies migrations and adds sample incidents and simulations.
Repeated runs preserve existing records and the existing admin password.
For a workspace with empty tables, run `flask --app app db upgrade` followed
by `flask --app app create-user --username operator` instead of seeding.

If PowerShell blocks script activation, run the same tools through the virtual
environment interpreter with `.\venv\Scripts\python.exe -m pip`,
`.\venv\Scripts\python.exe -m flask`, and `.\venv\Scripts\python.exe -m pytest`.

## Database

`flask --app app db upgrade` applies the tracked migrations to
`instance/cyberrisk.db`. SQLite foreign keys protect linked history from
accidental parent deletion. Stored timestamps use UTC. The Delete workflow
removes a record from active metrics and exposes it in the read-only
**Incidents → View archive** list with its assessment and response history.

## University demonstration

1. Sign in and review the database-backed incident, risk, and simulation metrics.
2. In **Run simulation**, select Phishing Attack and run the exercise. Open the
   generated incident from the result page.
3. Review the six response stages, event timeline, and initial and residual
   scores. Open the incident's risk register entry to set ownership, status,
   and a review date.
4. In **Incidents**, create a manual incident and record its initial assessment.
   Document mitigation and add a residual assessment. Review the assessment history.
5. In **Reports**, download the simulation or comparison report as PDF and Excel.

### Extended lab workflow

1. In **Assets**, register a lab server with identifier `lab-ssh-01`.
2. In **Alert inbox**, import [the synthetic Wazuh sample](examples/wazuh-alerts.jsonl)
   as JSON Lines. A source name identifies one Wazuh manager. Reimporting the
   same source and event ID skips the duplicate. Open an alert and create an incident.
3. Enter a first-observed time if the underlying evidence provides one.
   Record **Containment** and **Recovery** actions with their actual times.
   The dashboard's **Response metrics and targets** view uses the earliest
   usable stage timestamps and shows medians with sample sizes by origin.
4. Update the risk register owner and date. An analyst can request risk
   acceptance. A different account with the admin role must review it.
   **Risk approvals** also links admin and reviewer accounts to the audit log.
5. In **Vulnerabilities**, import the [sample CSV](examples/vulnerability-findings.csv).
   It uses a synthetic finding. For real findings, provide a registered asset,
   CVE, source, observation date, and known CVSS, EPSS and KEV values.
   Use blank for unknown values and a fraction from 0 to 1 for EPSS.
   A newer observation updates the same asset/CVE. P1 indicates a KEV flag;
   P2 indicates a critical or internet-exposed asset with CVSS ≥ 9 or EPSS ≥ 0.5;
   P3 is the remaining review queue. These are local triage rules.
6. Open **Interactive exercises** from **Run simulation**. Complete three
   decisions and review the branch-dependent evidence, rubric score, and timings.

The export center also offers incident, initial risk, residual risk, risk
register, incident response, and overall security reports.

The four exercises cover **Phishing Attack**, **Malware Infection**,
**Unauthorized Access**, and **Data Breach**. All actions use synthetic records
within the application. Reposting the same run request returns the original
result. A failed run rolls back its partial incident data and saves a failure
event. A new run request or `flask --app app recover-simulations` marks pending
or running jobs older than five minutes as interrupted.

## Risk methodology

Risk score equals likelihood multiplied by impact. Both inputs are integers
from 1 to 5.

| Score | Level |
| --- | --- |
| 1–4 | Low |
| 5–9 | Medium |
| 10–16 | High |
| 17–25 | Critical |

For example, likelihood 4 and impact 5 yield an initial score of 20 (Critical).
After documenting mitigation, likelihood 2 and impact 3 yield a residual score
of 6 (Medium). Each incident has one initial assessment and can keep multiple
residual assessments. Closing an incident preserves the recorded risk values.
Dashboard risk counts use the latest residual assessment when available and
the initial assessment otherwise.

## Incident response reference

The six educational stages are Preparation, Detection and Analysis,
Containment, Eradication, Recovery, and Lessons Learned. The application adapts
the lifecycle in [NIST SP 800-61 Rev. 2, section 3](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-61r2.pdf)
by separating containment, eradication, and recovery and recording lessons
learned as the post-incident activity. NIST superseded Rev. 2 with
[Rev. 3](https://csrc.nist.gov/pubs/sp/800/61/r3/final) in April 2025.

## Configuration

The development profile supports HTTP on loopback. Session cookies use
HttpOnly and SameSite=Lax. For a persistent local signing key, set the
`CYBERRISK_SECRET_KEY` environment variable to a private random value.
Otherwise the app generates a fresh key at startup.

For an HTTPS deployment, set `CYBERRISK_ENV=production` and supply a private
random `CYBERRISK_SECRET_KEY` of at least 32 characters. This profile uses
Secure session cookies and a separate `instance/cyberrisk-production.db`.
Apply migrations and create an account using the CLI above. Serve through a
production WSGI server behind HTTPS. Demo seeding is restricted to development
and tests. Passwords use Werkzeug hashes, and a password change ends existing
sessions for that account.

## Run tests

Run these in the PyCharm terminal. Database tests use temporary SQLite files,
and the application smoke tests use a separate in-memory database.

```powershell
python -m pytest -v
flask --app app db check
```

## Project layout and limits

- `models/` defines the SQLite schema and relationships. `migrations/` tracks schema changes.
- `forms/` validates input, `routes/` handles HTTP requests, and `modules/` contains risk, simulation, demo, and report logic.
- `templates/` and `static/` contain the dashboard, forms, and local browser assets.
- The workspace supports admin, analyst, and reviewer roles. Use `flask --app app create-user --username NAME --role ROLE` to provision an account. Roles share the same workspace data.
- Alert and vulnerability intake uses file imports. Reports are generated on demand in memory. PDF typography uses ReportLab's standard fonts for English output.
- The Windows validation environment used Python 3.12.10. The project targets Python 3.10 and newer.

Bootstrap 5.3.3 and Chart.js 4.4.8 are bundled under `static/vendor/` with
their license notices.
