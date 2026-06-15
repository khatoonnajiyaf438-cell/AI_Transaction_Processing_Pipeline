from collections import defaultdict
from decimal import Decimal
from statistics import median

from app.services.cleaner import CleanedTransaction

DOMESTIC_ONLY_MERCHANTS = {"SWIGGY", "OLA", "IRCTC"}


def detect_anomalies(transactions: list[CleanedTransaction]) -> dict[int, list[str]]:
    by_account: dict[str, list[Decimal]] = defaultdict(list)
    for transaction in transactions:
        by_account[transaction.account_id].append(transaction.amount)

    account_medians = {
        account_id: Decimal(str(median(amounts))) for account_id, amounts in by_account.items() if amounts
    }

    anomalies: dict[int, list[str]] = {}
    for index, transaction in enumerate(transactions):
        reasons: list[str] = []
        account_median = account_medians.get(transaction.account_id, Decimal("0"))
        if account_median > 0 and transaction.amount > account_median * Decimal("3"):
            reasons.append(f"amount exceeds 3x account median ({account_median})")

        merchant_upper = transaction.merchant.upper()
        if transaction.currency == "USD" and any(brand in merchant_upper for brand in DOMESTIC_ONLY_MERCHANTS):
            reasons.append("USD used for domestic-only merchant")

        if transaction.notes and "SUSPICIOUS" in transaction.notes.upper():
            reasons.append("notes mention suspicious activity")

        if reasons:
            anomalies[index] = reasons

    return anomalies
