# Label mapping and coverage

The production taxonomy stays Network, Hardware, Software, Account Access, and Other. These are proposed review rules. Every crosswalk requires the issue context.

| Candidate | Source label or unit | Proposed treatment |
| --- | --- | --- |
| A. Mendeley | Ticket, Service, HD Service, Deployment, and remaining workflow types | Keep as metadata. Manually label the first usable reporter issue. Deployment may relate to Software, but can also be an administrative workflow. Vacation, Project, and sprint types are generally out of scope. |
| B. Kaggle | Access, Administrative rights | Review for Account Access when identity, entitlement, or permission is the issue. Application error or hardware purchase mentions in the same queue do not establish that route. |
| B. Kaggle | Hardware | Review for Hardware where physical faults dominate. Connectivity, peripherals, OS symptoms, and purchases are ambiguous. |
| B. Kaggle | Storage | Review reachability for Network, permission for Account Access, and physical disk failure for Hardware. Keep other storage work outside automatic mapping. |
| B. Kaggle | Miscellaneous | Review case-by-case. Other requires a general IT request that fits the help desk's scope. |
| B. Kaggle | HR Support, Purchase, Internal Project | Exclude from automatic mapping. Route manually if the underlying request actually matches a production category. |
| C. Mack | User prompts | Treat as unlabeled. Review actionable issue prompts across the five categories. Drop persona, generic tutorials, off-topic questions, and policy/incident cases requiring a different queue. |
| C. Mack | Assistant tags and answers | Exclude as training features and ground truth. Their text can leak the intended answer and the tags do not consistently represent this taxonomy. |

## Network and adjacent coverage

| Text population | VPN | Wi-Fi range | DNS | Hardware terms | Software terms | Account Access terms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A. All sampled utterances | 10 | 0 | 18 | 50 | 1,760 | 88 |
| A. First public reporter comments | 0 | 0 | 0 | 3 | 27 | 14 |
| B. Kaggle documents | 0 | 409 | 0 | 3,752 | 9,123 | 1,840 |
| C. Mack user prompts | 4,794 | 1,448 | 1,126 | 9,175 | 11,252 | 4,533 |

Counts are rows containing term patterns with overlaps allowed. The Wi-Fi pattern includes wireless and WLAN, which can describe hardware peripherals. In Kaggle, 249 of its 409 matches sit under Hardware. The rest span all seven other source labels. The release has no Network target, so operational Network recall cannot be estimated from these labels. Mendeley exposes a handful of Network mentions in later conversational material, and its issue types and first-comment sample offer insufficient Network supervision. Mack supplies broad candidates for annotation. Its repeated prompts reduce independence.

After exact normalization, Mack has 3,174 distinct VPN-matching prompts, 1,047 Wi-Fi matches, and 640 DNS matches. These counts still include near-duplicates and questions that do not describe incidents. The existing Network label is largely Fileservice, with zero VPN, Wi-Fi, or DNS mentions in its Network training slice under the older audit. These candidate gaps explain why merging datasets by label name or keywords would not fix the VPN error. [Existing dataset audit](dataset-notes.md) · [Aggregate candidate term counts by source label](licensed-audit.json)
