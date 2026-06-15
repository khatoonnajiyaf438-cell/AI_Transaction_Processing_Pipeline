import json
import time
from collections import Counter, defaultdict
from decimal import Decimal
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.cleaner import CleanedTransaction

CATEGORIES = [
    "Food",
    "Shopping",
    "Travel",
    "Transport",
    "Utilities",
    "Cash Withdrawal",
    "Entertainment",
    "Other",
]


class LLMClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def classify_missing_categories(self, transactions: list[CleanedTransaction]) -> dict[int, dict[str, Any]]:
        pending = [
            {
                "index": index,
                "merchant": transaction.merchant,
                "amount": str(transaction.amount),
                "currency": transaction.currency,
                "notes": transaction.notes or "",
            }
            for index, transaction in enumerate(transactions)
            if transaction.original_category_missing
        ]
        if not pending:
            return {}

        prompt = (
            "Classify each transaction into exactly one category from "
            f"{', '.join(CATEGORIES)}. Return JSON array with index and category only: "
            f"{json.dumps(pending)}"
        )

        try:
            response = self._call_with_retries(prompt)
            parsed = self._parse_json(response)
            items = parsed if isinstance(parsed, list) else parsed.get("items", [])
            return {
                int(item["index"]): {"category": _normalise_category(item.get("category")), "raw": parsed}
                for item in items
                if "index" in item
            }
        except Exception as exc:
            return {
                item["index"]: {
                    "category": _heuristic_category(item["merchant"], item.get("notes", "")),
                    "raw": {"provider": "heuristic_fallback", "error": str(exc)},
                    "failed": True,
                }
                for item in pending
            }

    def build_summary(
        self,
        transactions: list[dict[str, Any]],
        anomaly_count: int,
        spend_by_category: dict[str, dict[str, str]],
    ) -> dict[str, Any]:
        totals = defaultdict(Decimal)
        merchant_totals = Counter()
        for transaction in transactions:
            amount = Decimal(str(transaction["amount"]))
            totals[transaction["currency"]] += amount
            merchant_totals[transaction["merchant"]] += amount

        top_merchants = [
            {"merchant": merchant, "amount": str(amount)}
            for merchant, amount in merchant_totals.most_common(3)
        ]
        risk_level = "high" if anomaly_count >= 5 else "medium" if anomaly_count >= 2 else "low"

        summary_input = {
            "total_spend_by_currency": {currency: str(amount) for currency, amount in totals.items()},
            "top_merchants": top_merchants,
            "anomaly_count": anomaly_count,
            "spend_by_category": spend_by_category,
            "risk_level": risk_level,
        }
        prompt = (
            "Produce strict JSON with keys total_spend_by_currency, top_merchants, anomaly_count, "
            "narrative, risk_level. Narrative must be 2-3 sentences. Input: "
            f"{json.dumps(summary_input)}"
        )

        try:
            parsed = self._parse_json(self._call_with_retries(prompt))
            narrative = str(parsed.get("narrative", "")).strip()
            if not narrative:
                narrative = _heuristic_narrative(totals, top_merchants, anomaly_count)
            return {
                "total_spend_inr": str(totals.get("INR", Decimal("0.00"))),
                "total_spend_usd": str(totals.get("USD", Decimal("0.00"))),
                "top_merchants": top_merchants,
                "anomaly_count": anomaly_count,
                "narrative": narrative,
                "risk_level": parsed.get("risk_level", risk_level),
                "llm_raw_response": parsed,
            }
        except Exception as exc:
            return {
                "total_spend_inr": str(totals.get("INR", Decimal("0.00"))),
                "total_spend_usd": str(totals.get("USD", Decimal("0.00"))),
                "top_merchants": top_merchants,
                "anomaly_count": anomaly_count,
                "narrative": _heuristic_narrative(totals, top_merchants, anomaly_count),
                "risk_level": risk_level,
                "llm_raw_response": {"provider": "heuristic_fallback", "error": str(exc)},
            }

    def _call_with_retries(self, prompt: str) -> str:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                return self._call_provider(prompt)
            except Exception as exc:
                last_error = exc
                time.sleep(2**attempt)
        raise RuntimeError(f"LLM call failed after retries: {last_error}")

    def _call_provider(self, prompt: str) -> str:
        provider = self.settings.llm_provider
        if provider == "heuristic":
            raise RuntimeError("No external LLM provider configured.")
        if provider == "ollama":
            return self._call_ollama(prompt)
        if provider == "gemini":
            return self._call_gemini(prompt)
        if provider == "openai":
            return self._call_openai(prompt)
        raise RuntimeError(f"Unsupported LLM provider: {provider}")

    def _call_ollama(self, prompt: str) -> str:
        payload = {"model": self.settings.llm_model, "prompt": prompt, "stream": False}
        with httpx.Client(timeout=self.settings.llm_timeout_seconds) as client:
            response = client.post(f"{self.settings.ollama_base_url}/api/generate", json=payload)
            response.raise_for_status()
            return response.json()["response"]

    def _call_gemini(self, prompt: str) -> str:
        if not self.settings.llm_api_key:
            raise RuntimeError("LLM_API_KEY is required for Gemini.")
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.settings.llm_model}:generateContent?key={self.settings.llm_api_key}"
        )
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        with httpx.Client(timeout=self.settings.llm_timeout_seconds) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    def _call_openai(self, prompt: str) -> str:
        if not self.settings.llm_api_key:
            raise RuntimeError("LLM_API_KEY is required for OpenAI.")
        payload = {
            "model": self.settings.llm_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }
        headers = {"Authorization": f"Bearer {self.settings.llm_api_key}"}
        with httpx.Client(timeout=self.settings.llm_timeout_seconds) as client:
            response = client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

    def _parse_json(self, text: str) -> Any:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.removeprefix("json").strip()
        first = min([pos for pos in [cleaned.find("{"), cleaned.find("[")] if pos >= 0], default=0)
        last = max(cleaned.rfind("}"), cleaned.rfind("]"))
        if last >= first:
            cleaned = cleaned[first : last + 1]
        return json.loads(cleaned)


