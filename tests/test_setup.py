from __future__ import annotations

import hashlib
import json
import zipfile

from src.data.setup import setup_dataset


def _source_text() -> str:
    rows = []
    for _row in range(149):
        values = ["1.0"] * 144
        rows.append(" ".join(values))
    return "\n".join(rows) + "\n"


def test_setup_extracts_verifies_and_caches(tmp_path):
    names = [
        "Train_Dst_NoAuction_DecPre_CF_7.txt",
        "Test_Dst_NoAuction_DecPre_CF_7.txt",
        "Test_Dst_NoAuction_DecPre_CF_8.txt",
        "Test_Dst_NoAuction_DecPre_CF_9.txt",
    ]
    archive = tmp_path / "fi2010.zip"
    contents = {}
    with zipfile.ZipFile(archive, "w") as output:
        for name in names:
            text = _source_text().encode()
            contents[name] = text
            output.writestr(f"nested/{name}", text)
    manifest = {
        "files": [
            {
                "name": name,
                "size": len(contents[name]),
                "sha256": hashlib.sha256(contents[name]).hexdigest(),
            }
            for name in names
        ]
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    root = tmp_path / "raw"
    cache = tmp_path / "processed"

    assert (
        setup_dataset(
            archive=archive,
            root=root,
            manifest_path=manifest_path,
            cache_root=cache,
        )
        == []
    )
    assert sorted(path.name for path in root.glob("*.txt")) == sorted(names)
    assert (cache / "Train_Dst_NoAuction_DecPre_CF_7.npz").is_file()
    assert (cache / "Train_Dst_NoAuction_DecPre_CF_7.json").is_file()
