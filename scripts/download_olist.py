"""Download only the three official Olist files needed by the dashboard."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen
from zipfile import ZipFile, is_zipfile
import json

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data/raw/olist"
FILES = ["olist_orders_dataset.csv", "olist_order_items_dataset.csv", "olist_customers_dataset.csv"]


def download(name):
    DEST.mkdir(parents=True, exist_ok=True)
    url = f"https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce/{name}?datasetVersionNumber=2"
    request = Request(url, headers={"User-Agent": "BANA409-assignment/1.0"})
    with urlopen(request, timeout=180) as response:
        body = response.read()
    stream = BytesIO(body)
    if is_zipfile(stream):
        with ZipFile(stream) as archive:
            matches = [p for p in archive.namelist() if Path(p).name == name]
            if len(matches) != 1:
                raise ValueError(f"Expected exactly one {name} in archive")
            body = archive.read(matches[0])
    header = body.splitlines()[0].replace(b'"', b'').lstrip(b'\xef\xbb\xbf')
    if not header.startswith((b"order_id,", b"customer_id,")):
        raise ValueError(f"Unexpected response for {name}: {header[:100]!r}")
    (DEST / name).write_bytes(body)
    result = {"file": name, "url": url, "bytes": len(body), "sha256": sha256(body).hexdigest()}
    print(f"Downloaded {name}: {len(body):,} bytes", flush=True)
    return result


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(download, FILES))
    (ROOT / "evidence/source_files.json").write_text(json.dumps(records, indent=2) + "\n")
