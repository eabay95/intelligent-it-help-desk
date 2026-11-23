import csv
from pathlib import Path
import tempfile
import unittest

from audit_replacement import audit, normalize, trigram_pairs


class AuditTest(unittest.TestCase):
    def test_normalizes_without_executing_generator(self):
        self.assertEqual(normalize(" WI-Fi [NAME] é! "), "wi fi é")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            generator = root / "generate_data.py"
            generator.write_text(
                'CATEGORIES = {"Network": ["VPN disconnects at the gateway"]}\n'
                'PREFIXES = ["", "Urgent: "]\nSUFFIXES = [""]\n'
                'raise RuntimeError("Generator must not execute")\n',
                encoding="utf-8",
            )
            fixture = root / "tickets.csv"
            with fixture.open("w", newline="", encoding="utf-8") as stream:
                csv.writer(stream).writerows([
                    ["text", "label"],
                    ["VPN disconnects at the gateway", "Network"],
                    ["VPN DISCONNECTS at the gateway.", "Network"],
                    ["Urgent: VPN disconnects at the gateway", "Hardware"],
                    ["Unrelated", "Hardware"],
                ])
            report = audit(fixture, generator)
        self.assertEqual(report["matched_rows"], 3)
        self.assertEqual(report["normalized_duplicate_excess"], 1)
        self.assertEqual(report["template_label_mismatches"], 1)
        self.assertEqual(report["unmatched_rows"], 1)
        self.assertEqual(report["observed_templates_by_label"], {"Network": 1})

    def test_trigram_similarity_excludes_exact_match_and_short_overlap(self):
        key = "one two three four five six seven eight nine"
        keys = [key, key, key + " ten", "one two three"]
        self.assertEqual(list(trigram_pairs(keys)), [(0, 2), (1, 2)])


if __name__ == "__main__":
    unittest.main()
