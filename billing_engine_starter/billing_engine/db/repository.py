"""
Repositories — the ONLY place SQL lives.

Each repository wraps the Database connection and exposes methods that
take/return domain dataclasses (defined in billing_engine/models/).

⚠️ YOU IMPLEMENT every method body marked TODO.
   The signatures, docstrings, and the LedgerRepository's append-only
   guarantee are already in place — do not change them.

Beginner map (Day 2):
  1) CustomerRepository: add, get, find_by_email, list_all
  2) PlanRepository: add, get, list_all
  3) PlanTierRepository: add, list_for_plan
  4) DiscountRepository: add, get_by_code
  5) SubscriptionRepository: add, get, list_all, get_due_for_billing
  6) UsageRecordRepository: add, sum_for_period
  7) InvoiceRepository: add, get
  8) InvoiceLineItemRepository: add, list_for_invoice

Skip on Day 2 (read-only for now):
  - SubscriptionRepository.update_period / update_status / update_plan
  - InvoiceRepository.count_for_subscription / mark_paid / mark_failed / set_pdf_path
  - LedgerRepository and PaymentAttemptRepository

Conventions:
  - Always use parameterized queries (`?` placeholders) — NEVER f-string SQL.
  - Money values are persisted as TEXT using `money.to_storage()`.
  - Dates are persisted as ISO strings (`date.isoformat()`).

New layering (beginner-friendly):
  - Raw SQL lives in `billing_engine/db/queries.py`.
  - Repository methods call those query helpers.
  - Your Day 2 focus is:
      1) Convert domain -> storage values before helper call
      2) Convert rows -> domain dataclasses after helper call
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from billing_engine.db.database import Database
from billing_engine.db import queries as q
from billing_engine.money import Money
from billing_engine.models import (
    Customer,
    Plan, PricingType, BillingPeriod,
    Subscription, SubscriptionStatus,
    Invoice, InvoiceStatus, InvoiceLineItem, LineItemKind,
    LedgerEntry, LedgerDirection,
)


# ============================================================
# CUSTOMERS
# ============================================================
# Day 2: start here.
class CustomerRepository:
    """Persistence boundary for customers.

    A Customer is the billing account owner: invoices, subscriptions, and
    ledger entries ultimately belong to a customer. This repository hides the
    `customers` table and returns Customer dataclasses so the rest of the app
    does not need to know SQL column names.
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, customer: Customer) -> Customer:
        # TODO Day 2
        # Hint: q.insert_customer(...)
        raise NotImplementedError("Day 2: implement CustomerRepository.add")

    def get(self, customer_id: int) -> Optional[Customer]:
        # TODO Day 2
        # Hint: q.select_customer_by_id(...)
        raise NotImplementedError("Day 2: implement CustomerRepository.get")

    def find_by_email(self, email: str) -> Optional[Customer]:
        # TODO Day 2
        # Hint: q.select_customer_by_email(...)
        raise NotImplementedError("Day 2: implement CustomerRepository.find_by_email")

    def list_all(self) -> list[Customer]:
        # TODO Day 2
        # Hint: q.select_all_customers(...)
        raise NotImplementedError("Day 2: implement CustomerRepository.list_all")


# ============================================================
# PLANS  +  PLAN TIERS
# ============================================================
# Day 2
class PlanRepository:
    """Persistence boundary for subscription plans.

    A Plan describes what the customer bought: pricing type, billing period,
    currency, and strategy configuration. Pricing code consumes Plan objects,
    while this repository handles the `plans` table representation.
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, plan: Plan) -> Plan:
        # TODO Day 2.
        # Hint: q.insert_plan(...)
        raise NotImplementedError("Day 2: implement PlanRepository.add")

    def get(self, plan_id: int) -> Optional[Plan]:
        # TODO Day 2.
        # Hint: q.select_plan_by_id(...)
        raise NotImplementedError("Day 2: implement PlanRepository.get")

    def list_all(self) -> list[Plan]:
        # TODO Day 2.
        # Hint: q.select_all_plans(...)
        raise NotImplementedError("Day 2: implement PlanRepository.list_all")


class PlanTierRepository:
    """Persistence boundary for pricing tiers attached to a plan.

    Tiered and usage-based plans need rows such as "0-100 units at 1.00" and
    "101+ units at 0.75". These rows live separately from plans because one
    plan can have many tiers.
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, plan_id: int, from_units: int, to_units: Optional[int], unit_price: Money) -> int:
        # TODO Day 2.
        # Hint: q.insert_plan_tier(...)
        raise NotImplementedError("Day 2: implement PlanTierRepository.add")

    def list_for_plan(self, plan_id: int, currency: str) -> list[tuple[int, Optional[int], Money]]:
        # TODO Day 2.
        # Hint: q.select_plan_tiers(...)
        raise NotImplementedError("Day 2: implement PlanTierRepository.list_for_plan")


