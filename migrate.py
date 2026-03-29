"""
Run this ONCE to add new columns to your existing database.
Usage: python migrate.py
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'fitness_tracker.db')
if not os.path.exists(DB_PATH):
    # Try root directory
    DB_PATH = 'fitness_tracker.db'

print(f"Migrating: {DB_PATH}")
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

new_columns = [
    ("user", "gender",         "TEXT DEFAULT 'male'"),
    ("user", "activity_level", "TEXT DEFAULT 'moderate'"),
    ("user", "target_protein", "REAL DEFAULT 0"),
    ("user", "target_carbs",   "REAL DEFAULT 0"),
    ("user", "target_fat",     "REAL DEFAULT 0"),
    ("user", "goal_weeks",     "INTEGER DEFAULT 12"),
    ("user", "onboarded",      "INTEGER DEFAULT 1"),
    ("user", "water_goal_ml",  "INTEGER DEFAULT 2500"),
    ("food_log", "unit",       "TEXT DEFAULT 'g'"),
]

for table, col, col_def in new_columns:
    try:
        c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
        print(f"  ✅ Added {table}.{col}")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print(f"  ⏭️  {table}.{col} already exists")
        else:
            print(f"  ❌ {table}.{col}: {e}")

conn.commit()
conn.close()
print("\nDone! Now restart Flask: python app.py")