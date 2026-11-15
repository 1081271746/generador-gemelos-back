"""Fail-closed guard for explicit, unambiguous numeric monetary boundaries.

This is not a general natural-language contract solver. Complex limits require
structured domain rules and human evaluation; prompts alone are not a guarantee.
"""
import re
from decimal import Decimal

from app.core.errors import ExternalServiceError

NUMBER = r"\d+(?:[.,]\d+)?"
BOUND = re.compile(
    rf"(?P<kind>precio m[ií]nimo|salario m[ií]nimo|minimum|"
    rf"no (?:vender|aceptar) por debajo de|no (?:vender|aceptar) por menos de|"
    rf"precio m[aá]ximo|salario m[aá]ximo|maximum|gasto m[aá]ximo|"
    rf"descuento m[aá]ximo)\s*(?:de\s*)?(?P<value>{NUMBER})(?P<percent>\s*%)?", re.I)


def amount(text):
    if re.search(r"[.,]\d{3}$", text):
        # Do not guess whether 9.000 means nine or nine thousand.
        raise ExternalServiceError("Use unambiguous numeric limits without thousands separators")
    return Decimal(text.replace(",", "."))


def numeric_bounds(limits):
    bounds = []
    for match in BOUND.finditer(limits):
        value = amount(match["value"])
        kind = match["kind"].lower()
        lower = "nimo" in kind or kind == "minimum" or "debajo" in kind or "menos" in kind
        bounds.append((lower, value, bool(match["percent"])))
    return bounds


def validate_numeric_limits(content, limits):
    bounds = numeric_bounds(limits)
    if not bounds:
        return
    labels = re.search(r"\b(?:m[ií]nim[oa]|m[aá]xim[oa]|l[ií]mite|presupuesto|minimum|maximum)\b", content, re.I)
    for match in re.finditer(rf"(?<!\w)({NUMBER})(\s*%)?", content):
        value = amount(match[1])
        percent = bool(match[2])
        for lower, boundary, is_percent in bounds:
            if labels and percent == is_percent and value == boundary:
                raise ExternalServiceError("Local AI response may disclose a private numeric boundary")
            if percent == is_percent and (value < boundary if lower else value > boundary):
                # Reject rather than rewriting a model response or fabricating a turn.
                raise ExternalServiceError("Local AI response violates an explicit numeric limit")
