import csv
from pathlib import Path

REQUIRED_COLUMNS = {
    "txn_id",
    "date",
    "merchant",
    "amount",
    "currency",
    "status",
    "category",
    "account_id",
    "notes",
}


class CSVValidationError(ValueError):
    pass


def read_transactions(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames:
            raise CSVValidationError("CSV file is empty or missing a header row.")

        columns = {column.strip() for column in reader.fieldnames}
        missing = REQUIRED_COLUMNS - columns
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise CSVValidationError(f"CSV is missing required columns: {missing_list}.")

        rows: list[dict[str, str]] = []
        for row in reader:
            rows.append({key.strip(): (value or "").strip() for key, value in row.items() if key})

    if not rows:
        raise CSVValidationError("CSV file has no data rows.")
    return rows
