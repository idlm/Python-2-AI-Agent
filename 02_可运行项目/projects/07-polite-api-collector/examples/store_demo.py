"""项目 7 JSONL 存储的无网络端到端演示。"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile

from polite_api_collector import CollectedPage, CollectionStore


def main() -> None:
    root = Path(tempfile.mkdtemp(prefix="course-collector-store-"))
    try:
        store = CollectionStore(root)
        pages = [CollectedPage("catalog", "/v1/catalog", {"items": ["one", "two"]})]
        first = store.append_pages(pages, source="approved-catalog", collected_at="2026-08-26T00:00:00+00:00")
        second = store.append_pages(pages, source="approved-catalog", collected_at="2026-08-26T00:00:00+00:00")
        records = CollectionStore(root).load_records()
        store.manifest_path.unlink()
        recovered = CollectionStore(root).recover_manifest()
        print(
            json.dumps(
                {
                    "first_added": first.added,
                    "duplicate_skipped": second.skipped_duplicates,
                    "loaded_record_count": len(records),
                    "recovered_record_count": recovered["record_count"],
                    "records_exists": store.records_path.exists(),
                    "manifest_exists": store.manifest_path.exists(),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    main()
