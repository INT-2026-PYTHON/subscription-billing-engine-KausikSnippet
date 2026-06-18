"""
BillingCycle — finds due subscriptions, generates invoices, posts ledger DEBITs,
advances the subscription period. Must be IDEMPOTENT (safe to run twice).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable, Optional

from billing_engine.billing.proration import compute_proration

from billing_engine.db import (
    Database,
    CustomerRepository, PlanRepository, SubscriptionRepository,
    UsageRecordRepository, InvoiceRepository, InvoiceLineItemRepository,
    LedgerRepository
)
from billing_engine.models import (
    Subscription,
    Invoice,
    InvoiceLineItem,
    InvoiceStatus,
    LedgerEntry,
    LedgerDirection,
    LineItemKind,
)


@dataclass
class BillingResult:
    invoices_created: int
    invoices_skipped_duplicate: int
    trials_activated: int


class BillingCycle:
    """Day-3 deliverable. Day-4 stretch: add `upgrade_subscription(...)`."""

    def __init__(
        self,
        db: Database,
        customer_repo: CustomerRepository,
        plan_repo: PlanRepository,
        subscription_repo: SubscriptionRepository,
        usage_repo: UsageRecordRepository,
        invoice_repo: InvoiceRepository,
        line_item_repo: InvoiceLineItemRepository,
        ledger_repo: LedgerRepository,
        strategy_factory: Callable,    # given a Plan, returns a PricingStrategy
        discount_factory: Callable,    # given a discount_id or None, returns a Discount or None
        tax_factory: Callable,         # given a Customer, returns (TaxCalculator, TaxContext)
    ) -> None:
        self.db = db
        self.customer_repo = customer_repo
        self.plan_repo = plan_repo
        self.subscription_repo = subscription_repo
        self.usage_repo = usage_repo
        self.invoice_repo = invoice_repo
        self.line_item_repo = line_item_repo
        self.ledger_repo = ledger_repo
        self.strategy_factory = strategy_factory
        self.discount_factory = discount_factory
        self.tax_factory = tax_factory

    # --------------------------------------------------------
    def run(self, as_of: date) -> BillingResult:
        """Bill all subscriptions whose current period ends on or before `as_of`."""
        result = BillingResult(0, 0, 0)
        
        # Safe imports based on the test file we now see!
        import calendar
        from billing_engine.models import (
            Invoice, LedgerEntry, 
            InvoiceStatus, SubscriptionStatus, LedgerDirection, InvoiceLineItem, invoice, LedgerEntry, LineItemKind
        )

    # --------------------------------------------------------
    def upgrade_subscription(self, subscription_id: int, new_plan_id: int, switch_date: date) -> None:
        """Mid-cycle upgrade — Day 4 stretch."""
        sub = self.subscription_repo.get(subscription_id)
        old_plan = self.plan_repo.get(sub.plan_id)
        new_plan = self.plan_repo.get(new_plan_id)
        customer = self.customer_repo.get(sub.customer_id)

        old_price = self.strategy_factory(old_plan).calculate(0)
        new_price = self.strategy_factory(new_plan).calculate(0)
        tax_calc, tax_context = self.tax_factory(customer)
    
        pr = compute_proration(
             old_plan_price=old_price,
             new_plan_price=new_price,
             period_start=sub.current_period_start,
             period_end=sub.current_period_end,
             switch_date=switch_date,
             tax_calc=tax_calc,
             tax_context=tax_context,
        )

        subtotal = pr.charge_amount - pr.credit_amount
        tax_total = pr.charge_tax - pr.credit_tax
        total = subtotal + tax_total
        discount_total = old_price - old_price

        invoice = self.invoice_repo.add(Invoice(
            id=None,
            subscription_id=sub.id,
            period_start=sub.current_period_start,
            period_end=sub.current_period_end,
            currency=old_price.currency,
            subtotal=subtotal,
            discount_total=discount_total,
            tax_total=tax_total,
            total=total,
            status=InvoiceStatus.ISSUED,
            issued_at=switch_date,
        ))

        self.line_item_repo.add(InvoiceLineItem(
             id=None, invoice_id=invoice.id,
             description=f"Credit for unused time on {old_plan.name}",
             amount=-pr.credit_amount,
             kind=LineItemKind.PRORATION_CREDIT,
        )) 

        self.line_item_repo.add(InvoiceLineItem(
             id=None, invoice_id=invoice.id,
             description=f"Charge for remaining time on {new_plan.name}",
             amount=pr.charge_amount,
             kind=LineItemKind.PRORATION_CHARGE,
        ))
 
        self.ledger_repo.add(LedgerEntry( 
             id=None, invoice_id=invoice.id, customer_id=customer.id, 
             amount=total, direction=LedgerDirection.DEBIT,
             reason=f"Proration for upgrade to {new_plan.name} (invoice #{invoice.id})",
        ))
        self.subscription_repo.update_plan(subscription_id, new_plan_id)  

        return invoice 
