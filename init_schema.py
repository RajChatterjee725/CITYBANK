import os
import sqlite3

root = os.path.dirname(__file__)
db_path = os.getenv("DB_PATH", os.path.join(root, "banking.db"))
schema_path = os.path.join(root, "schema.sql")

conn = sqlite3.connect(db_path)
conn.execute("PRAGMA foreign_keys = ON")
with open(schema_path, "r", encoding="utf-8") as f:
    conn.executescript(f.read())
conn.close()
print(f"Database initialized: {db_path}")
