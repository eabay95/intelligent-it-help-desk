"""Audit pinned publisher files from a local directory. Output aggregate data only."""
import argparse
from collections import Counter, defaultdict
import csv
from hashlib import sha256
import io
import json
from math import ceil
from pathlib import Path
import random
import re
import statistics
import zipfile

from audit_replacement import normalize

TERMS = {
    "VPN": r"\bvpn\b|\banyconnect\b",
    "Wi-Fi": r"\b(?:wi[\s-]*fi|wireless|wlan)\b",
    "DNS": r"(?<![a-z0-9])dns(?![a-z0-9])|\bnxdomain\b",
    "Hardware": r"\b(?:hardware|laptop|battery|printer|monitor|keyboard|touchpad|hard drive)\b",
    "Software": r"\b(?:software|application|install\w*|crash\w*|update\w*)\b",
    "Account Access": r"\b(?:password|log[\s-]?in|sign[\s-]?in|mfa|2fa|sso|lockout|authentication)\b",
}
INDICATORS = {
    "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    "ipv4": r"(?<![\w.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\w.])",
    "phone_format": r"(?<![\w.])(?:\+\d{1,3}[ .-]?)?(?:\(\d{3}\)|\d{3})[ .-]\d{3}[ .-]\d{4}(?![\w.])",
    "credential_assignment": r"\b(?:password|passwd|api[_ -]?key|client[_ -]?secret)\s*[:=]\s*[^\s<>{}\[\]]{4,}",
    "url": r"https?://[^\s<>]+",
}
PATTERNS = {name: re.compile(pattern, re.IGNORECASE) for name, pattern in INDICATORS.items()}
TERMS = {name: re.compile(pattern, re.IGNORECASE) for name, pattern in TERMS.items()}


def template_key(text):
    for name in ("url", "email", "ipv4", "phone_format"):
        text = PATTERNS[name].sub(" identifier ", text)
    return normalize(re.sub(r"\d+", " number ", text))


