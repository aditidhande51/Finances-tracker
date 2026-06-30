"""
reports.py
Generates text-based reports and simple bar-chart visualizations
from an ExpenseManager: monthly summaries, category breakdowns,
spending trends, overall statistics, and next-month predictions.
"""

import calendar
from collections import defaultdict

BAR_CHAR = "#"
MAX_BAR_WIDTH = 40


def _bar(amount, max_amount, width=MAX_BAR_WIDTH):
    if max_amount <= 0:
        return ""
    filled = int((amount / max_amount) * width)
    filled = max(filled, 1) if amount > 0 else 0
    return BAR_CHAR * filled


def monthly_summary(manager, year, month):
    expenses = manager.get_by_month(year, month)
    month_name = calendar.month_name[month]
    lines = [f"\n{'='*60}", f"   MONTHLY REPORT: {month_name} {year}", f"{'='*60}"]

    if not expenses:
        lines.append("No expenses recorded for this month.")
        return "\n".join(lines)

    total = manager.total(expenses)
    by_cat = defaultdict(float)
    for e in expenses:
        by_cat[e.category] += e.amount

    lines.append(f"Total spent:      ${total:,.2f}")
    lines.append(f"Transactions:     {len(expenses)}")
    lines.append(f"Average expense:  ${total/len(expenses):,.2f}")
    lines.append(f"Highest expense:  ${max(e.amount for e in expenses):,.2f}")
    lines.append(f"Lowest expense:   ${min(e.amount for e in expenses):,.2f}")

    lines.append(f"\n{'-'*60}")
    lines.append("CATEGORY BREAKDOWN")
    lines.append(f"{'-'*60}")
    max_cat = max(by_cat.values())
    for cat, amt in sorted(by_cat.items(), key=lambda x: -x[1]):
        pct = amt / total * 100
        lines.append(f"{cat:<14} ${amt:>9,.2f} ({pct:5.1f}%)  {_bar(amt, max_cat)}")

    budget_status = manager.get_budget_status(year, month)
    if budget_status:
        lines.append(f"\n{'-'*60}")
        lines.append("BUDGET vs ACTUAL")
        lines.append(f"{'-'*60}")
        for cat, info in budget_status.items():
            status = "OVER" if info["remaining"] < 0 else "OK"
            lines.append(
                f"{cat:<14} budget ${info['budget']:>8,.2f}  spent ${info['spent']:>8,.2f}  "
                f"({info['percent']:>5.1f}%) [{status}]"
            )

    return "\n".join(lines)


def category_breakdown(manager, expenses=None):
    expenses = manager.expenses if expenses is None else expenses
    if not expenses:
        return "No expenses to summarize."

    by_cat = defaultdict(float)
    for e in expenses:
        by_cat[e.category] += e.amount
    total = sum(by_cat.values())
    max_cat = max(by_cat.values())

    lines = [f"\n{'='*60}", "   CATEGORY BREAKDOWN (ALL TIME)", f"{'='*60}"]
    for cat, amt in sorted(by_cat.items(), key=lambda x: -x[1]):
        pct = amt / total * 100
        lines.append(f"{cat:<14} ${amt:>9,.2f} ({pct:5.1f}%)  {_bar(amt, max_cat)}")
    lines.append(f"{'-'*60}")
    lines.append(f"{'TOTAL':<14} ${total:>9,.2f}")
    return "\n".join(lines)


def trend_analysis(manager, num_months=6):
    months = sorted(set(e.month_key() for e in manager.expenses))[-num_months:]
    if not months:
        return "No data available for trend analysis."

    totals = [(m, manager.total([e for e in manager.expenses if e.month_key() == m])) for m in months]
    max_total = max(t for _, t in totals)

    lines = [f"\n{'='*60}", f"   SPENDING TREND (Last {len(months)} Months)", f"{'='*60}"]
    for m, total in totals:
        lines.append(f"{m}   ${total:>9,.2f}  {_bar(total, max_total)}")

    if len(totals) >= 2:
        change = totals[-1][1] - totals[-2][1]
        direction = "up" if change > 0 else "down" if change < 0 else "flat"
        lines.append(f"\nMost recent month is {direction} ${abs(change):,.2f} vs the prior month.")
    return "\n".join(lines)


def overall_statistics(manager):
    if not manager.expenses:
        return "No expenses recorded yet."

    total = manager.total()
    amounts = [e.amount for e in manager.expenses]
    months = sorted(set(e.month_key() for e in manager.expenses))

    lines = [f"\n{'='*60}", "   OVERALL STATISTICS", f"{'='*60}"]
    lines.append(f"Total expenses recorded: {len(manager.expenses)}")
    lines.append(f"Total amount spent:      ${total:,.2f}")
    lines.append(f"Average transaction:     ${total/len(amounts):,.2f}")
    lines.append(f"Largest transaction:     ${max(amounts):,.2f}")
    lines.append(f"Smallest transaction:    ${min(amounts):,.2f}")
    lines.append(f"Categories used:         {len(manager.categories_used())}")
    lines.append(f"Months tracked:          {len(months)}")
    if months:
        lines.append(f"Average monthly spend:   ${total/len(months):,.2f}")
    return "\n".join(lines)


def prediction_report(manager):
    prediction = manager.predict_next_month()
    if not prediction:
        return "Not enough history yet to make a prediction."

    lines = [f"\n{'='*60}", "   NEXT MONTH PREDICTION (avg of recent months)", f"{'='*60}"]
    total = 0.0
    for cat, amt in sorted(prediction.items(), key=lambda x: -x[1]):
        lines.append(f"{cat:<14} ~${amt:>9,.2f}")
        total += amt
    lines.append(f"{'-'*60}")
    lines.append(f"{'Estimated total':<14} ~${total:>9,.2f}")
    return "\n".join(lines)
