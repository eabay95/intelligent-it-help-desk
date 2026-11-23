from collections import Counter
from itertools import combinations
import random
import unittest

from audit_licensed import near_duplicates, summarize


class LicensedAuditTest(unittest.TestCase):
    def test_prefix_filter_matches_brute_force(self):
        rng = random.Random(42)
        keys = Counter()
        for _ in range(35):
            words = [str(rng.randrange(12)) for _ in range(12)]
            keys[" ".join(words)] += 2
            keys[" ".join(words + ["tail"])] += 1
            keys[" ".join(words[1:])] += 3
        grams = {}
        for key in keys:
            words = key.split()
            grams[key] = set(zip(words, words[1:], words[2:]))
        affected = set()
        pairs = 0
        for left, right in combinations(grams, 2):
            shared = len(grams[left] & grams[right])
            if shared >= 3 and 5 * shared >= 4 * len(grams[left] | grams[right]):
                pairs += 1
                affected.update((left, right))
        self.assertEqual(near_duplicates(keys), {
            "distinct_text_pairs": pairs,
            "affected_rows": sum(keys[key] for key in affected),
        })

    def test_counts_coverage_and_privacy_without_disclosing_text(self):
        text = "VPN password reset contact test@example.invalid"
        rows = [(text, "Access"), (text.upper(), "Hardware"), ("", None)]
        result = summarize(rows, 0)
        self.assertEqual(result["missing_text_rows"], 1)
        self.assertEqual(result["normalized_duplicate_excess"], 1)
        self.assertEqual(result["normalized_conflicting_label_groups"], 1)
        self.assertEqual(result["sensitive_pattern_row_counts"]["email"], 2)
        self.assertEqual(result["terms_by_source_label"]["VPN"]["Access"], 1)
        self.assertNotIn("example.invalid", str(result))


if __name__ == "__main__":
    unittest.main()
