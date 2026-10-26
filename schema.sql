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

INSERT OR IGNORE INTO branches(branch_id, branch_name, branch_email, branch_address) VALUES
(1, 'Central Branch', 'central@citybank.local', '12 College Street, Kolkata'),
(2, 'North Branch', 'north@citybank.local', '25 Lake Road, Kolkata');

INSERT OR IGNORE INTO account_types(account_type_id, type_name, minimum_balance, interest_rate, transaction_limit) VALUES
(1, 'Savings', 500.00, 3.50, 100000.00),
(2, 'Current', 1000.00, 0.00, 500000.00),
(3, 'Student', 0.00, 2.50, 25000.00);

INSERT OR IGNORE INTO customers(customer_id, full_name, email, phone, address) VALUES
(1, 'Aarav Sen', 'aarav@example.com', '9000000001', 'Kolkata, West Bengal'),
(2, 'Mira Das', 'mira@example.com', '9000000002', 'Howrah, West Bengal'),
(3, 'Rohan Roy', 'rohan@example.com', '9000000003', 'Salt Lake, West Bengal');

INSERT OR IGNORE INTO accounts(account_id, account_no, customer_id, account_type_id, branch_id, balance) VALUES
(1, 'BA10000001', 1, 1, 1, 12500.00),
(2, 'BA10000002', 2, 2, 1, 42000.00),
(3, 'BA10000003', 3, 3, 2, 3500.00);
