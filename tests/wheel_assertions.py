from __future__ import annotations

import base64
import csv
import hashlib
import zipfile
from pathlib import Path, PurePosixPath


def assert_wheel_record(wheel: Path) -> None:
    with zipfile.ZipFile(wheel) as archive:
        records = [
            name
            for name in archive.namelist()
            if name.endswith(".dist-info/RECORD")
            and len(PurePosixPath(name).parts) == 2
        ]
        assert len(records) == 1
        record_name = records[0]
        rows = list(csv.reader(archive.read(record_name).decode().splitlines()))
        files = {name for name in archive.namelist() if not name.endswith("/")}
        row_names = [row[0] for row in rows]
        assert len(row_names) == len(set(row_names))
        assert set(row_names) == files
        for name, digest, size in rows:
            if name == record_name:
                assert (digest, size) == ("", "")
                continue
            value = archive.read(name)
            encoded = base64.urlsafe_b64encode(hashlib.sha256(value).digest())
            assert digest == f"sha256={encoded.rstrip(b'=').decode()}"
            assert size == str(len(value))
