import os
import re
import sqlite3
import secrets
from datetime import date
from decimal import Decimal, InvalidOperation
from functools import wraps

from flask import Flask, abort, jsonify, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-development-secret")
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "banking.db"))


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if session.get("role") == "Customer":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def customer_login_username(conn, customer_id, full_name):
    base_username = re.sub(r"[^a-z0-9]", "", full_name.lower()) or f"customer{customer_id}"
    mapping = conn.execute(
        "SELECT user_id FROM customer_logins WHERE customer_id=?",
        (customer_id,)
    ).fetchone()
    mapped_user_id = mapping["user_id"] if mapping else None
    username = base_username
    suffix = str(customer_id)
    while True:
        existing = conn.execute(
            "SELECT user_id FROM users WHERE username=?",
            (username,)
        ).fetchone()
        if existing is None or existing["user_id"] == mapped_user_id:
            break
        username = f"{base_username}{suffix}"
        suffix = f"{int(suffix) + 1}"

    password_hash = generate_password_hash(username)
    if mapped_user_id is None:
        cursor = conn.execute(
            """INSERT INTO users(username, password_hash, role, is_active)
               VALUES(?, ?, 'Staff', 1)""",
            (username, password_hash)
        )
        user_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO customer_logins(user_id, customer_id) VALUES(?, ?)",
            (user_id, customer_id)
        )
    else:
        user_id = mapped_user_id
        conn.execute(
            """UPDATE users SET username=?, password_hash=?, role='Staff', is_active=1
               WHERE user_id=?""",
            (username, password_hash, user_id)
        )
    return username


def valid_money(value):
    try:
        amount = Decimal(value).quantize(Decimal("0.01"))
        if amount <= 0 or not amount.is_finite():
            return None
        return amount
    except (InvalidOperation, TypeError):
        return None


