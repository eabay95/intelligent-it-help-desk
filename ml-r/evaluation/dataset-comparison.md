# Current corpus versus the replacement candidate

| Dimension | Current corpus | Replacement candidate |
| --- | --- | --- |
| Provenance | 2,229 anonymized operational tickets from one Brazilian IT provider, with CC BY 4.0 and a published split | 625 English synthetic rows, generated from 125 fixed templates, with no verified data reuse grant |
| Category definitions | Five mapped application classes. Network is sourced from Fileservice. Other includes Support general and EOL. | Four shared routing classes and Security. No General or Other class. |
| Network coverage | 546 mapped Network train rows. 470 contain `file`. None mention VPN, Wi-Fi variants, or DNS under the current audit. | 125 rows from 25 Network templates, including four VPN, six Wi-Fi, and two DNS templates under the candidate audit. |
| Balance | Train counts 84 Account Access, 65 Hardware, 546 Network, 586 Other, and 291 Software | 125 rows and 25 templates per source category |
| Exact normalized duplication | 660 excess copies out of 1,572 train rows (42.0%), plus 129 out of 657 test rows (19.6%). 161 test rows overlap training. | 9 excess copies out of 625 rows (1.4%). Every row shares its generator template with four other rows. |
| Near-only trigram duplication | 116 train pairs, 65 test pairs, and 139 cross-split pairs | 114 pairs involving 205 rows across the single CSV |
| Linguistic diversity and realism | Multilingual operational language, variable detail and noisy forwarding templates | Short, polished English, explicit product or symptom names, and repeated wrappers. It provides technical coverage with limited incident diversity. |
| Label consistency | Two normalized-text groups disagree across mapped labels. VPN and DNS failures can be labeled Other. | Zero conflicting normalized-text labels and zero generator-label mismatches. Agreement with the generator does not establish routing correctness. |

The new corpus covers missing VPN, Wi-Fi, and DNS concepts and adds password, MFA, and crash examples. It leaves general requests uncovered, labels Security outside our taxonomy, and offers almost no printer coverage. It could inform the design of a newly authored, rights-cleared review set. Combining the CSV with the current corpus is unjustified on both permission and evidence grounds. The added rows would contribute fixed English templates while inheriting incompatible class definitions. No candidate metrics establish improved operational routing. [Current corpus audit](dataset-notes.md) · [Replacement audit](new-dataset-audit.md)
