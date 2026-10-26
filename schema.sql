PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'Staff' CHECK(role IN ('Admin','Staff')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS branches (
    branch_id INTEGER PRIMARY KEY AUTOINCREMENT,
    branch_name TEXT NOT NULL,
    branch_email TEXT,
    branch_address TEXT,
    status TEXT NOT NULL DEFAULT 'Active' CHECK(status IN ('Active','Inactive'))
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE,
    phone TEXT UNIQUE,
    address TEXT,
    status TEXT NOT NULL DEFAULT 'Active' CHECK(status IN ('Active','Inactive')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customer_logins (
    user_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS account_types (
    account_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
    type_name TEXT NOT NULL UNIQUE,
    minimum_balance NUMERIC NOT NULL DEFAULT 0 CHECK(minimum_balance >= 0),
    interest_rate NUMERIC NOT NULL DEFAULT 0 CHECK(interest_rate >= 0),
    transaction_limit NUMERIC NOT NULL DEFAULT 100000 CHECK(transaction_limit > 0)
);

CREATE TABLE IF NOT EXISTS employees (
    employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
    branch_id INTEGER NOT NULL,
    full_name TEXT NOT NULL,
    job_title TEXT NOT NULL,
    email TEXT UNIQUE,
    phone TEXT,
    FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_no TEXT NOT NULL UNIQUE,
    customer_id INTEGER NOT NULL,
    account_type_id INTEGER NOT NULL,
    branch_id INTEGER NOT NULL,
    balance NUMERIC NOT NULL DEFAULT 0 CHECK(balance >= 0),
    status TEXT NOT NULL DEFAULT 'Active' CHECK(status IN ('Active','Closed')),
    opened_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (account_type_id) REFERENCES account_types(account_type_id),
    FOREIGN KEY (branch_id) REFERENCES branches(branch_id)
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    transaction_type TEXT NOT NULL CHECK(transaction_type IN ('DEPOSIT','WITHDRAWAL','TRANSFER_OUT','TRANSFER_IN')),
    amount NUMERIC NOT NULL CHECK(amount > 0),
    description TEXT,
    status TEXT NOT NULL DEFAULT 'Success' CHECK(status IN ('Success','Failed')),
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id),
    FOREIGN KEY (created_by) REFERENCES users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_accounts_customer ON accounts(customer_id);
CREATE INDEX IF NOT EXISTS idx_transactions_account_date ON transactions(account_id, created_at);
CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(full_name);

-- Complete seed snapshot copied from banking.db; password hashes are initialized by init_db.py.
-- branches
INSERT OR IGNORE INTO "branches" ("branch_id", "branch_name", "branch_email", "branch_address", "status") VALUES (1, 'Central Branch', 'central@citybank.local', '12 College Street, Kolkata', 'Active');
INSERT OR IGNORE INTO "branches" ("branch_id", "branch_name", "branch_email", "branch_address", "status") VALUES (2, 'North Branch', 'north@citybank.local', '25 Lake Road, Kolkata', 'Active');
-- account_types
INSERT OR IGNORE INTO "account_types" ("account_type_id", "type_name", "minimum_balance", "interest_rate", "transaction_limit") VALUES (1, 'Savings', 500, 3.5, 100000);
INSERT OR IGNORE INTO "account_types" ("account_type_id", "type_name", "minimum_balance", "interest_rate", "transaction_limit") VALUES (2, 'Current', 1000, 0, 500000);
INSERT OR IGNORE INTO "account_types" ("account_type_id", "type_name", "minimum_balance", "interest_rate", "transaction_limit") VALUES (3, 'Student', 0, 2.5, 25000);
-- customers
INSERT OR IGNORE INTO "customers" ("customer_id", "full_name", "email", "phone", "address", "status", "created_at") VALUES (1, 'Aarav Sen', 'aarav@example.com', '9000000001', 'Kolkata, West Bengal', 'Active', '2026-10-26 13:59:48');
INSERT OR IGNORE INTO "customers" ("customer_id", "full_name", "email", "phone", "address", "status", "created_at") VALUES (3, 'Rohan Roy', 'rohan@example.com', '9000000003', 'Salt Lake, West Bengal', 'Active', '2026-10-26 13:59:48');
INSERT OR IGNORE INTO "customers" ("customer_id", "full_name", "email", "phone", "address", "status", "created_at") VALUES (4, 'Rishav Samanta', 'rs@example.com', '123456789', 'Uluberia, West Bengal', 'Active', '2026-10-26 14:48:57');
INSERT OR IGNORE INTO "customers" ("customer_id", "full_name", "email", "phone", "address", "status", "created_at") VALUES (5, 'Pranesh Halder', 'pkh.@example.com', '6767676767', 'West Bengal', 'Active', '2026-10-26 14:52:24');
INSERT OR IGNORE INTO "customers" ("customer_id", "full_name", "email", "phone", "address", "status", "created_at") VALUES (6, 'Soumyajit Maity', 'sm@example.com', '7888926520', 'West Bengal', 'Active', '2026-10-26 14:54:30');
INSERT OR IGNORE INTO "customers" ("customer_id", "full_name", "email", "phone", "address", "status", "created_at") VALUES (7, 'Raj', 'rc@admin.dev', '8734737761', NULL, 'Active', '2026-10-26 15:23:14');
-- users
INSERT OR IGNORE INTO "users" ("user_id", "username", "password_hash", "role", "is_active", "created_at") VALUES (1, 'admin', 'UNINITIALIZED', 'Admin', 1, '2026-10-26 14:00:37');
INSERT OR IGNORE INTO "users" ("user_id", "username", "password_hash", "role", "is_active", "created_at") VALUES (3, 'demo_customer', 'UNINITIALIZED', 'Staff', 0, '2026-10-26 14:10:25');
INSERT OR IGNORE INTO "users" ("user_id", "username", "password_hash", "role", "is_active", "created_at") VALUES (5, 'aaravsen', 'UNINITIALIZED', 'Staff', 1, '2026-10-26 14:20:37');
INSERT OR IGNORE INTO "users" ("user_id", "username", "password_hash", "role", "is_active", "created_at") VALUES (9, 'miradas', 'UNINITIALIZED', 'Staff', 0, '2026-10-26 14:42:42');
INSERT OR IGNORE INTO "users" ("user_id", "username", "password_hash", "role", "is_active", "created_at") VALUES (10, 'rohanroy', 'UNINITIALIZED', 'Staff', 1, '2026-10-26 14:42:42');
INSERT OR IGNORE INTO "users" ("user_id", "username", "password_hash", "role", "is_active", "created_at") VALUES (11, 'rishavsamanta', 'UNINITIALIZED', 'Staff', 1, '2026-10-26 14:48:57');
INSERT OR IGNORE INTO "users" ("user_id", "username", "password_hash", "role", "is_active", "created_at") VALUES (12, 'praneshhalder', 'UNINITIALIZED', 'Staff', 1, '2026-10-26 14:52:24');
INSERT OR IGNORE INTO "users" ("user_id", "username", "password_hash", "role", "is_active", "created_at") VALUES (13, 'soumyajitmaity', 'UNINITIALIZED', 'Staff', 1, '2026-10-26 14:54:30');
INSERT OR IGNORE INTO "users" ("user_id", "username", "password_hash", "role", "is_active", "created_at") VALUES (14, 'raj', 'UNINITIALIZED', 'Staff', 1, '2026-10-26 15:23:15');
-- customer_logins
INSERT OR IGNORE INTO "customer_logins" ("user_id", "customer_id", "created_at") VALUES (5, 1, '2026-10-26 14:10:25');
INSERT OR IGNORE INTO "customer_logins" ("user_id", "customer_id", "created_at") VALUES (10, 3, '2026-10-26 14:42:42');
INSERT OR IGNORE INTO "customer_logins" ("user_id", "customer_id", "created_at") VALUES (11, 4, '2026-10-26 14:48:57');
INSERT OR IGNORE INTO "customer_logins" ("user_id", "customer_id", "created_at") VALUES (12, 5, '2026-10-26 14:52:24');
INSERT OR IGNORE INTO "customer_logins" ("user_id", "customer_id", "created_at") VALUES (13, 6, '2026-10-26 14:54:30');
INSERT OR IGNORE INTO "customer_logins" ("user_id", "customer_id", "created_at") VALUES (14, 7, '2026-10-26 15:23:15');
-- accounts
INSERT OR IGNORE INTO "accounts" ("account_id", "account_no", "customer_id", "account_type_id", "branch_id", "balance", "status", "opened_at") VALUES (1, 'BA10000001', 1, 1, 1, 12500, 'Active', '2026-10-26 13:59:48');
INSERT OR IGNORE INTO "accounts" ("account_id", "account_no", "customer_id", "account_type_id", "branch_id", "balance", "status", "opened_at") VALUES (3, 'BA10000003', 3, 3, 2, 3500, 'Active', '2026-10-26 13:59:48');
INSERT OR IGNORE INTO "accounts" ("account_id", "account_no", "customer_id", "account_type_id", "branch_id", "balance", "status", "opened_at") VALUES (4, 'BA166E45D48C', 1, 1, 1, 0, 'Active', '2026-10-26 14:25:33');
INSERT OR IGNORE INTO "accounts" ("account_id", "account_no", "customer_id", "account_type_id", "branch_id", "balance", "status", "opened_at") VALUES (5, 'BA79B19A2BBC', 4, 3, 1, 11, 'Active', '2026-10-26 14:49:31');
INSERT OR IGNORE INTO "accounts" ("account_id", "account_no", "customer_id", "account_type_id", "branch_id", "balance", "status", "opened_at") VALUES (6, 'BA742DDFF4AE', 5, 3, 2, 20000, 'Active', '2026-10-26 14:55:11');
INSERT OR IGNORE INTO "accounts" ("account_id", "account_no", "customer_id", "account_type_id", "branch_id", "balance", "status", "opened_at") VALUES (7, 'BA10000036', 6, 3, 2, 3600000, 'Active', '2026-10-26 14:56:04');
INSERT OR IGNORE INTO "accounts" ("account_id", "account_no", "customer_id", "account_type_id", "branch_id", "balance", "status", "opened_at") VALUES (8, 'BA10000089', 7, 1, 1, 67.69, 'Active', '2026-10-26 15:27:01');
-- transactions
INSERT OR IGNORE INTO "transactions" ("transaction_id", "account_id", "transaction_type", "amount", "description", "status", "created_by", "created_at") VALUES (1, 5, 'DEPOSIT', 11, NULL, 'Success', 11, '2026-10-26 14:50:17');
INSERT OR IGNORE INTO "transactions" ("transaction_id", "account_id", "transaction_type", "amount", "description", "status", "created_by", "created_at") VALUES (2, 6, 'DEPOSIT', 20000, 'Opening balance', 'Success', 1, '2026-10-26 14:55:11');
INSERT OR IGNORE INTO "transactions" ("transaction_id", "account_id", "transaction_type", "amount", "description", "status", "created_by", "created_at") VALUES (3, 7, 'DEPOSIT', 3600000, 'Opening balance', 'Success', 1, '2026-10-26 14:56:04');
INSERT OR IGNORE INTO "transactions" ("transaction_id", "account_id", "transaction_type", "amount", "description", "status", "created_by", "created_at") VALUES (4, 8, 'DEPOSIT', 67.69, 'Opening balance', 'Success', 1, '2026-10-26 15:27:01');
