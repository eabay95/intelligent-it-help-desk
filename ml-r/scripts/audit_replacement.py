"""Audit an unlicensed candidate in temporary storage. Emit aggregate statistics only."""
import argparse
import ast
from collections import Counter, defaultdict
import csv
from hashlib import sha256
from itertools import combinations, product
import json
from pathlib import Path
import random
import re
import unicodedata

TERMS = {
    "vpn": r"\bvpn\b",
    "wifi": r"\b(?:wi[ -]?fi|wireless|wlan)\b",
    "dns": r"\bdns\b|\bdns_",
    "password": r"\bpassword\b",
    "login": r"\b(?:log[ -]?in|sign[ -]?in|sso)\b",
    "mfa": r"\b(?:mfa|2fa|multi[ -]?factor|two[ -]?factor|authenticator)\b",
    "laptop": r"\blaptop\b",
    "printer": r"\bprinter\b",
    "crash": r"\bcrash(?:es|ed|ing)?\b",
}


def normalize(text):
    text = unicodedata.normalize("NFC", text).casefold()
    text = re.sub(r"\[[^\[\]]+\]", " ", text)
    return " ".join(re.findall(r"[^\W_]+", text))


def read_literals(path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    literals = {}
    for statement in tree.body:
        if not isinstance(statement, ast.Assign):
            continue
        for target in statement.targets:
            if isinstance(target, ast.Name) and target.id in {"CATEGORIES", "PREFIXES", "SUFFIXES"}:
                literals[target.id] = ast.literal_eval(statement.value)
    return literals["CATEGORIES"], literals["PREFIXES"], literals["SUFFIXES"]


def trigram_pairs(keys):
    grams = [set(zip(words, words[1:], words[2:])) for words in map(str.split, keys)]
    for left, right in combinations(range(len(keys)), 2):
        if keys[left] == keys[right]:
            continue
        shared = len(grams[left] & grams[right])
        if shared >= 3 and shared / (len(grams[left]) + len(grams[right]) - shared) >= 0.8:
            yield left, right


def audit(csv_path, generator):
    variants = defaultdict(set)
    templates, prefixes, suffixes = read_literals(generator)
    for label, bodies in templates.items():
        for index, body in enumerate(bodies, 1):
            for prefix, suffix in product(prefixes, suffixes):
                variants[normalize(prefix + body + suffix)].add((label, index))

    with csv_path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["text", "label"]:
            raise ValueError("Expected exactly text and label columns.")
        rows = list(reader)
    if any(None in row or row["text"] is None or row["label"] is None for row in rows):
        raise ValueError("CSV contains malformed records.")
    keys = [normalize(row["text"]) for row in rows]
    raw = [row["text"] for row in rows]
    labels = [row["label"] for row in rows]
    unique = defaultdict(set)
    groups = Counter()
    assignments = {}
    for index, (key, label) in enumerate(zip(keys, labels)):
        unique[key].add(label)
        matches = variants[key]
        if len(matches) == 1:
            group = next(iter(matches))
            groups[group] += 1
            assignments[index] = group
    pairs = list(trigram_pairs(keys))
    duplicate_counts = Counter(keys)
    lengths = sorted(len(key.split()) for key in keys)
    rng = random.Random(42)
    partitions = defaultdict(set)
    for label in sorted(set(labels)):
        indices = [i for i, value in enumerate(labels) if value == label]
        rng.shuffle(indices)
        n = round(len(indices) * 0.15)
        for position, index in enumerate(indices):
            if index in assignments:
                partitions[assignments[index]].add(
                    "test" if position < n else "validation" if position < 2 * n else "train"
                )

    return {
        "sha256": sha256(csv_path.read_bytes()).hexdigest(),
        "columns": ["text", "label"],
        "rows": len(rows),
        "labels": dict(sorted(Counter(labels).items())),
        "empty_text": sum(not text.strip() for text in raw),
        "empty_label": sum(not label.strip() for label in labels),
        "normalized_empty": sum(not key for key in keys),
        "exact_duplicate_excess": len(raw) - len(set(raw)),
        "exact_row_duplicate_excess": len(raw) - len(set(zip(raw, labels))),
        "normalized_duplicate_excess": len(keys) - len(set(keys)),
        "rows_in_normalized_duplicate_groups": sum(n for n in duplicate_counts.values() if n > 1),
        "conflicting_normalized_labels": sum(len(values) > 1 for values in unique.values()),
        "near_only_pairs": len(pairs),
        "near_only_rows": len({index for pair in pairs for index in pair}),
        "word_count_min_median_max": [
            min(lengths),
            (lengths[(len(lengths) - 1) // 2] + lengths[len(lengths) // 2]) / 2,
            max(lengths),
        ],
        "generator_templates": {label: len(bodies) for label, bodies in templates.items()},
        "generator_prefix_count": len(prefixes),
        "generator_suffix_count": len(suffixes),
        "matched_rows": len(assignments),
        "unmatched_rows": sum(not variants[key] for key in keys),
        "ambiguous_template_rows": sum(len(variants[key]) > 1 for key in keys),
        "template_label_mismatches": sum(group[0] != labels[i] for i, group in assignments.items()),
        "observed_templates_by_label": dict(sorted(Counter(label for label, _ in groups).items())),
        "template_group_size_distribution": dict(sorted(Counter(groups.values()).items())),
        "groups_spanning_simulated_random_partitions": sum(len(parts) > 1 for parts in partitions.values()),
        "test_groups_also_in_simulated_train": sum({"train", "test"} <= parts for parts in partitions.values()),
        "simulated_test_groups": sum("test" in parts for parts in partitions.values()),
        "term_coverage": {
            term: {label: sum(bool(re.search(pattern, text, re.IGNORECASE))
                             for text, value in zip(raw, labels) if value == label)
                   for label in sorted(set(labels))}
            for term, pattern in TERMS.items()
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("generator_path", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.csv_path, args.generator_path), indent=2))
