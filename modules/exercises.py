from dataclasses import dataclass


@dataclass(frozen=True)
class DecisionOption:
    label: str
    feedback: str
    points: int


@dataclass(frozen=True)
class Checkpoint:
    title: str
    evidence: str
    changed_evidence: str | None
    options: tuple[DecisionOption, DecisionOption]


EXERCISES = {
    "Phishing Attack": (
        Checkpoint("Preserve the message", "A user reports a suspicious login link. The message and headers are still available.", None, (
            DecisionOption("Preserve the message and headers", "You retained evidence for sender and recipient analysis.", 2),
            DecisionOption("Delete the message immediately", "You lost the original headers and reduced your ability to identify related messages.", 0),
        )),
        Checkpoint("Contain the account", "The sign-in timeline shows an unfamiliar session after the reported click.", "The original headers are unavailable. Sign-in logs still show an unfamiliar session after the reported click.", (
            DecisionOption("Wait for a second user report", "The unfamiliar session remains active.", 0),
            DecisionOption("Revoke sessions and require reauthentication", "The suspicious session was contained in the exercise.", 2),
        )),
        Checkpoint("Verify recovery", "The test account can sign in again and the suspicious session is absent.", "The training audit log shows continued activity from the original session.", (
            DecisionOption("Verify session revocation and review sign-in logs", "You established a clear recovery check before closure.", 2),
            DecisionOption("Close on the first successful sign-in", "Account access alone is insufficient recovery evidence.", 0),
        )),
    ),
    "Malware Infection": (
        Checkpoint("Capture endpoint evidence", "The workstation alert includes a process tree and repeated file changes.", None, (
            DecisionOption("Save the process tree and log timestamps", "You retained a timeline for scoping and investigation.", 2),
            DecisionOption("Clear the endpoint logs", "You lost telemetry needed to understand the alert.", 0),
        )),
        Checkpoint("Limit spread", "The affected training workstation is making unusual network connections.", "There is no preserved process tree. Network telemetry still shows unusual connections.", (
            DecisionOption("Continue normal workstation operation", "The simulated process retained network access.", 0),
            DecisionOption("Isolate the training workstation", "You contained the simulated network activity.", 2),
        )),
        Checkpoint("Restore service", "The exercise provides a known-clean image and a recovery checklist.", "The exercise now shows activity on an additional workstation.", (
            DecisionOption("Validate scope, restore, and monitor", "You checked recovery and watched for recurrence.", 2),
            DecisionOption("Reconnect after deleting the first sample", "The exercise lacks evidence that the scope and recovery are complete.", 0),
        )),
    ),
    "Unauthorized Access": (
        Checkpoint("Correlate identity events", "A successful login follows repeated failures from an unusual source.", None, (
            DecisionOption("Review the source and session audit logs", "You retained the evidence needed to establish scope.", 2),
            DecisionOption("Dismiss the alert as a password typo", "You missed an opportunity to investigate the success event.", 0),
        )),
        Checkpoint("Contain the identity", "The account was granted an unapproved privileged role.", "A later audit still shows an unapproved role, with incomplete session attribution.", (
            DecisionOption("Keep the role until the weekly review", "The privileged access remained in place.", 0),
            DecisionOption("Revoke the grant and terminate suspicious sessions", "You removed the access path in the exercise.", 2),
        )),
        Checkpoint("Confirm access integrity", "Normal access has resumed for the authorized identity.", "The synthetic record shows privileged activity continuing after the review window.", (
            DecisionOption("Verify permissions and document the audit evidence", "You checked access integrity and retained the findings.", 2),
            DecisionOption("Close after resetting the password", "A password reset does not validate role assignments.", 0),
        )),
    ),
    "Data Breach": (
        Checkpoint("Scope the export", "A synthetic audit log shows a bulk export outside the exercise window.", None, (
            DecisionOption("Preserve the export logs and identify affected records", "You retained the scope evidence.", 2),
            DecisionOption("Overwrite the export audit file", "The scope is now harder to establish.", 0),
        )),
        Checkpoint("Restrict further exports", "A training account has broad export permissions.", "Scope remains uncertain. Permission records show a training account with broad export access.", (
            DecisionOption("Leave the route open while drafting a report", "The exercise still permits further unauthorized export.", 0),
            DecisionOption("Suspend the route and revoke the excess permission", "You restricted the simulated export path.", 2),
        )),
        Checkpoint("Verify and hand off", "The authorized training workflow can be restored with limited permissions.", "The mock audit log reports another export while containment was delayed.", (
            DecisionOption("Verify restrictions and hand off the documented scope", "The exercise retains evidence and a verified recovery check.", 2),
            DecisionOption("Close as soon as the export stops", "The record lacks scope and control verification.", 0),
        )),
    ),
}
