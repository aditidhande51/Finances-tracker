"""
file_handler.py
Handles all file persistence for the Personal Finance Tracker:
    - JSON save/load (atomic writes)
    - CSV export/import
    - Timestamped backups + restore
All failure modes raise FileHandlerError with a clear message,
so the UI layer never has to deal with raw OSError/json errors.
"""

import json
import csv
import os
import shutil
import itertools
from datetime import datetime

from expenses import Expense, ExpenseManager, ValidationError

DATA_DIR = "data"
DATA_FILE = os.path.join(DATA_DIR, "expenses.json")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
CSV_FILE = os.path.join(DATA_DIR, "expenses_export.csv")


class FileHandlerError(Exception):
    """Raised for any file I/O problem (missing file, bad permissions, corrupt data...)."""
    pass


def ensure_data_dir():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(BACKUP_DIR, exist_ok=True)
    except OSError as e:
        raise FileHandlerError(f"Could not create data directory: {e}")


# ---------------------------------------------------------------- JSON ----
def save_data(manager: ExpenseManager, filepath=DATA_FILE):
    """Save expenses + budgets to JSON. Writes to a temp file then renames,
    so a crash mid-write can never corrupt the existing data file."""
    ensure_data_dir()
    payload = {
        "expenses": [e.to_dict() for e in manager.expenses],
        "budgets": manager.budgets,
        "saved_at": datetime.now().isoformat(),
    }
    tmp_path = filepath + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp_path, filepath)
    except PermissionError:
        raise FileHandlerError(f"Permission denied writing to '{filepath}'.")
    except OSError as e:
        raise FileHandlerError(f"Could not save data: {e}")
    return filepath


def load_data(filepath=DATA_FILE) -> ExpenseManager:
    """Load expenses + budgets from JSON. Missing file = fresh start (not an error).
    Corrupt individual records are skipped with a warning rather than failing entirely."""
    manager = ExpenseManager()
    if not os.path.exists(filepath):
        return manager

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except PermissionError:
        raise FileHandlerError(f"Permission denied reading '{filepath}'.")
    except json.JSONDecodeError as e:
        raise FileHandlerError(f"Data file is corrupted and could not be parsed: {e}")
    except OSError as e:
        raise FileHandlerError(f"Could not read data: {e}")

    max_id = 0
    for d in payload.get("expenses", []):
        try:
            exp = Expense.from_dict(d)
            manager.expenses.append(exp)
            max_id = max(max_id, exp.id)
        except (ValidationError, KeyError, TypeError) as e:
            print(f"  Warning: skipped a corrupted expense record ({e})")

    # Keep the auto-increment ID counter ahead of anything we just loaded.
    Expense._id_counter = itertools.count(max_id + 1)
    manager.budgets = payload.get("budgets", {})
    return manager


# ---------------------------------------------------------------- backup ----
def backup_data(filepath=DATA_FILE):
    ensure_data_dir()
    if not os.path.exists(filepath):
        raise FileHandlerError("No data file exists yet to back up.")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"expenses_backup_{timestamp}.json")
    try:
        shutil.copy2(filepath, backup_path)
    except OSError as e:
        raise FileHandlerError(f"Backup failed: {e}")
    return backup_path


def list_backups():
    ensure_data_dir()
    files = [f for f in os.listdir(BACKUP_DIR) if f.endswith(".json")]
    return sorted(files, reverse=True)


def restore_backup(backup_filename, filepath=DATA_FILE) -> ExpenseManager:
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    if not os.path.exists(backup_path):
        raise FileHandlerError(f"Backup '{backup_filename}' not found.")
    try:
        if os.path.exists(filepath):
            # safety net: keep a copy of what we're about to overwrite
            shutil.copy2(filepath, filepath + ".before_restore")
        shutil.copy2(backup_path, filepath)
    except OSError as e:
        raise FileHandlerError(f"Restore failed: {e}")
    return load_data(filepath)


# ------------------------------------------------------------------ CSV ----
def export_csv(manager: ExpenseManager, filepath=CSV_FILE):
    ensure_data_dir()
    try:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "date", "amount", "category", "description", "recurring"])
            for e in sorted(manager.expenses, key=lambda x: x.date):
                writer.writerow([e.id, e.date, e.amount, e.category, e.description, e.recurring])
    except PermissionError:
        raise FileHandlerError(f"Permission denied writing to '{filepath}'.")
    except OSError as e:
        raise FileHandlerError(f"CSV export failed: {e}")
    return filepath


def import_csv(filepath, manager: ExpenseManager):
    """Import rows from a CSV file. Returns (imported_count, skipped_count).
    Invalid rows are skipped individually rather than aborting the whole import."""
    if not os.path.exists(filepath):
        raise FileHandlerError(f"File '{filepath}' not found.")

    imported, skipped = 0, 0
    try:
        with open(filepath, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            required = {"date", "amount", "category"}
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                raise FileHandlerError(f"CSV must contain at least these columns: {', '.join(sorted(required))}")
            for row in reader:
                try:
                    manager.add_expense(
                        row["date"], row["amount"], row["category"],
                        row.get("description", ""),
                        str(row.get("recurring", "False")).strip().lower() == "true",
                    )
                    imported += 1
                except ValidationError:
                    skipped += 1
    except PermissionError:
        raise FileHandlerError(f"Permission denied reading '{filepath}'.")
    except csv.Error as e:
        raise FileHandlerError(f"CSV parsing error: {e}")
    return imported, skipped