# ============================================================
# DISCOUNTS
# ============================================================
# Day 2
class DiscountRepository:
    """Persistence boundary for discount definitions.

    Discounts are stored as flexible rows because different discount types need
    different interpretation: percentage, fixed amount, or first-month-free.
    This repository intentionally returns dictionaries instead of a dataclass.
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, code: str, discount_type: str, value: str, currency: Optional[str] = None) -> int:
        # TODO Day 2.
        # Hint: q.insert_discount(...)
        raise NotImplementedError("Day 2: implement DiscountRepository.add")

    def get_by_code(self, code: str) -> Optional[dict]:
        # TODO Day 2.
        # Hint: q.select_discount_by_code(...)
        raise NotImplementedError("Day 2: implement DiscountRepository.get_by_code")


# ============================================================
# SUBSCRIPTIONS
# ============================================================
# Day 2 (only add/get/list_all/get_due_for_billing)
class SubscriptionRepository:
    """Persistence boundary for customer subscriptions.

    A Subscription connects a customer to a plan and tracks lifecycle state:
    TRIAL, ACTIVE, PAST_DUE, or CANCELLED. It also stores the current billing
    period, trial end date, optional discount, and dunning state.
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, subscription: Subscription) -> Subscription:
        # TODO Day 2.
        # Hint: q.insert_subscription(...)
        raise NotImplementedError("Day 2: implement SubscriptionRepository.add")

    def get(self, subscription_id: int) -> Optional[Subscription]:
        # TODO Day 2.
        # Hint: q.select_subscription_by_id(...)
        raise NotImplementedError("Day 2: implement SubscriptionRepository.get")

    def list_all(self) -> list[Subscription]:
        # TODO Day 2.
        # Hint: q.select_all_subscriptions(...)
        raise NotImplementedError("Day 2: implement SubscriptionRepository.list_all")

    def get_due_for_billing(self, as_of: date) -> list[Subscription]:
        # TODO Day 2.
        # Hint: q.select_due_subscriptions(...)
        raise NotImplementedError("Day 2: implement SubscriptionRepository.get_due_for_billing")

    # ------------------------------------------------------------------
    # Day 2 boundary:
    # Everything below this line in this class is intentionally deferred.
    # Keep the method stubs so Day 3/4 can build on the same API surface.
    # ------------------------------------------------------------------
    def update_period(self, subscription_id: int, new_start: date, new_end: date) -> None:
        with self.db.transaction() as conn:
           conn.execute(
            """
            UPDATE subscriptions
            SET current_period_start = ?, current_period_end = ?
            WHERE id = ?
            """,
            (new_start.isoformat(), new_end.isoformat(), subscription_id),
        )

    def update_status(
        self,
        subscription_id: int,
        new_status: SubscriptionStatus,
        past_due_since: Optional[date] = None,
    ) -> None:
        with self.db.transaction() as conn:
          conn.execute(
            """
            UPDATE subscriptions
            SET status = ?, past_due_since = ?
            WHERE id = ?
            """,
            (
                new_status.value,  # store enum as string
                past_due_since.isoformat() if past_due_since else None,
                subscription_id,
            ),
        )

    def update_plan(self, subscription_id: int, new_plan_id: int) -> None:
        # TODO Day 4.
        # Hint: q.update_subscription_plan(...)
        raise NotImplementedError("Day 4: implement SubscriptionRepository.update_plan")


# ============================================================
# USAGE
# ============================================================
# Day 2
class UsageRecordRepository:
    """Persistence boundary for metered usage.

    Usage records store quantities such as API calls, seats, messages, or GBs.
    Usage-based pricing strategies ask this repository for the total quantity
    they should charge for a subscription.
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, subscription_id: int, metric: str, quantity: int) -> int:
        # TODO Day 2.
        # Hint: q.insert_usage_record(...)
        raise NotImplementedError("Day 2: implement UsageRecordRepository.add")

    def sum_for_period(
        self, subscription_id: int, metric: str, period_start: date, period_end: date
    ) -> int:
        # TODO Day 2: SELECT COALESCE(SUM(quantity), 0) ...
        # Hint: q.sum_usage_for_subscription_metric(...)
        raise NotImplementedError("Day 2: implement UsageRecordRepository.sum_for_period")


# ============================================================
# INVOICES + LINE ITEMS
# ============================================================
# Day 2 (InvoiceRepository only add/get)
class InvoiceRepository:
    """Persistence boundary for invoice headers.

    An Invoice stores the totals for one subscription period: subtotal,
    discounts, tax, final total, status, issue time, and optional PDF path.
    Line items are stored separately by InvoiceLineItemRepository.
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, invoice: Invoice) -> Invoice:
        # TODO Day 2.
        # Hint: q.insert_invoice(...)
        raise NotImplementedError("Day 2: implement InvoiceRepository.add")

    def get(self, invoice_id: int) -> Optional[Invoice]:
        # TODO Day 2.
        # Hint: q.select_invoice_by_id(...)
        raise NotImplementedError("Day 2: implement InvoiceRepository.get")

    def count_for_subscription(self, subscription_id: int) -> int:
        with self.db.connect() as conn:
         cur = conn.execute(
            """
            SELECT COUNT(*) 
            FROM invoices 
            WHERE subscription_id = ?
            """,
            (subscription_id,),
        )
        return cur.fetchone()[0]

    def mark_paid(self, invoice_id: int) -> None:
        # TODO Day 4.
        # Hint: q.update_invoice_status(..., "PAID")
        raise NotImplementedError("Day 4: implement InvoiceRepository.mark_paid")

    def mark_failed(self, invoice_id: int) -> None:
        # TODO Day 4.
        # Hint: q.update_invoice_status(..., "FAILED")
        raise NotImplementedError("Day 4: implement InvoiceRepository.mark_failed")

    def set_pdf_path(self, invoice_id: int, path: str) -> None:
        # TODO Day 4.
        # Hint: q.update_invoice_pdf_path(...)
        raise NotImplementedError("Day 4: implement InvoiceRepository.set_pdf_path")


