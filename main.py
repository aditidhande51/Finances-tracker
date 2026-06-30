"""
main.py
Personal Finance Tracker - entry point.

Run with:  python main.py

Ties together expenses.py (data + logic), file_handler.py (persistence),
and reports.py (statistics / visualizations) behind a simple text menu.
"""

import sys
from datetime import datetime

from expenses import ExpenseManager, ValidationError, DEFAULT_CATEGORIES
import file_handler as fh
import reports


def prompt(text, default=None):
    suffix = f" [{default}]" if default not in (None, "") else ""
    val = input(f"{text}{suffix}: ").strip()
    return val if val else default


def prompt_date(text="Date (YYYY-MM-DD)", default_today=True):
    default = datetime.now().strftime("%Y-%m-%d") if default_today else None
    return prompt(text, default)


def prompt_float(text):
    while True:
        raw = input(f"{text}: ").strip()
        try:
            return float(raw)
        except ValueError:
            print("  Please enter a valid number.")


class FinanceTracker:
    def __init__(self):
        self.manager = ExpenseManager()
        self.dirty = False

    # ---------------------------------------------------------- startup ----
    def load(self):
        try:
            self.manager = fh.load_data()
            print(f"Loaded {len(self.manager.expenses)} expense(s) from disk.")
        except fh.FileHandlerError as e:
            print(f"Warning: {e}")
            print("Starting with an empty expense list.")
            self.manager = ExpenseManager()

    def save(self):
        try:
            fh.save_data(self.manager)
            self.dirty = False
        except fh.FileHandlerError as e:
            print(f"Error saving data: {e}")

    # ------------------------------------------------------------- menu ----
    def run(self):
        print("=" * 60)
        print("          PERSONAL FINANCE TRACKER")
        print("=" * 60)
        self.load()

        actions = {
            "1": self.add_expense,
            "2": self.view_expenses,
            "3": self.search_expenses,
            "4": self.generate_monthly_report,
            "5": self.view_category_breakdown,
            "6": self.set_budget,
            "7": self.export_import_csv,
            "8": self.view_statistics,
            "9": self.backup_restore,
            "10": self.recurring_and_prediction,
            "11": self.edit_delete_expense,
            "h": self.show_help,
        }

        while True:
            self.print_menu()
            choice = input("\nEnter your choice: ").strip().lower()
            if choice == "0":
                self.exit_app()
                break
            action = actions.get(choice)
            if action:
                try:
                    action()
                except ValidationError as e:
                    print(f"  Input error: {e}")
                except fh.FileHandlerError as e:
                    print(f"  File error: {e}")
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    print(f"  Unexpected error: {e}")
            else:
                print("Invalid choice! Please try again (or 'h' for help).")

    def print_menu(self):
        print("\n" + "=" * 40)
        print("              MAIN MENU")
        print("=" * 40)
        print("1.  Add New Expense")
        print("2.  View All Expenses")
        print("3.  Search / Filter Expenses")
        print("4.  Generate Monthly Report")
        print("5.  View Category Breakdown")
        print("6.  Set/Update Budget")
        print("7.  Export/Import CSV")
        print("8.  View Statistics & Trends")
        print("9.  Backup/Restore Data")
        print("10. Recurring Expenses & Prediction")
        print("11. Edit/Delete an Expense")
        print("h.  Help")
        print("0.  Save & Exit")
        print("=" * 40)
        if self.dirty:
            print("(unsaved changes)")

    def exit_app(self):
        self.save()
        print("\n" + "=" * 60)
        print("Data saved. Thank you for using Personal Finance Tracker!")
        print("=" * 60)

    def show_help(self):
        print("\n--- HELP ---")
        print("Dates use YYYY-MM-DD format (e.g. 2026-06-30).")
        print("Amounts must be positive numbers, e.g. 12.50.")
        print(f"Suggested categories: {', '.join(DEFAULT_CATEGORIES)}")
        print("Data auto-saves to data/expenses.json after every change.")
        print("Use option 9 regularly to create timestamped backups.")

    # --------------------------------------------------------- features ----
    def add_expense(self):
        print("\n--- ADD NEW EXPENSE ---")
        print(f"Common categories: {', '.join(DEFAULT_CATEGORIES)}")
        date_str = prompt_date()
        amount = prompt_float("Amount ($)")
        category = prompt("Category", "Other")
        description = prompt("Description (optional)", "")
        is_recurring = (prompt("Recurring monthly? (y/n)", "n") or "n").lower().startswith("y")

        expense = self.manager.add_expense(date_str, amount, category, description, is_recurring)
        self.dirty = True
        self.save()
        print(f"Expense added: {expense}")

    def view_expenses(self):
        print("\n--- ALL EXPENSES ---")
        if not self.manager.expenses:
            print("No expenses recorded yet.")
            return
        for e in sorted(self.manager.expenses, key=lambda x: x.date):
            print(f"  {e}")
        print(f"\nTotal: ${self.manager.total():,.2f} across {len(self.manager.expenses)} expense(s)")

    def search_expenses(self):
        print("\n--- SEARCH / FILTER EXPENSES ---")
        keyword = prompt("Keyword in description/category (blank to skip)", "")
        category = prompt("Exact category (blank to skip)", "")
        start = prompt("Start date YYYY-MM-DD (blank to skip)", "")
        end = prompt("End date YYYY-MM-DD (blank to skip)", "")
        min_amt = prompt("Min amount (blank to skip)", "")
        max_amt = prompt("Max amount (blank to skip)", "")

        results = self.manager.search(
            keyword=keyword or None,
            category=category or None,
            start_date=start or None,
            end_date=end or None,
            min_amount=float(min_amt) if min_amt else None,
            max_amount=float(max_amt) if max_amt else None,
        )
        if not results:
            print("No matching expenses found.")
            return
        for e in results:
            print(f"  {e}")
        print(f"\n{len(results)} match(es) totaling ${self.manager.total(results):,.2f}")

    def generate_monthly_report(self):
        year = int(prompt("Year", str(datetime.now().year)))
        month = int(prompt("Month (1-12)", str(datetime.now().month)))
        print(reports.monthly_summary(self.manager, year, month))

    def view_category_breakdown(self):
        print(reports.category_breakdown(self.manager))

    def set_budget(self):
        print("\n--- SET/UPDATE BUDGET ---")
        if self.manager.budgets:
            print("Current budgets:")
            for cat, amt in self.manager.budgets.items():
                print(f"  {cat}: ${amt:,.2f}/month")
        category = prompt("Category", "Other")
        amount = prompt_float("Monthly budget amount ($)")
        self.manager.set_budget(category, amount)
        self.dirty = True
        self.save()
        print(f"Budget set: {category} = ${amount:,.2f}/month")

    def export_import_csv(self):
        print("\n--- EXPORT / IMPORT CSV ---")
        choice = (prompt("Export (e) or Import (i)?", "e") or "e").lower()
        if choice == "e":
            path = fh.export_csv(self.manager)
            print(f"Exported {len(self.manager.expenses)} expense(s) to {path}")
        else:
            path = prompt("CSV file path to import", fh.CSV_FILE)
            imported, skipped = fh.import_csv(path, self.manager)
            self.dirty = True
            self.save()
            print(f"Imported {imported} expense(s), skipped {skipped} invalid row(s).")

    def view_statistics(self):
        print(reports.overall_statistics(self.manager))
        print(reports.trend_analysis(self.manager))

    def backup_restore(self):
        print("\n--- BACKUP / RESTORE ---")
        choice = (prompt("Backup (b) or Restore (r)?", "b") or "b").lower()
        if choice == "b":
            self.save()
            path = fh.backup_data()
            print(f"Backup created: {path}")
        else:
            backups = fh.list_backups()
            if not backups:
                print("No backups available.")
                return
            for i, b in enumerate(backups, 1):
                print(f"  {i}. {b}")
            idx = prompt("Backup number to restore", "1")
            try:
                selected = backups[int(idx) - 1]
            except (ValueError, IndexError, TypeError):
                print("Invalid selection.")
                return
            confirm = prompt(f"This will overwrite current data with '{selected}'. Continue? (y/n)", "n")
            if (confirm or "n").lower().startswith("y"):
                self.manager = fh.restore_backup(selected)
                self.dirty = False
                print("Data restored successfully.")

    def recurring_and_prediction(self):
        print("\n--- RECURRING EXPENSES & PREDICTION ---")
        year = int(prompt("Process recurring expenses for year", str(datetime.now().year)))
        month = int(prompt("Month", str(datetime.now().month)))
        created = self.manager.process_recurring(year, month)
        if created:
            self.dirty = True
            self.save()
            print(f"Generated {len(created)} recurring expense(s) for {year}-{month:02d}.")
        else:
            print("No new recurring expenses needed for that month.")
        print(reports.prediction_report(self.manager))

    def edit_delete_expense(self):
        print("\n--- EDIT / DELETE EXPENSE ---")
        eid = prompt("Expense ID", "")
        if not eid:
            return
        try:
            eid = int(eid)
        except ValueError:
            print("Invalid ID.")
            return
        expense = self.manager.get_expense(eid)
        if not expense:
            print("Expense not found.")
            return
        print(f"Found: {expense}")
        action = (prompt("Edit (e) or Delete (d)?", "e") or "e").lower()
        if action == "d":
            self.manager.remove_expense(eid)
            self.dirty = True
            self.save()
            print("Expense deleted.")
        else:
            date_str = prompt_date("New date", default_today=False) or expense.date
            amount = prompt("New amount", str(expense.amount))
            category = prompt("New category", expense.category)
            description = prompt("New description", expense.description)
            self.manager.update_expense(
                eid, date=date_str, amount=float(amount), category=category, description=description
            )
            self.dirty = True
            self.save()
            print("Expense updated.")


def main():
    tracker = FinanceTracker()
    try:
        tracker.run()
    except KeyboardInterrupt:
        print("\n\nInterrupted. Saving data before exit...")
        tracker.save()
        print("Goodbye!")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        print("Attempting to save data before exiting...")
        tracker.save()
        sys.exit(1)


if __name__ == "__main__":
    main()
