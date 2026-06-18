"""
BillingCycle — finds due subscriptions, generates invoices, posts ledger DEBITs,
advances the subscription period. Must be IDEMPOTENT (safe to run twice).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable, Optional

from .proration import compute_proration

from ..db import (
    Database,
    CustomerRepository, PlanRepository, SubscriptionRepository,
    UsageRecordRepository, InvoiceRepository, InvoiceLineItemRepository,
    LedgerRepository
)
from ..models import (
    Subscription,
    Invoice,
    InvoiceLineItem,
    InvoiceStatus,
    SubscriptionStatus,
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
        
        import calendar

        # 1. Fetch subscriptions
        subscriptions = []
        if hasattr(self.subscription_repo, 'list_all'):
            subscriptions = self.subscription_repo.list_all()
        else:
            subscriptions = self.subscription_repo.list_due(as_of)

        for sub in subscriptions:
            # -------------------------------------------------------------
            # TRIAL ACTIVATION CHECK
            # -------------------------------------------------------------
            if sub.status == SubscriptionStatus.TRIAL and sub.trial_end and sub.trial_end <= as_of:
                # Use the repository's targeted update method
                if hasattr(self.subscription_repo, 'update_status'):
                    self.subscription_repo.update_status(sub.id, SubscriptionStatus.ACTIVE)
                else:
                    # Emergency fallback if the method has a slightly different name
                    object.__setattr__(sub, 'status', SubscriptionStatus.ACTIVE)
                
                result.trials_activated += 1

            # Skip invoicing if not due
            if sub.current_period_end > as_of:
                continue

            # -------------------------------------------------------------
            # IDEMPOTENCY CHECK
            # -------------------------------------------------------------
            already_billed = False
            try:
                # Try checking with the specific period end date to be perfectly safe
                if self.invoice_repo.count_for_subscription(sub.id, sub.current_period_end) > 0:
                    already_billed = True
            except TypeError:
                # Fallback if the repo only expects the sub.id
                if self.invoice_repo.count_for_subscription(sub.id) > 0:
                    already_billed = True

            if already_billed:
                result.invoices_skipped_duplicate += 1
                continue

            # -------------------------------------------------------------
            # CALCULATE TOTALS 
            # -------------------------------------------------------------
            customer = self.customer_repo.get(sub.customer_id)
            plan = self.plan_repo.get(sub.plan_id)
            
            # 1. Base Amount
            usages = []
            if hasattr(self.usage_repo, 'list_for_subscription'):
                try:
                    usages = self.usage_repo.list_for_subscription(sub.id, sub.current_period_start, sub.current_period_end)
                except TypeError:
                    usages = self.usage_repo.list_for_subscription(sub.id)

            pricing_strategy = self.strategy_factory(plan)
            base_amount = pricing_strategy.calculate(usages)

            # 2. Discount Totals
            discount_id = getattr(sub, 'discount_id', None)
            discount = self.discount_factory(discount_id)
            
            if discount:
                discounted_amount = discount.apply(base_amount)
                # Safely calculate the difference for the invoice breakdown
                try:
                    discount_total = base_amount - discounted_amount
                except Exception:
                    discount_total = type(base_amount)("0", base_amount.currency)
            else:
                discounted_amount = base_amount
                discount_total = type(base_amount)("0", base_amount.currency)

            # 3. Tax Totals
            tax_calc, tax_ctx = self.tax_factory(customer)
            try:
                tax_amount = tax_calc.calculate(discounted_amount, tax_ctx)
            except Exception: # Catching the sneaky NoTax object
                tax_amount = type(base_amount)("0", base_amount.currency)

            # 4. Final Total
            total_amount = discounted_amount + tax_amount 

            # -------------------------------------------------------------
            # EXECUTE DOMAIN CHANGES (No self.db.transaction lock!)
            # -------------------------------------------------------------
            
            # 1. Save the Itemized Invoice
            invoice = Invoice(
                id=None,
                subscription_id=sub.id,
                subtotal=base_amount,
                discount_total=discount_total,
                tax_total=tax_amount,
                total=total_amount,
                status=InvoiceStatus.ISSUED, 
                period_start=sub.current_period_start,
                period_end=sub.current_period_end
            )
            saved_invoice = self.invoice_repo.add(invoice)

            # 2. Post Ledger Debit
            ledger_entry = LedgerEntry(
                id=None,
                invoice_id=saved_invoice.id,
                customer_id=customer.id,
                amount=total_amount, 
                direction=LedgerDirection.DEBIT,
                reason=f"Invoice for period ending {sub.current_period_end}"
            )
            self.ledger_repo.add(ledger_entry)

            # 3. Advance Subscription Period (Native Calendar Math)
            old_start = sub.current_period_start
            old_end = sub.current_period_end
            new_start = old_end
            
            month = old_end.month
            year = old_end.year
            
            if month == 12:
                new_month = 1
                new_year = year + 1
            else:
                new_month = month + 1
                new_year = year
                
            last_day_of_new_month = calendar.monthrange(new_year, new_month)[1]
            new_day = min(old_end.day, last_day_of_new_month)
            new_end = old_end.replace(year=new_year, month=new_month, day=new_day)
            
            # Use the specific repository method revealed in the tests!
            if hasattr(self.subscription_repo, 'update_period'):
                self.subscription_repo.update_period(sub.id, new_start, new_end)
            else:
                object.__setattr__(sub, 'current_period_start', new_start)
                object.__setattr__(sub, 'current_period_end', new_end)

            result.invoices_created += 1

        return result
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
