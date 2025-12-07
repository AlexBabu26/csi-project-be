from pathlib import Path
from typing import Iterable, Sequence

from openpyxl import Workbook

from app.common.config import get_settings
from app.common.storage import ensure_dir

settings = get_settings()


def write_rows_to_xlsx(headers: Sequence[str], rows: Iterable[Sequence], filename: str) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.append(list(headers))
    for row in rows:
        ws.append(list(row))
    dest_dir = ensure_dir(settings.export_dir)
    path = dest_dir / filename
    wb.save(path)
    return path

