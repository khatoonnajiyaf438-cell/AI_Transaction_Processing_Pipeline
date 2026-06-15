from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class CleanedTransaction:
    txn_id: str | None
    date: date | None
    merchant: str
    amount: Decimal
    currency: str
    status: str
    category: str
    original_category_missing: bool
    account_id: str
    notes: str | None


class CleaningError(ValueError):
    pass


def clean_transactions(rows: list[dict[str, str]]) -> list[CleanedTransaction]:
    cleaned: list[CleanedTransaction] = []
    seen: set[tuple[str, ...]] = set()

    for index, row in enumerate(rows, start=2):
        canonical = tuple((row.get(column, "") or "").strip() for column in sorted(row))
        if canonical in seen:
            continue
        seen.add(canonical)

        amount = _parse_amount(row.get("amount", ""), index)
        category_raw = (row.get("category") or "").strip()
        transaction = CleanedTransaction(
            txn_id=(row.get("txn_id") or "").strip() or None,
            date=_parse_date(row.get("date", ""), index),
            merchant=(row.get("merchant") or "").strip(),
            amount=amount,
            currency=((row.get("currency") or "INR").strip().upper() or "INR"),
            status=((row.get("status") or "PENDING").strip().upper() or "PENDING"),
            category=category_raw or "Uncategorised",
            original_category_missing=not bool(category_raw),
            account_id=(row.get("account_id") or "UNKNOWN").strip() or "UNKNOWN",
            notes=(row.get("notes") or "").strip() or None,
        )
        cleaned.append(transaction)

    return cleaned


def _parse_amount(value: str, row_number: int) -> Decimal:
    normalised = (value or "0").replace("$", "").replace(",", "").strip()
    try:
        return Decimal(normalised).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise CleaningError(f"Invalid amount at row {row_number}: {value!r}") from exc


def _parse_date(value: str, row_number: int) -> date | None:
    if not value:
        return None

    for date_format in ("%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value.strip(), date_format).date()
        except ValueError:
            continue
    raise CleaningError(f"Invalid date at row {row_number}: {value!r}")
