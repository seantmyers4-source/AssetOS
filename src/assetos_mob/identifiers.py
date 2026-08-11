"""Permanent Asset-ID candidate generation and validation.

Implements the approved Identification & Labeling v0.1 controlled revision:

    AOS-<16 Crockford Base32 body characters>-<mod-37 check symbol>
"""

from __future__ import annotations

from dataclasses import dataclass
import secrets
import re

from .errors import ValidationError

BODY_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
CHECK_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ*~$=U"
CANONICAL_RE = re.compile(
    r"^AOS-([0-9ABCDEFGHJKMNPQRSTVWXYZ]{4})-"
    r"([0-9ABCDEFGHJKMNPQRSTVWXYZ]{4})-"
    r"([0-9ABCDEFGHJKMNPQRSTVWXYZ]{4})-"
    r"([0-9ABCDEFGHJKMNPQRSTVWXYZ]{4})-"
    r"([0-9ABCDEFGHJKMNPQRSTVWXYZ*~$=U])$"
)


@dataclass(frozen=True)
class AssetIdParts:
    canonical: str
    body: str
    check_symbol: str
    check_value: int


def calculate_check_value(body: str) -> int:
    """Calculate left-to-right mod-37 remainder over a normalized 16-char body."""
    if len(body) != 16:
        raise ValidationError("asset_id body must contain exactly 16 symbols")
    r = 0
    for symbol in body:
        try:
            value = BODY_ALPHABET.index(symbol)
        except ValueError as exc:
            raise ValidationError(f"invalid body symbol: {symbol!r}") from exc
        r = (r * 32 + value) % 37
    return r


def calculate_check_symbol(body: str) -> str:
    return CHECK_ALPHABET[calculate_check_value(body)]


def format_asset_id(body: str) -> str:
    check_symbol = calculate_check_symbol(body)
    return f"AOS-{body[0:4]}-{body[4:8]}-{body[8:12]}-{body[12:16]}-{check_symbol}"


def normalize_asset_id(value: str) -> AssetIdParts:
    """Normalize and validate a canonical Asset ID.

    The specification allows lowercase ASCII normalization, but does not allow
    guessing, substitution, or repairing misplaced canonical grouping.
    """
    candidate = value.strip().upper()
    match = CANONICAL_RE.fullmatch(candidate)
    if not match:
        raise ValidationError("asset_id must match canonical AOS-####-####-####-####-# form")
    body = "".join(match.group(i) for i in range(1, 5))
    supplied_check = match.group(5)
    check_value = calculate_check_value(body)
    expected_check = CHECK_ALPHABET[check_value]
    if supplied_check != expected_check:
        raise ValidationError("asset_id check symbol mismatch")
    return AssetIdParts(candidate, body, supplied_check, check_value)


def validate_asset_id(value: str) -> bool:
    normalize_asset_id(value)
    return True


def generate_candidate_asset_id() -> AssetIdParts:
    """Generate an unissued candidate ID using 80 random bits of body entropy."""
    body = "".join(secrets.choice(BODY_ALPHABET) for _ in range(16))
    return normalize_asset_id(format_asset_id(body))