def near_duplicates(key_counts, key_labels=None):
    """Exact prefix-filtered Jaccard search over distinct normalized texts."""
    grams = []
    frequencies = Counter()
    for key in key_counts:
        words = key.split()
        shingle = set(zip(words, words[1:], words[2:]))
        grams.append(shingle)
        frequencies.update(shingle)
    index = defaultdict(list)
    participants = set()
    pair_count = 0
    different_labels = 0
    keys = list(key_counts)
    for i, shingles in enumerate(grams):
        size = len(shingles)
        if size < 3:
            continue
        prefix = sorted(shingles, key=lambda gram: (frequencies[gram], gram))[:size // 5 + 1]
        possibilities = {other for gram in prefix for other in index[gram]}
        for other in possibilities:
            previous = grams[other]
            if 5 * min(size, len(previous)) < 4 * max(size, len(previous)):
                continue
            shared = len(shingles & previous)
            if shared >= 3 and 5 * shared >= 4 * (size + len(previous) - shared):
                pair_count += 1
                participants.update((i, other))
                if key_labels is not None:
                    current_labels = key_labels.get(keys[i], set())
                    previous_labels = key_labels.get(keys[other], set())
                    if current_labels and previous_labels and current_labels.isdisjoint(previous_labels):
                        different_labels += 1
        for gram in prefix:
            index[gram].append(i)
    result = {"distinct_text_pairs": pair_count, "affected_rows": sum(
        count for i, count in enumerate(key_counts.values()) if i in participants
    )}
    if key_labels is not None:
        result["pairs_with_disjoint_source_labels"] = different_labels
    return result


def languages(texts, sample_size):
    if sample_size == 0 or not texts:
        return {"sample_rows": 0, "counts": {}}
    from langdetect import DetectorFactory, LangDetectException, detect_langs

    DetectorFactory.seed = 42
    counts = Counter()
    sample = random.Random(42).sample(texts, min(len(texts), sample_size))
    for text in sample:
        if sum(char.isalpha() for char in text) < 25:
            counts["undetermined"] += 1
            continue
        try:
            scores = detect_langs(text[:2000])
            language = scores[0].lang if scores and scores[0].prob >= 0.8 else "undetermined"
        except LangDetectException:
            language = "undetermined"
        counts[language] += 1
    return {"sample_rows": len(sample), "counts": counts}


def summarize(rows, sample_size):
    labels = Counter()
    texts = []
    raw = Counter()
    keys = Counter()
    templates = Counter()
    key_labels = defaultdict(set)
    coverage = defaultdict(Counter)
    distinct_coverage = defaultdict(set)
    sensitive = Counter()
    has_text = 0
    for text, label in rows:
        labels[label or "(unlabeled)"] += 1
        if not text.strip():
            continue
        has_text += 1
        for name, pattern in PATTERNS.items():
            sensitive[name] += bool(pattern.search(text))
        key = normalize(text)
        if not key:
            continue
        texts.append(text)
        raw[text] += 1
        keys[key] += 1
        templates[template_key(text)] += 1
        if label:
            key_labels[key].add(label)
        for name, pattern in TERMS.items():
            matched = bool(pattern.search(text))
            coverage[name][label or "(unlabeled)"] += matched
            if matched:
                distinct_coverage[name].add(key)
    lengths = sorted(map(len, texts))
    return {
        "rows": sum(labels.values()), "source_labels": labels,
        "missing_text_rows": sum(labels.values()) - has_text,
        "nonblank_normalized_rows": len(texts),
        "length_chars_min_p25_median_p75_max": [
            lengths[0], lengths[ceil(len(lengths) / 4) - 1], statistics.median(lengths),
            lengths[ceil(len(lengths) * 3 / 4) - 1], lengths[-1]
        ] if lengths else [],
        "exact_duplicate_excess": len(texts) - len(raw),
        "normalized_duplicate_excess": len(texts) - len(keys),
        "normalized_conflicting_label_groups": sum(len(group) > 1 for group in key_labels.values()),
        "near_duplicates": near_duplicates(keys, key_labels if key_labels else None),
        "masked_template_excess": len(texts) - len(templates),
        "masked_template_extra_matches_over_normalized": len(keys) - len(templates),
        "largest_masked_template_group": max(templates.values(), default=0),
        "language_estimate": languages(texts, sample_size),
        "sensitive_pattern_row_counts": sensitive, "terms_by_source_label": coverage,
        "distinct_normalized_term_texts": {
            term: len(distinct_coverage[term]) for term in TERMS
        },
    }


def mendeley(root, sample_size):
    with (root / "issues.csv").open(encoding="utf-8-sig", newline="") as stream:
        metadata = list(csv.DictReader(stream))
    issues = {row["id"]: row["issue_type"] for row in metadata}
    utterances = []
    first = {}
    with (root / "sample_utterances.csv").open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        for row in reader:
            utterances.append(row)
            if row["author_role"] == "reporter" and row["is_private"] == "0.0":
                issue = row["issueid"]
                position = int(float(row["comment_seq"]))
                if issue not in first or position < first[issue][0]:
                    first[issue] = (position, [])
                if position == first[issue][0]:
                    first[issue][1].append((int(float(row["utr_seq"])), row["actionbody"]))
    return {
        "issue_metadata_rows": len(metadata),
        "issue_metadata_duplicate_ids": len(metadata) - len(issues),
        "issue_types": Counter(row["issue_type"] for row in metadata),
        "issue_description_column": False,
        "issues_represented_in_utterances": len({row["issueid"] for row in utterances}),
        "utterances_without_issue_match": sum(row["issueid"] not in issues for row in utterances),
        "utterances_by_role": Counter(row["author_role"] for row in utterances),
        "private_flagged_utterances": sum(row["is_private"] == "1.0" for row in utterances),
        "utterances": summarize(
            ((row["actionbody"], issues.get(row["issueid"])) for row in utterances), sample_size
        ),
        "first_available_public_reporter_comments": summarize(
            ((" ".join(text for _, text in sorted(pieces)), issues.get(issue))
             for issue, (_, pieces) in first.items()), sample_size
        ),
    }


def kaggle(path, sample_size):
    with zipfile.ZipFile(path) as archive:
        name, = archive.namelist()
        with archive.open(name) as raw, io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as text:
            reader = csv.DictReader(text)
            if reader.fieldnames != ["Document", "Topic_group"]:
                raise ValueError("Unexpected Kaggle columns")
            return {"archive_member": name, "columns": reader.fieldnames, **summarize(
                ((row["Document"], row["Topic_group"]) for row in reader), sample_size
            )}


def mack(path, sample_size):
    users = []
    assistant_indicators = Counter()
    tag_counts = Counter()
    opening_patterns = Counter()
    with path.open(encoding="utf-8-sig") as stream:
        for line in stream:
            if not line.strip():
                continue
            item = json.loads(line)
            user, assistant = item["messages"]
            if (user["role"], assistant["role"]) != ("user", "assistant"):
                raise ValueError("Unexpected dialogue shape")
            prompt, reply = user["content"], assistant["content"]
            users.append((prompt, None))
            lead = re.match(r"^\s*(mack\b|resolve\b|fix\b|configure\b|explain\b|what\b)", prompt, re.I)
            if lead:
                opening_patterns[lead.group(1).lower()] += 1
            for name, pattern in PATTERNS.items():
                assistant_indicators[name] += bool(pattern.search(reply))
            if re.fullmatch(r"[a-z]{2,}(?:_[a-z]{2,})+", reply.strip()):
                tag_counts["snake_case_reply_rows"] += 1
    return {
        "columns": ["messages"], "user_opening_counts": opening_patterns,
        "assistant_pattern_row_counts": assistant_indicators,
        **tag_counts, **summarize(users, sample_size),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--language-sample", type=int, default=2000)
    args = parser.parse_args()
    root = args.directory
    count = args.language_sample
    if count < 0:
        parser.error("--language-sample must be nonnegative")
    inputs = ("issues.csv", "sample_utterances.csv", "kaggle.zip", "mack.jsonl")
    result = {"sha256": {name: sha256((root / name).read_bytes()).hexdigest() for name in inputs}}
    result["mendeley"] = mendeley(root, count)
    result["kaggle"] = kaggle(root / "kaggle.zip", count)
    result["mack"] = mack(root / "mack.jsonl", count)
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
