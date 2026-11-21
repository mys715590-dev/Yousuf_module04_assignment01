"""Human-approved local CSV quote storage. No automatic saving by the model."""

import csv
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import uuid4

SAVED_QUOTES = (
    Path(__file__).resolve().parent
    / "data"
    / "approved_quotes.csv"
)

FIELDS = [
    "quote_id",
    "saved_at_utc",
    "client_name",
    "currency",
    "total",
    "details_json"
]


def save_approved_quote(quote: dict, client_name: str) -> dict:
    """Save a valid quotation only after explicit human approval."""

    if not isinstance(quote, dict):
        raise ValueError("Invalid quotation data.")

    if quote.get("status") != "DRAFT_AWAITING_HUMAN_APPROVAL":
        raise ValueError("Only a valid draft can be approved.")

    if not isinstance(client_name, str) or not client_name.strip():
        raise ValueError("Enter a client name before approving.")

    client_name = client_name.strip()

    if len(client_name) > 100:
        raise ValueError("Client name cannot exceed 100 characters.")

    currency = quote.get("currency")
    total = quote.get("total")

    if not isinstance(currency, str) or not currency.strip():
        raise ValueError("Quotation currency is missing.")

    try:
        numeric_total = Decimal(str(total))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Quotation total is invalid.")

    if not numeric_total.is_finite() or numeric_total < 0:
        raise ValueError("Quotation total must be a valid non-negative amount.")

    items = quote.get("items")

    if not isinstance(items, list) or not items:
        raise ValueError("Quotation must contain at least one service.")

    # Prepare the storage directory.
    SAVED_QUOTES.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # Create a unique quotation ID.
    quote_id = f"SQ-{uuid4().hex[:8].upper()}"

    row = {
        "quote_id": quote_id,
        "saved_at_utc": datetime.now(
            timezone.utc
        ).isoformat(timespec="seconds"),
        "client_name": client_name,
        "currency": currency.strip(),
        "total": str(numeric_total),
        "details_json": json.dumps(
            quote,
            ensure_ascii=False
        )
    }

    is_new = (
        not SAVED_QUOTES.exists()
        or SAVED_QUOTES.stat().st_size == 0
    )

    try:
        with SAVED_QUOTES.open(
            "a",
            encoding="utf-8",
            newline=""
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=FIELDS
            )

            if is_new:
                writer.writeheader()

            writer.writerow(row)

    except OSError as exc:
        raise ValueError(
            "Could not save quotation. Check folder permissions."
        ) from exc

    return {
        "quote_id": quote_id,
        "path": str(SAVED_QUOTES),
        "status": "APPROVED_AND_SAVED"
    }