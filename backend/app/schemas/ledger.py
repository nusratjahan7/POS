"""Ledger schemas: a party's statement, entry by entry.

A ledger is **derived**, not stored: every entry maps to a row that already
exists (an opening balance, a credit sale, a purchase receipt, a payment, a
refund reversal), so a statement can never disagree with the balance the rest of
the system maintains.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

LedgerEntryType = Literal["opening", "sale", "purchase", "payment", "refund"]


class LedgerEntry(BaseModel):
    """One movement on an account, already placed in the running balance."""

    occurred_at: datetime
    entry_type: LedgerEntryType
    #: Human identifier — a document number, a payment reference, "Opening balance".
    reference: str
    description: str | None = None
    #: Increases what is owed (a charge, for a receivable; a payment, for a payable).
    debit: Decimal
    #: Decreases what is owed.
    credit: Decimal
    #: The account's balance immediately after this entry.
    balance: Decimal


class LedgerStatement(BaseModel):
    #: The balance carried into the requested window (0 when unbounded).
    opening_balance: Decimal
    entries: list[LedgerEntry]
    #: The balance after the last entry in the window (equals the account
    #: balance when no date range narrows it).
    closing_balance: Decimal
