# Personal Finance Tracker

A complete, menu-driven command-line app for tracking expenses, budgets,
and spending trends — built as a modular Python project.

## Run it

```
python main.py
```

No external dependencies — pure standard library (`json`, `csv`, `datetime`, etc).
Requires Python 3.8+.

## Project structure

```
finance_tracker/
├── main.py          # Menu system / UI layer, ties everything together
├── expenses.py       # Expense + ExpenseManager classes, validation, budgets,
│                      # recurring-expense logic, simple prediction
├── file_handler.py   # JSON persistence, CSV import/export, backup/restore
├── reports.py         # Monthly summaries, category breakdowns, trends,
│                      # text-based bar-chart visualizations
└── data/              # Created automatically at first run
    ├── expenses.json        # Your saved data (expenses + budgets)
    ├── expenses_export.csv  # Created when you export to CSV
    └── backups/             # Timestamped JSON backups
```

## Features

- **Add / view / edit / delete expenses** with date, amount, category,
  description, and an optional "recurring monthly" flag.
- **Validation** on every input: dates must be real and not in the future,
  amounts must be positive numbers, categories can't be blank.
- **Search & filter** by keyword, exact category, date range, or amount range.
- **Monthly reports** with totals, averages, category breakdown (with a
  text bar chart), and budget-vs-actual comparison.
- **Budgets** per category, tracked against actual monthly spend.
- **Recurring expenses**: mark an expense recurring once, then "process"
  a given month to auto-generate that month's instance.
- **Prediction**: naive next-month estimate per category, averaged from
  recent months of history.
- **CSV export/import** for use in Excel/Sheets or migrating data in.
- **Backup & restore**: timestamped JSON snapshots, with a safety copy
  made automatically before any restore overwrites current data.
- **Robust error handling**: missing files, permission errors, and
  corrupted JSON are all caught and reported without crashing the app;
  individual bad rows in CSV imports or corrupted records in JSON are
  skipped rather than failing the whole load.

## Data format

Expenses are stored as JSON:

```json
{
  "expenses": [
    {"id": 1, "date": "2026-06-15", "amount": 1200.0,
     "category": "Housing", "description": "Rent", "recurring": false}
  ],
  "budgets": {"Food": 200.0}
}
```

## Notes / things you could extend

- Swap the text bar charts in `reports.py` for `matplotlib` if you want
  real charts (kept text-only here to avoid extra dependencies).
- The prediction model is a simple 3-month average — could be replaced
  with a weighted average or linear regression for trend-aware estimates.
- Multi-user support would mean namespacing `data/` by user.
