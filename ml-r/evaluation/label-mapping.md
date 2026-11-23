# Proposed label mapping

Use this proposal for human review. The production category and team configuration stay in place.

| Replacement label | Existing application label | Review rule |
| --- | --- | --- |
| Network | Network | Connectivity, VPN tunnel failures, Wi-Fi service and DNS. Separate access entitlement from transport failure. |
| Hardware | Hardware | Physical part failure. Confirm whether a peripheral symptom persists off the network. |
| Software | Software | Application, OS and installation failures. Review reported security detections separately. |
| Account / Access | Account Access | Credentials, MFA enrollment, identity-provider and permission issues. Escalate suspected compromise. |
| Security | No automatic mapping | Track explicitly as a research label. Review for security escalation. |
| No source equivalent | Other | Collect general requests and cases with insufficient information for a more specific route. |

A separate Security category is operationally justified if there is a staffed incident queue, an escalation playbook, and reviewed labels covering the queue's boundaries. Phishing, malware, suspicious activity, and possible disclosure can need urgent specialized handling. Combining them with Other would hide the escalation signal and invalidate cross-corpus comparisons. For future five-class experiments, report Security exclusions and measure it separately in a human-reviewed escalation set. A taxonomy change would require its own review of the workflow and API.

| Representative case | Adjudication guidance |
| --- | --- |
| VPN tunnel drops or DNS resolution fails | Network when the transport or resolver is failing. An explicit denial of VPN entitlement may be Account Access. |
| Wi-Fi adapter visibly damaged | Hardware. Repeated roaming or association failure can be Network. |
| Password reset, MFA enrollment, sign-in loop | Account Access for routine identity recovery. A suspicious MFA prompt or sign-in attempt should be flagged for Security escalation. A sign-in loop can also be application-specific. |
| Laptop display damage, power fault, or mechanical drive clicking | Hardware. |
| Printer IP unreachable on guest Wi-Fi | Network is plausible. Confirm whether network policy or a broken or misconfigured printer owns the issue. An actual feed jam would be Hardware. |
| Application crash or installer rollback | Software. A security tool blocking a build needs review to distinguish policy enforcement from a software defect or suspected incident. |

Use [the blank review worksheet](human-review-template.csv) in approved storage. Assign a stable group identifier for duplicate incidents and templates. Have reviewers independently record their category, adjudicate disagreements including escalation, and record the expected team. Freeze the reserved holdout groups before training. Use redacted text and a provenance reference. Keep populated worksheets and sensitive tickets outside Git. No reviewed labels are included in the template.
