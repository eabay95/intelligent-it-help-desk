"""Fetch the four pinned publisher inputs to a temporary directory."""
from hashlib import sha256
from pathlib import Path
import tempfile
from urllib.request import Request, urlopen

MENDELEY = "https://data.mendeley.com/public-files/datasets/btm76zndnt/files/"
HUGGING_FACE = "https://huggingface.co/datasets/benjaminmacklin/IT_Support_V2/resolve/"
FILES = {
    "issues.csv": (
        MENDELEY + "2018b884-181a-482b-8a06-a86bbf41f4e7/file_downloaded",
        "eab3b8857bc19bd917e0767fb9c30b7714d5468b25c5a1c1cd71a760e9602f02",
    ),
    "sample_utterances.csv": (
        MENDELEY + "4e1eec04-5c2f-44f5-a855-690519f57f4d/file_downloaded",
        "6486067634164a8d9fc361887b9b700965e704c9b03c87ef4e19275cccf30196",
    ),
    "kaggle.zip": (
        "https://www.kaggle.com/api/v1/datasets/download/adisongoh/"
        "it-service-ticket-classification-dataset?datasetVersionNumber=1",
        "1e6c2508dba84f737ef30f589c2e4f7b2b27a4bbec753e6b5c84183a5f91ed4f",
    ),
    "mack.jsonl": (
        HUGGING_FACE + "bbaf7b99593a9492594d5be414619c1ad33e1730/Mack_training_data%20.jsonl",
        "81b38a8b0890702ef263379447cecae93431f1ee89596784649f61d6f2ba5f11",
    ),
}


def fetch(destination):
    destination.mkdir(parents=True, exist_ok=True)
    for name, (url, expected) in FILES.items():
        path = destination / name
        if path.exists():
            contents = path.read_bytes()
        else:
            request = Request(url, headers={"User-Agent": "helpdesk-dataset-audit"})
            with urlopen(request, timeout=120) as response:
                contents = response.read()
        if sha256(contents).hexdigest() != expected:
            raise ValueError(f"{name} does not match the audited release digest")
        if not path.exists():
            path.write_bytes(contents)
        print(f"Verified {name}")


if __name__ == "__main__":
    root = Path(tempfile.gettempdir()).resolve() / "helpdesk-licensed-audit"
    fetch(root)