@app.route("/")
def index():
    return redirect(url_for("dashboard" if "user_id" in session else "login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    with get_db() as conn:
        login_users = conn.execute(
            """SELECT u.username,
                      CASE WHEN cl.customer_id IS NOT NULL THEN 'Customer'
                           ELSE u.role END AS role
               FROM users u LEFT JOIN customer_logins cl ON cl.user_id=u.user_id
               WHERE u.is_active=1 ORDER BY role, u.username"""
        ).fetchall()
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        with get_db() as conn:
            user = conn.execute(
                """SELECT u.user_id, u.username, u.password_hash, u.role, cl.customer_id
                   FROM users u LEFT JOIN customer_logins cl ON cl.user_id=u.user_id
                   WHERE u.username=? AND u.is_active=1""",
                (username,)
            ).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            session["role"] = "Customer" if user["customer_id"] is not None else user["role"]
            if user["customer_id"] is not None:
                session["customer_id"] = user["customer_id"]
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html", login_users=login_users)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    with get_db() as conn:
        if session.get("role") == "Customer":
            customer_id = session.get("customer_id")
            if customer_id is None:
                abort(403)
            customers = 1
            accounts = conn.execute(
                "SELECT COUNT(*) FROM accounts WHERE customer_id=? AND status='Active'",
                (customer_id,)
            ).fetchone()[0]
            total_balance = conn.execute(
                "SELECT COALESCE(SUM(balance),0) FROM accounts WHERE customer_id=? AND status='Active'",
                (customer_id,)
            ).fetchone()[0]
            today_transactions = conn.execute(
                """SELECT COUNT(*) FROM transactions t
                   JOIN accounts a ON a.account_id=t.account_id
                   WHERE a.customer_id=? AND date(t.created_at)=date('now','localtime')""",
                (customer_id,)
            ).fetchone()[0]
            recent = conn.execute("""SELECT t.transaction_id, t.transaction_type, t.amount, t.created_at,
                                          strftime('%Y-%m-%d %H:%M', t.created_at) AS display_created_at,
                                          t.status, a.account_no
                                   FROM transactions t JOIN accounts a ON a.account_id=t.account_id
                                   WHERE a.customer_id=?
                                   ORDER BY t.created_at DESC LIMIT 8""", (customer_id,)).fetchall()
        else:
            customers = conn.execute("SELECT COUNT(*) FROM customers WHERE status='Active'").fetchone()[0]
            accounts = conn.execute("SELECT COUNT(*) FROM accounts WHERE status='Active'").fetchone()[0]
            total_balance = conn.execute("SELECT COALESCE(SUM(balance),0) FROM accounts WHERE status='Active'").fetchone()[0]
            today_transactions = conn.execute("SELECT COUNT(*) FROM transactions WHERE date(created_at)=date('now','localtime')").fetchone()[0]
            recent = conn.execute("""SELECT t.transaction_id, t.transaction_type, t.amount, t.created_at,
                                          strftime('%Y-%m-%d %H:%M', t.created_at) AS display_created_at,
                                          t.status, a.account_no
                                   FROM transactions t JOIN accounts a ON a.account_id=t.account_id
                                   ORDER BY t.created_at DESC LIMIT 8""").fetchall()
    return render_template("dashboard.html", customers=customers, accounts=accounts,
                           total_balance=total_balance, today_transactions=today_transactions, recent=recent)


@app.route("/customers")
@admin_required
def customers_list():
    filters = {
        "q": request.args.get("q", "").strip(),
        "customer_id": request.args.get("customer_id", "").strip(),
        "status": request.args.get("status", "").strip(),
        "min_accounts": request.args.get("min_accounts", "").strip(),
        "max_accounts": request.args.get("max_accounts", "").strip(),
        "date_from": request.args.get("date_from", "").strip(),
        "date_to": request.args.get("date_to", "").strip(),
    }
    conditions = []
    params = []
    if filters["q"]:
        conditions.append(
            "(full_name LIKE ? OR COALESCE(email,'') LIKE ? "
            "OR COALESCE(phone,'') LIKE ? OR COALESCE(address,'') LIKE ?)"
        )
        pattern = f"%{filters['q']}%"
        params.extend((pattern, pattern, pattern, pattern))
    if filters["customer_id"].isdigit():
        conditions.append("customer_id=?")
        params.append(int(filters["customer_id"]))
    if filters["status"] in ("Active", "Inactive"):
        conditions.append("status=?")
        params.append(filters["status"])

    account_counts = {}
    for key in ("min_accounts", "max_accounts"):
        if filters[key]:
            try:
                count = int(filters[key])
                if count < 0:
                    raise ValueError
                account_counts[key] = count
            except ValueError:
                flash(f"Enter a valid non-negative value for {key.replace('_', ' ')}.", "error")
                filters[key] = ""
    if (
        "min_accounts" in account_counts
        and "max_accounts" in account_counts
        and account_counts["min_accounts"] > account_counts["max_accounts"]
    ):
        flash("Minimum account count cannot exceed maximum account count.", "error")
        account_counts.clear()
        filters["min_accounts"] = ""
        filters["max_accounts"] = ""
    for key, operator in (("min_accounts", ">="), ("max_accounts", "<=")):
        if key in account_counts:
            conditions.append(f"account_count {operator} ?")
            params.append(account_counts[key])

    customer_dates = {}
    for key in ("date_from", "date_to"):
        if filters[key]:
            try:
                customer_dates[key] = date.fromisoformat(filters[key])
            except ValueError:
                date_label = "start" if key == "date_from" else "end"
                flash(f"Enter a valid {date_label} date.", "error")
                filters[key] = ""
    if (
        "date_from" in customer_dates
        and "date_to" in customer_dates
        and customer_dates["date_from"] > customer_dates["date_to"]
    ):
        flash("Start date cannot be after end date.", "error")
        customer_dates.clear()
        filters["date_from"] = ""
        filters["date_to"] = ""
    for key, operator in (("date_from", ">="), ("date_to", "<=")):
        if key in customer_dates:
            conditions.append(f"date(created_at) {operator} ?")
            params.append(customer_dates[key].isoformat())

    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    with get_db() as conn:
        rows = conn.execute(
            """WITH customer_rows AS (
                   SELECT c.*, COUNT(a.account_id) AS account_count
                   FROM customers c LEFT JOIN accounts a ON a.customer_id=c.customer_id
                   GROUP BY c.customer_id
               )
               SELECT * FROM customer_rows"""
            + where
            + " ORDER BY customer_id DESC",
            params
        ).fetchall()
    return render_template("customers.html", customers=rows, filters=filters)


@app.route("/customers/new", methods=["GET", "POST"])
@app.route("/customers/<int:customer_id>/edit", methods=["GET", "POST"])
@admin_required
def customer_form(customer_id=None):
    with get_db() as conn:
        customer = conn.execute("SELECT * FROM customers WHERE customer_id=?", (customer_id,)).fetchone() if customer_id else None
        if customer_id and not customer:
            flash("Customer not found.", "error")
            return redirect(url_for("customers_list"))
        if request.method == "POST":
            name = request.form.get("full_name", "").strip()
            email = request.form.get("email", "").strip() or None
            phone = request.form.get("phone", "").strip() or None
            address = request.form.get("address", "").strip() or None
            if not name:
                flash("Customer name is required.", "error")
            else:
                try:
                    if customer_id:
                        conn.execute("UPDATE customers SET full_name=?,email=?,phone=?,address=? WHERE customer_id=?",
                                     (name, email, phone, address, customer_id))
                    else:
                        cursor = conn.execute(
                            "INSERT INTO customers(full_name,email,phone,address) VALUES(?,?,?,?)",
                            (name, email, phone, address)
                        )
                        customer_id = cursor.lastrowid
                    login_username = customer_login_username(conn, customer_id, name)
                    conn.commit()
                    flash(
                        f"Customer saved. Login username and password: {login_username}",
                        "success"
                    )
                    return redirect(url_for("customers_list"))
                except sqlite3.IntegrityError:
                    flash("Could not save customer. Email or phone may already exist.", "error")
    return render_template("customer_form.html", customer=customer)


@app.route("/customers/<int:customer_id>/delete", methods=["POST"])
@admin_required
def customer_delete(customer_id):
    with get_db() as conn:
        customer = conn.execute(
            "SELECT customer_id FROM customers WHERE customer_id=?",
            (customer_id,)
        ).fetchone()
        if customer is None:
            flash("Customer not found.", "error")
            return redirect(url_for("customers_list"))
        customer_login = conn.execute(
            "SELECT user_id FROM customer_logins WHERE customer_id=?",
            (customer_id,)
        ).fetchone()
        if customer_login:
            conn.execute(
                "UPDATE users SET is_active=0 WHERE user_id=?",
                (customer_login["user_id"],)
            )
        conn.execute(
            """DELETE FROM transactions
               WHERE account_id IN (SELECT account_id FROM accounts WHERE customer_id=?)""",
            (customer_id,)
        )
        conn.execute("DELETE FROM accounts WHERE customer_id=?", (customer_id,))
        conn.execute("DELETE FROM customers WHERE customer_id=?", (customer_id,))
        conn.commit()
        flash("Customer, their accounts, and related transactions deleted.", "success")
    return redirect(url_for("customers_list"))


@app.route("/accounts")
@login_required
def accounts_list():
    filters = {
        "q": request.args.get("q", "").strip(),
        "customer_id": request.args.get("customer_id", "").strip(),
        "account_type_id": request.args.get("account_type_id", "").strip(),
        "branch_id": request.args.get("branch_id", "").strip(),
        "status": request.args.get("status", "").strip(),
        "min_balance": request.args.get("min_balance", "").strip(),
        "max_balance": request.args.get("max_balance", "").strip(),
    }
    with get_db() as conn:
        query = """SELECT a.*, c.full_name, at.type_name, b.branch_name
                   FROM accounts a JOIN customers c ON c.customer_id=a.customer_id
                   JOIN account_types at ON at.account_type_id=a.account_type_id
                   JOIN branches b ON b.branch_id=a.branch_id"""
        conditions = []
        params = []
        if session.get("role") == "Customer":
            customer_id = session.get("customer_id")
            if customer_id is None:
                abort(403)
            conditions.append("a.customer_id=?")
            params.append(customer_id)
        else:
            customer_id = None

        if filters["q"]:
            conditions.append("(a.account_no LIKE ? OR c.full_name LIKE ?)")
            pattern = f"%{filters['q']}%"
            params.extend((pattern, pattern))
        for key, column in (
            ("account_type_id", "a.account_type_id"),
            ("branch_id", "a.branch_id"),
        ):
            if filters[key].isdigit():
                conditions.append(f"{column}=?")
                params.append(int(filters[key]))
        if customer_id is None and filters["customer_id"].isdigit():
            conditions.append("a.customer_id=?")
            params.append(int(filters["customer_id"]))
        if filters["status"] in ("Active", "Closed"):
            conditions.append("a.status=?")
            params.append(filters["status"])

        balances = {}
        for key in ("min_balance", "max_balance"):
            if filters[key]:
                try:
                    amount = Decimal(filters[key])
                    if not amount.is_finite() or amount < 0:
                        raise InvalidOperation
                    balances[key] = amount
                except InvalidOperation:
                    flash(f"Enter a valid non-negative value for {key.replace('_', ' ')}.", "error")
                    filters[key] = ""
        if (
            "min_balance" in balances
            and "max_balance" in balances
            and balances["min_balance"] > balances["max_balance"]
        ):
            flash("Minimum balance cannot exceed maximum balance.", "error")
            balances.clear()
            filters["min_balance"] = ""
            filters["max_balance"] = ""
        for key, operator in (("min_balance", ">="), ("max_balance", "<=")):
            if key in balances:
                conditions.append(f"a.balance {operator} ?")
                params.append(str(balances[key]))

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        accounts = conn.execute(
            query + where + " ORDER BY a.account_id DESC",
            params
        ).fetchall()
        types = conn.execute(
            "SELECT account_type_id, type_name FROM account_types ORDER BY type_name"
        ).fetchall()
        branches = conn.execute(
            "SELECT branch_id, branch_name FROM branches ORDER BY branch_name"
        ).fetchall()
        customers = [] if customer_id is not None else conn.execute(
            "SELECT customer_id, full_name FROM customers ORDER BY full_name"
        ).fetchall()
    return render_template(
        "accounts.html",
        accounts=accounts,
        filters=filters,
        types=types,
        branches=branches,
        customers=customers,
    )


@app.route("/accounts/new", methods=["GET", "POST"])
@login_required
def account_new():
    is_customer = session.get("role") == "Customer"
    customer_id = session.get("customer_id") if is_customer else None
    if is_customer and customer_id is None:
        abort(403)
    with get_db() as conn:
        if is_customer:
            customer = conn.execute(
                "SELECT customer_id FROM customers WHERE customer_id=? AND status='Active'",
                (customer_id,)
            ).fetchone()
            if customer is None:
                abort(403)
            customers = []
        else:
            customers = conn.execute("SELECT customer_id, full_name FROM customers WHERE status='Active' ORDER BY full_name").fetchall()
        types = conn.execute("SELECT account_type_id, type_name FROM account_types ORDER BY type_name").fetchall()
        branches = conn.execute("SELECT branch_id, branch_name FROM branches WHERE status='Active' ORDER BY branch_name").fetchall()
        if request.method == "POST":
            try:
                if not is_customer:
                    customer_id = int(request.form["customer_id"])
                type_id = int(request.form["account_type_id"])
                branch_id = int(request.form["branch_id"])
                if is_customer:
                    opening = Decimal("0.00")
                else:
                    raw_opening = request.form.get("opening_balance", "").strip()
                    opening = Decimal(raw_opening).quantize(Decimal("0.01")) if raw_opening else Decimal("0.00")
                if not opening.is_finite() or opening < 0:
                    raise ValueError()
                if not conn.execute(
                    "SELECT 1 FROM branches WHERE branch_id=? AND status='Active'",
                    (branch_id,)
                ).fetchone():
                    raise ValueError()
                account_no = (
                    "BA" + secrets.token_hex(5).upper()
                    if is_customer
                    else request.form.get("account_no", "").strip() or "BA" + secrets.token_hex(5).upper()
                )
                cur = conn.execute("""INSERT INTO accounts(account_no,customer_id,account_type_id,branch_id,balance)
                                      VALUES(?,?,?,?,?)""", (account_no, customer_id, type_id, branch_id, str(opening)))
                if opening > 0:
                    conn.execute("""INSERT INTO transactions(account_id,transaction_type,amount,description,status,created_by)
                                    VALUES(?,'DEPOSIT',?,'Opening balance','Success',?)""",
                                 (cur.lastrowid, str(opening), session["user_id"]))
                conn.commit()
                flash("Account created successfully.", "success")
                return redirect(url_for("accounts_list"))
            except (ValueError, KeyError, sqlite3.IntegrityError):
                conn.rollback()
                flash("Could not create account. Check the details and ensure the account number is unique.", "error")
    return render_template(
        "account_form.html",
        customers=customers,
        types=types,
        branches=branches,
        is_customer=is_customer,
    )


@app.route("/accounts/<int:account_id>/status", methods=["POST"])
@admin_required
def account_status(account_id):
    status = request.form.get("status")
    if status not in ("Active", "Closed"):
        flash("Invalid account status.", "error")
    else:
        with get_db() as conn:
            conn.execute("UPDATE accounts SET status=? WHERE account_id=?", (status, account_id))
            conn.commit()
        flash(f"Account marked {status.lower()}.", "success")
    return redirect(url_for("accounts_list"))


@app.route("/accounts/<int:account_id>/delete", methods=["POST"])
@admin_required
def account_delete(account_id):
    with get_db() as conn:
        account = conn.execute(
            "SELECT account_id FROM accounts WHERE account_id=?",
            (account_id,)
        ).fetchone()
        if account is None:
            flash("Account not found.", "error")
        else:
            conn.execute(
                "DELETE FROM transactions WHERE account_id=?",
                (account_id,)
            )
            conn.execute("DELETE FROM accounts WHERE account_id=?", (account_id,))
            conn.commit()
            flash("Account and its transaction history deleted.", "success")
    return redirect(url_for("accounts_list"))


@app.route("/accounts/<int:account_id>/close", methods=["POST"])
@login_required
def customer_close_account(account_id):
    customer_id = session.get("customer_id")
    if session.get("role") != "Customer" or customer_id is None:
        abort(403)
    with get_db() as conn:
        cursor = conn.execute(
            """UPDATE accounts SET status='Closed'
               WHERE account_id=? AND customer_id=? AND status='Active'""",
            (account_id, customer_id)
        )
        if cursor.rowcount:
            conn.commit()
            flash("Your account has been closed.", "success")
        else:
            flash("Account not found, not yours, or already closed.", "error")
    return redirect(url_for("accounts_list"))


@app.route("/transactions")
@login_required
def transactions_list():
    filters = {
        "q": request.args.get("q", "").strip(),
        "customer_id": request.args.get("customer_id", "").strip(),
        "account_id": request.args.get("account_id", "").strip(),
        "transaction_type": request.args.get("transaction_type", "").strip(),
        "status": request.args.get("status", "").strip(),
        "date_from": request.args.get("date_from", "").strip(),
        "date_to": request.args.get("date_to", "").strip(),
        "min_amount": request.args.get("min_amount", "").strip(),
        "max_amount": request.args.get("max_amount", "").strip(),
    }
    transaction_types = ("DEPOSIT", "WITHDRAWAL", "TRANSFER_OUT", "TRANSFER_IN")
    with get_db() as conn:
        customer_id = session.get("customer_id") if session.get("role") == "Customer" else None
        if session.get("role") == "Customer" and customer_id is None:
            abort(403)
        query = """SELECT t.*, strftime('%Y-%m-%d %H:%M', t.created_at) AS display_created_at,
                          a.account_no, c.full_name, u.username
                   FROM transactions t JOIN accounts a ON a.account_id=t.account_id
                   JOIN customers c ON c.customer_id=a.customer_id
                   LEFT JOIN users u ON u.user_id=t.created_by"""
        conditions = []
        params = []
        if customer_id is not None:
            conditions.append("a.customer_id=?")
            params.append(customer_id)
        else:
            customer_id = None
        if filters["q"]:
            conditions.append(
                "(a.account_no LIKE ? OR c.full_name LIKE ? OR COALESCE(t.description,'') LIKE ?)"
            )
            pattern = f"%{filters['q']}%"
            params.extend((pattern, pattern, pattern))
        if customer_id is None and filters["customer_id"].isdigit():
            conditions.append("a.customer_id=?")
            params.append(int(filters["customer_id"]))
        if filters["account_id"].isdigit():
            conditions.append("t.account_id=?")
            params.append(int(filters["account_id"]))
        if filters["transaction_type"] in transaction_types:
            conditions.append("t.transaction_type=?")
            params.append(filters["transaction_type"])
        if filters["status"] in ("Success", "Failed"):
            conditions.append("t.status=?")
            params.append(filters["status"])

        dates = {}
        for key in ("date_from", "date_to"):
            if filters[key]:
                try:
                    dates[key] = date.fromisoformat(filters[key])
                except ValueError:
                    flash(f"Enter a valid {key.replace('_', ' ')} date.", "error")
                    filters[key] = ""
        if (
            "date_from" in dates
            and "date_to" in dates
            and dates["date_from"] > dates["date_to"]
        ):
            flash("Start date cannot be after end date.", "error")
            dates.clear()
            filters["date_from"] = ""
            filters["date_to"] = ""
        if "date_from" in dates:
            conditions.append("date(t.created_at)>=?")
            params.append(dates["date_from"].isoformat())
        if "date_to" in dates:
            conditions.append("date(t.created_at)<=?")
            params.append(dates["date_to"].isoformat())

        amounts = {}
        for key in ("min_amount", "max_amount"):
            if filters[key]:
                try:
                    amount = Decimal(filters[key])
                    if not amount.is_finite() or amount < 0:
                        raise InvalidOperation
                    amounts[key] = amount
                except InvalidOperation:
                    flash(f"Enter a valid non-negative value for {key.replace('_', ' ')}.", "error")
                    filters[key] = ""
        if (
            "min_amount" in amounts
            and "max_amount" in amounts
            and amounts["min_amount"] > amounts["max_amount"]
        ):
            flash("Minimum amount cannot exceed maximum amount.", "error")
            amounts.clear()
            filters["min_amount"] = ""
            filters["max_amount"] = ""
        for key, operator in (("min_amount", ">="), ("max_amount", "<=")):
            if key in amounts:
                conditions.append(f"t.amount {operator} ?")
                params.append(str(amounts[key]))

        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = conn.execute(
            query + where + " ORDER BY t.created_at DESC LIMIT 200",
            params
        ).fetchall()
        if customer_id is not None:
            accounts = conn.execute(
                """SELECT account_id, account_no, balance FROM accounts
                   WHERE customer_id=? ORDER BY account_no""",
                (customer_id,)
            ).fetchall()
            customers = []
        else:
            accounts = conn.execute(
                "SELECT account_id, account_no, balance FROM accounts ORDER BY account_no"
            ).fetchall()
            customers = conn.execute(
                "SELECT customer_id, full_name FROM customers ORDER BY full_name"
            ).fetchall()
    return render_template(
        "transactions.html",
        transactions=rows,
        accounts=accounts,
        customers=customers,
        filters=filters,
        transaction_types=transaction_types,
    )


@app.route("/transactions/new", methods=["GET", "POST"])
@login_required
def transaction_new():
    with get_db() as conn:
        customer_id = session.get("customer_id") if session.get("role") == "Customer" else None
        if session.get("role") == "Customer" and customer_id is None:
            abort(403)
        if customer_id is not None:
            accounts = conn.execute(
                """SELECT account_id, account_no, balance FROM accounts
                   WHERE customer_id=? AND status='Active' ORDER BY account_no""",
                (customer_id,)
            ).fetchall()
        else:
            accounts = conn.execute("SELECT account_id, account_no, balance FROM accounts WHERE status='Active' ORDER BY account_no").fetchall()
        if request.method == "POST":
            kind = request.form.get("transaction_type")
            amount = valid_money(request.form.get("amount", ""))
            account_id = request.form.get("account_id")
            description = request.form.get("description", "").strip() or None
            to_account_no = request.form.get("to_account_no", "").strip()
            if kind not in ("DEPOSIT", "WITHDRAWAL", "TRANSFER") or amount is None:
                flash("Choose a transaction type and enter an amount greater than zero.", "error")
            else:
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    if customer_id is not None:
                        source = conn.execute(
                            """SELECT account_id, account_no, balance, status FROM accounts
                               WHERE account_id=? AND customer_id=?""",
                            (account_id, customer_id)
                        ).fetchone()
                    else:
                        source = conn.execute(
                            "SELECT account_id, account_no, balance, status FROM accounts WHERE account_id=?",
                            (account_id,)
                        ).fetchone()
                    if not source or source["status"] != "Active":
                        raise ValueError("Select an active account.")
                    balance = Decimal(str(source["balance"]))
                    if kind in ("WITHDRAWAL", "TRANSFER") and balance < amount:
                        raise ValueError("Insufficient balance.")
                    if kind == "DEPOSIT":
                        conn.execute("UPDATE accounts SET balance=balance+? WHERE account_id=?", (str(amount), source["account_id"]))
                        conn.execute("""INSERT INTO transactions(account_id,transaction_type,amount,description,status,created_by)
                                        VALUES(?,'DEPOSIT',?,?,'Success',?)""",
                                     (source["account_id"], str(amount), description, session["user_id"]))
                    elif kind == "WITHDRAWAL":
                        conn.execute("UPDATE accounts SET balance=balance-? WHERE account_id=?", (str(amount), source["account_id"]))
                        conn.execute("""INSERT INTO transactions(account_id,transaction_type,amount,description,status,created_by)
                                        VALUES(?,'WITHDRAWAL',?,?,'Success',?)""",
                                     (source["account_id"], str(amount), description, session["user_id"]))
                    else:
                        if to_account_no == source["account_no"]:
                            raise ValueError("Source and destination accounts must be different.")
                        target = conn.execute("SELECT account_id, account_no, status FROM accounts WHERE account_no=?", (to_account_no,)).fetchone()
                        if not target or target["status"] != "Active":
                            raise ValueError("Destination account was not found or is closed.")
                        conn.execute("UPDATE accounts SET balance=balance-? WHERE account_id=?", (str(amount), source["account_id"]))
                        conn.execute("UPDATE accounts SET balance=balance+? WHERE account_id=?", (str(amount), target["account_id"]))
                        conn.execute("""INSERT INTO transactions(account_id,transaction_type,amount,description,status,created_by)
                                        VALUES(?,'TRANSFER_OUT',?,?,'Success',?)""",
                                     (source["account_id"], str(amount), description or f"Transfer to {to_account_no}", session["user_id"]))
                        conn.execute("""INSERT INTO transactions(account_id,transaction_type,amount,description,status,created_by)
                                        VALUES(?,'TRANSFER_IN',?,?,'Success',?)""",
                                     (target["account_id"], str(amount), f"Transfer from {source['account_no']}", session["user_id"]))
                    conn.commit()
                    flash("Transaction completed successfully.", "success")
                    return redirect(url_for("transactions_list"))
                except ValueError as exc:
                    conn.rollback()
                    flash(str(exc), "error")
                except sqlite3.Error:
                    conn.rollback()
                    flash("Transaction failed. No balance changes were saved.", "error")
    return render_template("transaction_form.html", accounts=accounts)


@app.route("/accounts/search")
@login_required
def account_search():
    if session.get("role") == "Customer" and session.get("customer_id") is None:
        abort(403)
    search = request.args.get("q", "").strip()
    if len(search) < 2:
        return jsonify(accounts=[])
    source_account_id = request.args.get("source_account_id", type=int)
    with get_db() as conn:
        query = """SELECT account_no FROM accounts
                   WHERE status='Active' AND account_no LIKE ?"""
        params = [f"%{search}%"]
        if source_account_id is not None:
            query += " AND account_id<>?"
            params.append(source_account_id)
        rows = conn.execute(
            query + " ORDER BY account_no LIMIT 10",
            params
        ).fetchall()
    return jsonify(accounts=[row["account_no"] for row in rows])


@app.route("/account-types")
@admin_required
def account_types():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM account_types ORDER BY account_type_id").fetchall()
    return render_template("account_types.html", types=rows)


@app.route("/branches", methods=["GET", "POST"])
@admin_required
def branches_list():
    with get_db() as conn:
        if request.method == "POST":
            branch_name = request.form.get("branch_name", "").strip()
            branch_email = request.form.get("branch_email", "").strip() or None
            branch_address = request.form.get("branch_address", "").strip() or None
            status = request.form.get("status", "Active")
            if not branch_name:
                flash("Branch name is required.", "error")
            elif status not in ("Active", "Inactive"):
                flash("Choose a valid branch status.", "error")
            else:
                conn.execute(
                    """INSERT INTO branches(branch_name, branch_email, branch_address, status)
                       VALUES(?, ?, ?, ?)""",
                    (branch_name, branch_email, branch_address, status)
                )
                conn.commit()
                flash("Branch added successfully.", "success")
                return redirect(url_for("branches_list"))
        rows = conn.execute("SELECT * FROM branches ORDER BY branch_id").fetchall()
    return render_template("branches.html", branches=rows)


@app.route("/profile", methods=["GET", "POST"])
@login_required
def customer_profile():
    if session.get("role") != "Customer" or session.get("customer_id") is None:
        abort(403)
    customer_id = session["customer_id"]
    with get_db() as conn:
        customer = conn.execute(
            "SELECT * FROM customers WHERE customer_id=?",
            (customer_id,)
        ).fetchone()
        if customer is None:
            abort(404)
        if request.method == "POST":
            name = request.form.get("full_name", "").strip()
            email = request.form.get("email", "").strip() or None
            phone = request.form.get("phone", "").strip() or None
            address = request.form.get("address", "").strip() or None
            if not name:
                flash("Your name is required.", "error")
            else:
                try:
                    conn.execute(
                        """UPDATE customers SET full_name=?, email=?, phone=?, address=?
                           WHERE customer_id=?""",
                        (name, email, phone, address, customer_id)
                    )
                    conn.commit()
                    flash("Profile updated successfully.", "success")
                    return redirect(url_for("customer_profile"))
                except sqlite3.IntegrityError:
                    flash("Could not update profile. Email or phone may already be in use.", "error")
    return render_template("profile.html", customer=customer)


if __name__ == "__main__":
    app.run(debug=True)