def _normalise_category(value: Any) -> str:
    category = str(value or "Other").strip().title()
    for allowed in CATEGORIES:
        if category.lower() == allowed.lower():
            return allowed
    return "Other"


def _heuristic_category(merchant: str, notes: str = "") -> str:
    text = f"{merchant} {notes}".upper()
    rules = [
        ("Food", ["SWIGGY", "ZOMATO", "CAFE", "RESTAURANT", "FOOD"]),
        ("Travel", ["IRCTC", "HOTEL", "AIR", "FLIGHT", "RAIL"]),
        ("Transport", ["OLA", "UBER", "METRO", "FUEL", "CAB"]),
        ("Utilities", ["BILL", "ELECTRIC", "WATER", "MOBILE", "RECHARGE"]),
        ("Cash Withdrawal", ["ATM", "CASH"]),
        ("Entertainment", ["NETFLIX", "PVR", "SPOTIFY", "MOVIE"]),
        ("Shopping", ["AMAZON", "FLIPKART", "MALL", "STORE"]),
    ]
    for category, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return category
    return "Other"


def _heuristic_narrative(totals: dict[str, Decimal], top_merchants: list[dict], anomaly_count: int) -> str:
    currency_bits = ", ".join(f"{currency} {amount:.2f}" for currency, amount in sorted(totals.items()))
    leader = top_merchants[0]["merchant"] if top_merchants else "no single merchant"
    risk = "requires review" if anomaly_count else "looks stable"
    return (
        f"Total spend across the uploaded file is {currency_bits or '0.00'}, with {leader} leading merchant spend. "
        f"The pipeline flagged {anomaly_count} anomalous transaction(s), so the batch {risk} before reconciliation."
    )
