"""
expenses.py
Core data layer for the Personal Finance Tracker.

Defines:
    - Expense:        a single validated expense record
    - ExpenseManager:  an in-memory collection of expenses + budgets,
                        with search/filter, budget tracking, recurring
                        expense generation, and simple prediction.
"""

import itertools
from datetime import datetime, date
from collections import defaultdict
from typing import List, Dict, Optional

DEFAULT_CATEGORIES = [
    "Food", "Transportation", "Housing", "Utilities", "Entertainment",
    "Healthcare", "Shopping", "Education", "Savings", "Other",
]


class ValidationError(Exception):
    """Raised when expense or budget data fails validation."""
    pass


class Expense:
    """A single expense record with built-in validation."""

    _id_counter = itertools.count(1)

    def __init__(self, date_str, amount, category, description="", recurring=False, expense_id=None):
        self.id = expense_id if expense_id is not None else next(Expense._id_counter)
        self.date = self._validate_date(date_str)
        self.amount = self._validate_amount(amount)
        self.category = self._validate_category(category)
        self.description = str(description).strip()
        self.recurring = bool(recurring)

    # ---------- validation ----------
    @staticmethod
    def _validate_date(date_str):
        if isinstance(date_str, date):
            return date_str.strftime("%Y-%m-%d")
        date_str = str(date_str).strip()
        try:
            parsed = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise ValidationError(f"Invalid date '{date_str}'. Use YYYY-MM-DD format.")
        if parsed.date() > datetime.now().date():
            raise ValidationError("Expense date cannot be in the future.")
        return parsed.strftime("%Y-%m-%d")

    @staticmethod
    def _validate_amount(amount):
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            raise ValidationError(f"Amount '{amount}' is not a valid number.")
        if amount <= 0:
            raise ValidationError("Amount must be greater than zero.")
        if amount > 10_000_000:
            raise ValidationError("Amount is unrealistically large.")
        return round(amount, 2)

    @staticmethod
    def _validate_category(category):
        category = str(category).strip().title()
        if not category:
            raise ValidationError("Category cannot be empty.")
        if len(category) > 40:
            raise ValidationError("Category name is too long.")
        return category

    # ---------- serialization ----------
    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date,
            "amount": self.amount,
            "category": self.category,
            "description": self.description,
            "recurring": self.recurring,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            d["date"], d["amount"], d["category"],
            d.get("description", ""), d.get("recurring", False),
            expense_id=d.get("id"),
        )

    def month_key(self):
        """Return 'YYYY-MM' for grouping by month."""
        return self.date[:7]

    def __repr__(self):
        return f"<Expense #{self.id} {self.date} {self.category} ${self.amount:.2f}>"

    def __str__(self):
        desc = f" - {self.description}" if self.description else ""
        flag = "  [recurring]" if self.recurring else ""
        return f"#{self.id:<4} {self.date}  {self.category:<14} ${self.amount:>10.2f}{desc}{flag}"


class ExpenseManager:
    """Manages a collection of expenses plus category budgets."""

    def __init__(self):
        self.expenses: List[Expense] = []
        self.budgets: Dict[str, float] = {}

    # ---------- CRUD ----------
    def add_expense(self, date_str, amount, category, description="", recurring=False):
        expense = Expense(date_str, amount, category, description, recurring)
        self.expenses.append(expense)
        return expense

    def remove_expense(self, expense_id):
        before = len(self.expenses)
        self.expenses = [e for e in self.expenses if e.id != expense_id]
        return len(self.expenses) < before

    def get_expense(self, expense_id) -> Optional[Expense]:
        for e in self.expenses:
            if e.id == expense_id:
                return e
        return None

    def update_expense(self, expense_id, **kwargs):
        expense = self.get_expense(expense_id)
        if not expense:
            return False
        data = expense.to_dict()
        data.update(kwargs)
        new_expense = Expense.from_dict(data)
        new_expense.id = expense_id
        idx = self.expenses.index(expense)
        self.expenses[idx] = new_expense
        return True

    # ---------- search / filter ----------
    def search(self, keyword=None, category=None, start_date=None, end_date=None,
               min_amount=None, max_amount=None):
        results = self.expenses
        if keyword:
            kw = keyword.lower()
            results = [e for e in results if kw in e.description.lower() or kw in e.category.lower()]
        if category:
            results = [e for e in results if e.category.lower() == category.lower()]
        if start_date:
            results = [e for e in results if e.date >= start_date]
        if end_date:
            results = [e for e in results if e.date <= end_date]
        if min_amount is not None:
            results = [e for e in results if e.amount >= min_amount]
        if max_amount is not None:
            results = [e for e in results if e.amount <= max_amount]
        return sorted(results, key=lambda e: e.date)

    def get_by_month(self, year, month):
        key = f"{year:04d}-{month:02d}"
        return [e for e in self.expenses if e.month_key() == key]

    def categories_used(self):
        return sorted(set(e.category for e in self.expenses))

    def total(self, expenses=None):
        expenses = self.expenses if expenses is None else expenses
        return round(sum(e.amount for e in expenses), 2)

    # ---------- budgets ----------
    def set_budget(self, category, amount):
        category = Expense._validate_category(category)
        amount = Expense._validate_amount(amount)
        self.budgets[category] = amount

    def get_budget_status(self, year, month):
        month_expenses = self.get_by_month(year, month)
        spent_by_cat = defaultdict(float)
        for e in month_expenses:
            spent_by_cat[e.category] += e.amount

        status = {}
        for cat, budget in self.budgets.items():
            spent = round(spent_by_cat.get(cat, 0.0), 2)
            status[cat] = {
                "budget": budget,
                "spent": spent,
                "remaining": round(budget - spent, 2),
                "percent": round((spent / budget * 100), 1) if budget else 0.0,
            }
        return status

    # ---------- recurring expenses ----------
    def process_recurring(self, year, month):
        """
        Create this month's instance of each recurring expense
        (matched by category + description) if it hasn't been
        created yet for that month.
        """
        key = f"{year:04d}-{month:02d}"
        already_present = {
            (e.category, e.description)
            for e in self.expenses if e.month_key() == key and e.recurring
        }
        templates = {}
        for e in self.expenses:
            if e.recurring:
                templates[(e.category, e.description)] = e

        created = []
        for sig, template in templates.items():
            if sig in already_present:
                continue
            day = template.date[-2:]
            new_date = f"{key}-{day}"
            try:
                new_exp = self.add_expense(
                    new_date, template.amount, template.category,
                    template.description, recurring=True,
                )
                created.append(new_exp)
            except ValidationError:
                # e.g. day 31 doesn't exist in this month - skip gracefully
                continue
        return created

    # ---------- prediction ----------
    def predict_next_month(self, lookback=3):
        """Naive prediction: average per-category spend over the last N months with data."""
        months = sorted(set(e.month_key() for e in self.expenses), reverse=True)[:lookback]
        if not months:
            return {}

        totals = defaultdict(list)
        for m in months:
            cat_totals = defaultdict(float)
            for e in self.expenses:
                if e.month_key() == m:
                    cat_totals[e.category] += e.amount
            for cat, amt in cat_totals.items():
                totals[cat].append(amt)

        return {cat: round(sum(amts) / len(months), 2) for cat, amts in totals.items()}
