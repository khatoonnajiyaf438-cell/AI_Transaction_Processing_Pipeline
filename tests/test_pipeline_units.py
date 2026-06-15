from decimal import Decimal

from app.services.anomaly import detect_anomalies
from app.services.cleaner import clean_transactions


def test_clean_transactions_normalises_and_deduplicates_rows():
    rows = [
        {
            "txn_id": "T1",
            "date": "01-05-2026",
            "merchant": "Ola",
            "amount": "$120.50",
            "currency": "inr",
            "status": "success",
            "category": "",
            "account_id": "A1",
            "notes": "",
        },
        {
            "txn_id": "T1",
            "date": "01-05-2026",
            "merchant": "Ola",
            "amount": "$120.50",
            "currency": "inr",
            "status": "success",
            "category": "",
            "account_id": "A1",
            "notes": "",
        },
    ]

    cleaned = clean_transactions(rows)

    assert len(cleaned) == 1
    assert cleaned[0].amount == Decimal("120.50")
    assert cleaned[0].currency == "INR"
    assert cleaned[0].status == "SUCCESS"
    assert cleaned[0].category == "Uncategorised"


def test_detect_anomalies_flags_statistical_and_domestic_currency_issues():
    rows = [
        {
            "txn_id": "T1",
            "date": "2026/05/01",
            "merchant": "Swiggy",
            "amount": "100",
            "currency": "INR",
            "status": "SUCCESS",
            "category": "Food",
            "account_id": "A1",
            "notes": "",
        },
        {
            "txn_id": "T2",
            "date": "2026/05/02",
            "merchant": "Swiggy",
            "amount": "5000",
            "currency": "USD",
            "status": "SUCCESS",
            "category": "Food",
            "account_id": "A1",
            "notes": "",
        },
        {
            "txn_id": "T3",
            "date": "2026/05/03",
            "merchant": "Amazon",
            "amount": "120",
            "currency": "INR",
            "status": "SUCCESS",
            "category": "Shopping",
            "account_id": "A1",
            "notes": "",
        },
    ]

    anomalies = detect_anomalies(clean_transactions(rows))

    assert 1 in anomalies
    assert any("3x account median" in reason for reason in anomalies[1])
    assert any("domestic-only merchant" in reason for reason in anomalies[1])
