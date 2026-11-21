"""Deterministic tools: catalogue lookup, quotation math, and business policy."""

import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

CATALOG_PATH = Path(__file__).resolve().parent / "services.json"


def load_catalog() -> dict:
    """Load and validate the service catalogue."""
    if not CATALOG_PATH.exists():
        raise FileNotFoundError("services.json was not found.")

    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    required_fields = {"currency", "services", "maximum_discount_pct"}
    if not required_fields.issubset(data):
        raise ValueError("Service catalogue is missing required fields.")

    if not isinstance(data["services"], list):
        raise ValueError("Services must be provided as a list.")

    return data


def get_service_catalog(category: str = "all") -> dict:
    """Return available services, optionally filtered by category."""
    data = load_catalog()

    if not isinstance(category, str) or not category.strip():
        return {"error": "Please provide a valid service category."}

    services = data["services"]
    selected_category = category.strip().lower()

    if selected_category != "all":
        services = [
            service for service in services
            if service.get("category", "").lower() == selected_category
        ]

    return {
        "currency": data["currency"],
        "services": services,
        "disclaimer": data.get("disclaimer", "Prices are subject to change.")
    }


def get_business_policy() -> dict:
    """Return quotation, discount and approval policies."""
    data = load_catalog()

    return {
        "maximum_discount_pct": data["maximum_discount_pct"],
        "tax_included": False,
        "price_policy": "Prices are fictional educational examples only.",
        "discount_policy": "Discounts cannot exceed the configured maximum.",
        "approval_policy": (
            "A human must click Save Approved Quote "
            "before anything is written to disk."
        )
    }


def _money(value: Decimal) -> str:
    """Format monetary values to two decimal places."""
    return str(
        value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )


def calculate_quote(items: list[dict], discount_pct: float = 0) -> dict:
    """Calculate a verified quotation using Decimal arithmetic."""
    data = load_catalog()

    index = {
        service["code"]: service
        for service in data["services"]
    }

    if not isinstance(items, list) or not (1 <= len(items) <= 15):
        return {"error": "Provide between 1 and 15 quote line items."}

    try:
        discount = Decimal(str(discount_pct))
    except (InvalidOperation, ValueError, TypeError):
        return {"error": "Discount must be numeric."}

    maximum_discount = Decimal(str(data["maximum_discount_pct"]))

    if (
        not discount.is_finite()
        or discount < 0
        or discount > maximum_discount
    ):
        return {
            "error": (
                f"Discount must be between 0 and "
                f"{maximum_discount}%."
            )
        }

    quote_lines = []
    subtotal = Decimal("0.00")

    for item in items:
        if not isinstance(item, dict):
            return {"error": "Every line item must be an object."}

        code = item.get("service_code")
        quantity = item.get("quantity")

        if not isinstance(code, str) or code not in index:
            return {
                "error": (
                    f"Unknown service code: {code}. "
                    "First call get_service_catalog."
                )
            }

        if type(quantity) is not int or not (1 <= quantity <= 100):
            return {
                "error": "Quantities must be whole numbers from 1 to 100."
            }

        service = index[code]

        try:
            unit_price = Decimal(str(service["unit_price"]))
        except (InvalidOperation, ValueError, KeyError):
            return {"error": f"Invalid price configuration for {code}."}

        if not unit_price.is_finite() or unit_price < 0:
            return {"error": f"Invalid unit price for {code}."}

        line_total = unit_price * quantity
        subtotal += line_total

        quote_lines.append({
            "service_code": code,
            "service": service["name"],
            "quantity": quantity,
            "unit": service.get("unit", "unit"),
            "unit_price": _money(unit_price),
            "line_total": _money(line_total)
        })

    discount_amount = (
        subtotal * discount / Decimal("100")
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    total = subtotal - discount_amount

    return {
        "status": "DRAFT_AWAITING_HUMAN_APPROVAL",
        "currency": data["currency"],
        "items": quote_lines,
        "subtotal": _money(subtotal),
        "discount_pct": _money(discount),
        "discount_amount": _money(discount_amount),
        "total": _money(total),
        "tax_note": (
            "Tax excluded; this is a classroom demo quotation, "
            "not an invoice."
        )
    }


# Names and descriptions provided to the model.
# Actual tool execution happens in Python.

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_service_catalog",
            "description": (
                "Get available service names, codes and prices. "
                "Always check the catalogue before preparing quotations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": (
                            "Category: all, Marketing, Web or Branding."
                        )
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_business_policy",
            "description": (
                "Retrieve discount, tax and quotation approval policies."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_quote",
            "description": (
                "Calculate a quotation using verified service codes. "
                "Never calculate totals yourself."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 15,
                        "items": {
                            "type": "object",
                            "properties": {
                                "service_code": {
                                    "type": "string"
                                },
                                "quantity": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 100
                                }
                            },
                            "required": [
                                "service_code",
                                "quantity"
                            ]
                        }
                    },
                    "discount_pct": {
                        "type": "number",
                        "description": (
                            "Optional discount percentage. "
                            "Maximum is determined by business policy."
                        )
                    }
                },
                "required": ["items"]
            }
        }
    }
]


TOOL_FUNCTIONS = {
    "get_service_catalog": get_service_catalog,
    "get_business_policy": get_business_policy,
    "calculate_quote": calculate_quote
}