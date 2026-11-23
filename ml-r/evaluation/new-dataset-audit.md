# Replacement ticket dataset audit

**Eligibility: audit only. Recommendation: Reject this snapshot as a replacement or training supplement.** The public repository has no detected license in GitHub metadata. The pinned tree contained no license, copyright, notice, or attribution file by filename, and the README, config, and generator gave no reuse grant covering the CSV. I found neither a code license nor a separate data license. A future code license would need to explicitly cover the dataset, or be accompanied by a data license or written permission. Public visibility and synthetic generation alone establish no training or redistribution permission. The downloaded files stayed in a temporary audit directory outside the repository. No third-party code or model was executed. [Pinned repository](https://github.com/KS-Adharshini/SLM-Support-Ticket-Classifier/tree/af5e9e7e5823b9b599df5b1f2bbb8d399fc3816d) · [GitHub licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)

## Snapshot and provenance

| Item | Finding |
| --- | --- |
| Commit | `af5e9e7e5823b9b599df5b1f2bbb8d399fc3816d` |
| CSV SHA-256 | `e88c6b6dcb23b376c0c7ff8f329ac7423002b84ec128aab8a663501ecd25eec9` |
| Schema | `text`, `label`. No independent title, reporter, incident ID, timestamp, or severity. |
| Rows | **625** in the actual CSV. The README says 616, which is also the number of unique exact texts after removing nine excess copies. |
| Classes | Account / Access, Hardware, Network, Security, Software. **125 each**, 20% apiece. |
| Completeness | Zero blank texts, blank labels, or texts empty after normalization. All rows had the expected fields. |
| Text length | 8–25 normalized words, with median 18. |

The generator declares 25 fixed base sentences per category, 10 prefixes, and 9 suffixes. It chooses prefix/suffix combinations with a default seed of 42, generates five variants per template, and shuffles the rows. A literal-only audit matched all 625 CSV texts uniquely to those declared templates after normalization. All 125 templates occurred five times, and assigned template labels agreed with the CSV. The source provides no independent human adjudication or evidence of employee submissions. The configuration names the correct CSV columns and specifies 15% test and 15% validation. Its confidence threshold is an inference setting, not a data quality signal. [CSV](https://github.com/KS-Adharshini/SLM-Support-Ticket-Classifier/blob/af5e9e7e5823b9b599df5b1f2bbb8d399fc3816d/data/tickets.csv) · [Generator](https://github.com/KS-Adharshini/SLM-Support-Ticket-Classifier/blob/af5e9e7e5823b9b599df5b1f2bbb8d399fc3816d/data/generate_data.py) · [README](https://github.com/KS-Adharshini/SLM-Support-Ticket-Classifier/blob/af5e9e7e5823b9b599df5b1f2bbb8d399fc3816d/README.md) · [Config](https://github.com/KS-Adharshini/SLM-Support-Ticket-Classifier/blob/af5e9e7e5823b9b599df5b1f2bbb8d399fc3816d/config.yaml)

## Duplication and wording

- There are 9 excess exact copies and 9 excess normalized copies. Eighteen rows belong to normalized duplicate groups. Zero normalized-text groups contain conflicting labels.
- A near-only match has different normalized text, at least three shared distinct word trigrams, and trigram Jaccard similarity of at least 0.80. This finds **114 pairs involving 205 rows**. Template matching captures repetition that Jaccard misses when wrappers change.
- In our seed-42 simulation of a stratified row-wise 70/15/15 split with per-class rounding, **102 of 125 template groups spanned partitions**. All **72 groups represented in test also appeared in train**. This measures leakage risk under the simulated split, without reproducing or evaluating the source model.
- Standard urgency, productivity, and restart boilerplate appears across unrelated incidents. App names and explicit error messages provide useful variety, but within each template the problem statement stays fixed. Balanced row counts conceal the limited variety of genuinely distinct incidents.

## Coverage and review flags

| Issue | Actual CSV evidence |
| --- | --- |
| VPN | 20 Network rows from four templates. They cover a repeatedly dropping tunnel, connection rejection, and other VPN contexts. |
| Wi-Fi | 30 Network rows from six templates and five Hardware rows from one template. Physical adapter failure and wireless service failure deserve different labels. |
| DNS | 10 Network rows from two templates, using the DNS acronym or an error code beginning with it. |
| Password, login, MFA | Account / Access has 15 password, 10 login/SSO, and 15 MFA-pattern matches. Security also includes password and MFA mentions in incident contexts. |
| Laptops, printers | 45 Hardware rows mention laptops. Five rows mention a printer, all variants of one Network printer-reachability template. There are no Hardware printer mentions under this audit pattern. |
| Software crashes | 30 Software rows from six templates mention a crash or crashing. |

Counts are term-pattern matches and can overlap. Representative generator review supports Network for VPN drops and DNS resolution, Account Access for password reset and MFA enrollment, Hardware for physical laptop or drive faults, and Software for application crashes. Flag printer IP reachability, an unrecognized MFA token, and endpoint protection blocking a build tool for human review because the symptoms cross team boundaries. Phishing and malware reports require explicit Security escalation. See the [mapping and adjudication guidance](label-mapping.md). [Template source](https://github.com/KS-Adharshini/SLM-Support-Ticket-Classifier/blob/af5e9e7e5823b9b599df5b1f2bbb8d399fc3816d/data/generate_data.py)

High-severity findings are missing permission, template leakage, and taxonomy gaps for Other and Security. Medium-severity findings include short polished English sentences and limited physical-printer coverage. Aggregate output is available in [audit JSON](replacement-audit.json).
