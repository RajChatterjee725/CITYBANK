# CITYBANK Account Management System (SQLite Edition)

A local browser-based college project using Python Flask, SQLite, HTML, CSS and JavaScript. **No MySQL installation or separate database server is needed.** SQLite stores data in the local `banking.db` file.

## Features
- Login with hashed password and session
- Separate admin/staff management mode and customer self-service demo mode
- Customer-only account, balance and transaction views, plus profile editing
- Filter accounts by customer, type, branch, status, search text, and balance range
- Filter transactions by customer, account, type, status, search text, date range, and amount range
- Filter customers by ID, name/contact/address search, status, account-count range, and creation date
- Dashboard statistics and recent transactions
- Customer CRUD and search
- Admin can delete accounts and customers; deleting either also removes associated transaction history
- Admin branch creation
- Create accounts and activate/close accounts
- Deposit, withdrawal and transfer
- Transaction history, account types and branches
- Sample database records

## Requirements
- Python 3.10 or later
- A modern web browser

## Windows setup
1. Extract the ZIP file.
2. Open Command Prompt in the extracted project folder.
3. Create and activate a virtual environment:

```bat
py -m venv .venv
.venv\Scripts\activate
```

4. Install Flask:

```bat
pip install -r requirements.txt
```

5. Create the SQLite database and sample data:

```bat
python init_schema.py
```

6. Create the demo login:

```bat
python init_db.py
```

7. Start the website:

```bat
python app.py
```

8. Open `http://127.0.0.1:5000` in your browser.

## Demo login
- Username: `admin`
- Password: `admin`

Every customer has a demo login. Its username is the customer's name converted to lowercase with spaces and punctuation removed (for example, `Aarav Sen` becomes `aaravsen`); the password is the same as the username. If a username is already taken, a numeric suffix is added. The login page provides a dropdown of active usernames. Customer logins are created when customers are added and when `init_db.py` is run for existing customers.

Customer mode can view that customer's accounts and transaction history, open additional accounts for itself, update its profile, and make demo deposits, withdrawals, and transfers. Customer routes restrict account and transaction access to the linked customer. Customer-opened accounts receive an automatically generated account number and a zero opening balance. These are classroom demo credentials and are **not real banking authentication**.

To refresh an existing database after updating the project, run `python init_schema.py` and then `python init_db.py`. The schema script creates the customer-login mapping without deleting existing records, and the user script creates/updates the admin and all customer demo logins. The admin login can be overridden with `ADMIN_USERNAME` and `ADMIN_PASSWORD`.

## Demo walkthrough
1. Review the dashboard.
2. Add or edit a customer.
3. Open an account.
4. Make a deposit or withdrawal.
5. Transfer money between two active accounts.
6. Review transaction history and updated balances.

## Database
- `schema.sql`: SQLite schema, constraints, indexes and sample data.
- `init_schema.py`: creates `banking.db` and initializes the tables.
- `init_db.py`: creates/updates the hashed-password admin and demo customer users.
- `banking.db`: generated locally the first time `init_schema.py` runs.

Back up the `banking.db` file to preserve the data. To reset the demo, stop the app, delete `banking.db`, and rerun `python init_schema.py` followed by `python init_db.py`.

## Notes
This is an educational local demo, not production banking software. Do not use real customer data. Debug mode is enabled for local development only. SQLite is ideal for a local single-computer demonstration; a real multi-user banking service would need additional security and operational controls.