class InvoiceLineItemRepository:
    """Persistence boundary for invoice detail rows.

    Line items explain how the invoice total was built: base charge, usage,
    discount, tax, or proration. They are separate from the invoice header so
    one invoice can contain multiple visible charges and credits.
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, line_item: InvoiceLineItem) -> InvoiceLineItem:
        # TODO Day 2.
        # Hint: q.insert_invoice_line_item(...)
        raise NotImplementedError("Day 2: implement InvoiceLineItemRepository.add")

    def list_for_invoice(self, invoice_id: int) -> list[InvoiceLineItem]:
        # TODO Day 2.
        # Hint: q.select_line_items_for_invoice(...)
        raise NotImplementedError("Day 2: implement InvoiceLineItemRepository.list_for_invoice")


# ============================================================
# DAY 3/4 ONLY — keep stubs for later
# ============================================================

# ============================================================
# LEDGER — APPEND-ONLY (do not implement update/delete)
# ============================================================
class LedgerRepository:
    """Persistence boundary for the append-only accounting ledger.

    The ledger records financial movements: DEBIT when the customer owes money,
    CREDIT when money is received or reversed. It is append-only so history is
    auditable; mistakes should be corrected with reversing entries, not edits.
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, entry: LedgerEntry) -> LedgerEntry:
        with self.db.transaction() as conn:
            entry_id = q.insert_ledger_entry(
                conn,
                entry.invoice_id,
                entry.customer_id,
                str(entry.amount.amount),   # <-- FIX: Convert Decimal to string for SQLite
                str(entry.amount.currency), # <-- FIX: Convert to string just in case
                entry.direction,
                entry.reason,
            )
            
        return LedgerEntry(
            id=entry_id,
            invoice_id=entry.invoice_id,
            customer_id=entry.customer_id,
            amount=entry.amount,            # <-- Pass the original Money object back
            direction=entry.direction,
            reason=entry.reason,
        )

    def list_for_customer(self, customer_id: int) -> list[LedgerEntry]:
        with self.db.connect() as conn:
            rows = q.select_ledger_for_customer(conn, customer_id)
            
        return [
            LedgerEntry(
                id=row["id"],
                invoice_id=row["invoice_id"],
                customer_id=row["customer_id"],
                amount=Money(str(row["amount"]), str(row["currency"])), 
                direction=row["direction"],
                reason=row["reason"],
                # FIX: Slice the string to keep only the 'YYYY-MM-DD' portion
                created_at=date.fromisoformat(str(row["created_at"])[:10]),
            )
            for row in rows
        ]

    # These two methods are intentionally implemented to REJECT — do not override.
    def update(self, *args, **kwargs):
        raise NotImplementedError("Ledger is append-only. Post a reversing entry instead.")

    def delete(self, *args, **kwargs):
        raise NotImplementedError("Ledger is append-only. Post a reversing entry instead.")


# ============================================================
# PAYMENT ATTEMPTS
# ============================================================
class PaymentAttemptRepository:
    """Persistence boundary for payment retry history.

    Each payment attempt records whether charging an invoice succeeded or
    failed, why it failed, and when the next retry should happen. This history
    powers the Day 3/4 dunning flow.
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    def add(
        self,
        invoice_id: int,
        attempt_no: int,
        status: str,
        failure_reason: Optional[str],
        next_retry_at: Optional[datetime],
    ) -> int:
        with self.db.transaction() as conn:
            return q.insert_payment_attempt(
                conn,
                invoice_id,
                attempt_no,
                status,
                failure_reason,
                next_retry_at.isoformat() if next_retry_at else None,
            )

    def list_for_invoice(self, invoice_id: int) -> list[dict]:
        with self.db.connect() as conn:
            rows = q.select_attempts_for_invoice(conn, invoice_id)
        return [
            {
                "id": row["id"],
                "invoice_id": row["invoice_id"],
                "attempt_no": row["attempt_no"],
                "status": row["status"],
                "failure_reason": row["failure_reason"],
                "next_retry_at": row["next_retry_at"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def count_for_invoice(self, invoice_id: int) -> int:
        with self.db.connect() as conn:
            return q.count_attempts_for_invoice(conn, invoice_id)
