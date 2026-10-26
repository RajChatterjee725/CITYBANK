import os
import re
import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "banking.db"))
username = os.getenv("ADMIN_USERNAME", "admin")
password = os.getenv("ADMIN_PASSWORD", re.sub(r"\s+", "", username).lower())

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON")
conn.execute(
    """INSERT INTO users(username, password_hash, role) VALUES(?,?,'Admin')
       ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash,
       role='Admin', is_active=1""",
    (username, generate_password_hash(password))
)
admin_user_id = conn.execute(
    "SELECT user_id FROM users WHERE username=?",
    (username,)
).fetchone()[0]
for user_id, existing_username in conn.execute(
    """SELECT user_id, username FROM users
       WHERE user_id != ?
       AND user_id NOT IN (SELECT user_id FROM customer_logins)""",
    (admin_user_id,)
).fetchall():
    user_password = re.sub(r"\s+", "", existing_username).lower()
    conn.execute(
        "UPDATE users SET password_hash=? WHERE user_id=?",
        (generate_password_hash(user_password), user_id)
    )

for customer_id, full_name in conn.execute(
    "SELECT customer_id, full_name FROM customers ORDER BY customer_id"
).fetchall():
    existing_mapping = conn.execute(
        "SELECT user_id FROM customer_logins WHERE customer_id=?",
        (customer_id,)
    ).fetchone()
    mapped_user_id = existing_mapping[0] if existing_mapping else None
    base_username = re.sub(r"[^a-z0-9]", "", full_name.lower()) or f"customer{customer_id}"
    customer_username = base_username
    suffix = str(customer_id)
    while True:
        existing_user = conn.execute(
            "SELECT user_id FROM users WHERE username=?",
            (customer_username,)
        ).fetchone()
        if existing_user is None or existing_user[0] == mapped_user_id:
            break
        customer_username = f"{base_username}{suffix}"
        suffix = str(int(suffix) + 1)

    customer_password_hash = generate_password_hash(customer_username)
    if mapped_user_id is None:
        cursor = conn.execute(
            """INSERT INTO users(username, password_hash, role, is_active)
               VALUES(?, ?, 'Staff', 1)""",
            (customer_username, customer_password_hash)
        )
        customer_user_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO customer_logins(user_id, customer_id) VALUES(?, ?)",
            (customer_user_id, customer_id)
        )
    else:
        customer_user_id = mapped_user_id
        conn.execute(
            """UPDATE users SET username=?, password_hash=?, role='Staff', is_active=1
               WHERE user_id=?""",
            (customer_username, customer_password_hash, customer_user_id)
        )

conn.commit()
conn.close()
print("Admin user created/updated.")
print(f"Username: {username}")
print(f"Password: {password}")
print("Customer logins created/updated. Each customer username is also the password.")
