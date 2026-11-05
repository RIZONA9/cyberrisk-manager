from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    description: str
    asset: str
    initial: tuple[int, int]
    residual: tuple[int, int]
    actions: tuple[str, ...]


SCENARIO_DETAILS = {
    "Phishing Attack": Scenario(
        "A fictional employee reports a message containing a mock sign-in link.",
        "Training mailbox", (4, 5), (2, 3),
        (
            "Prepared a mailbox reporting checklist and test account inventory.",
            "Reviewed a fictional report and identified the mock credential request.",
            "Marked the sample message as quarantined and mock sessions as revoked.",
            "Removed the training message from the simulated mailbox.",
            "Verified sign-in and mailbox access for the training account.",
            "Recorded stronger sign-in controls and a reporting awareness exercise.",
        ),
    ),
    "Malware Infection": Scenario(
        "A synthetic endpoint alert describes suspicious file activity on a training workstation.",
        "Training workstation", (5, 5), (2, 3),
        (
            "Prepared the exercise workstation inventory and recovery checklist.",
            "Reviewed synthetic process and file events for the training workstation.",
            "Marked the fictional workstation as isolated in the exercise record.",
            "Recorded removal of the sample artifact from the fictional inventory.",
            "Verified restoration from a mock clean workstation image.",
            "Recorded improvements to alert triage and recovery rehearsals.",
        ),
    ),
    "Unauthorized Access": Scenario(
        "A fictional access log shows repeated failed logins followed by a successful sign-in.",
        "Training identity portal", (4, 4), (2, 2),
        (
            "Prepared a mock identity log and account response checklist.",
            "Correlated a synthetic sign-in with the fictional account activity.",
            "Marked the mock account as temporarily locked and its sessions revoked.",
            "Recorded removal of a fictional unapproved access grant.",
            "Verified normal access for the authorized training persona.",
            "Recorded stricter access review and additional sign-in alert coverage.",
        ),
    ),
    "Data Breach": Scenario(
        "A mock audit log describes an unexpected export of synthetic customer records.",
        "Synthetic customer dataset", (5, 5), (2, 4),
        (
            "Prepared a classification checklist and mock export audit log.",
            "Estimated the scope of a fictional export using synthetic event records.",
            "Marked the mock export route as suspended for the training account.",
            "Recorded revocation of the fictional access grant that enabled the export.",
            "Validated mock export restrictions and resumed approved training workflows.",
            "Recorded improvements to data loss monitoring and approval controls.",
        ),
    ),
}
