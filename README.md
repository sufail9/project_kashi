# Project Kashi — Banking Management System

A college project demonstrating how a web application can connect a Python Flask backend to a MySQL database. It is an educational project and is **not intended to operate as a real banking system**.

## Features
- Customer registration
- Bank account opening
- Deposit money
- Withdraw money
- Transaction history
- Account details
- Customer details
- Dashboard with summary counts and transaction totals

All displayed monetary values should use Indian Rupees (₹).

## Technology Stack
- **Frontend:** HTML templates, CSS and static assets
- **Backend:** Python with Flask
- **Database:** MySQL
- **Database connectivity:** `mysql-connector-python` (or the connector specified in `requirements.txt`)

## Repository Structure
```text
project_kashi/
├── app.py
├── db_config.py
├── requirements.txt
├── test_db.py
├── Database/
├── static/
├── templates/
├── .gitignore
└── README.md
```

## Prerequisites
1. Python 3 installed
2. MySQL Server installed and running
3. MySQL Workbench (recommended for database setup)
4. Git (optional, for version control)

## Setup
### 1. Clone the repository
```bash
git clone https://github.com/sufail9/project_kashi.git
cd project_kashi
```

### 2. Create and activate a virtual environment
Windows PowerShell:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure database credentials securely
Create a local `.env` file in the project root. Do **not** commit this file to GitHub.
```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=project_kashi
```
Use the actual database name and configuration expected by the SQL scripts and `db_config.py`. Never place real passwords in source code or publish them in README files.

### 5. Create the database
Open the SQL files in the `Database/` folder in MySQL Workbench and run them in the order required by their dependencies. If the folder does not contain a complete schema/setup script, create the database and tables using your project SQL script before starting Flask.

### 6. Test the database connection
```bash
python test_db.py
```

### 7. Run the application
```bash
python app.py
```
Open the local URL printed by Flask, commonly `http://127.0.0.1:5000/`.

## Main Database Tables
The current project design includes the following entities; check the actual SQL files for exact column names and constraints:
- `CUSTOMER` — customer personal/contact details
- `BRANCH` — branch details
- `EMPLOYEE` — employee and branch association
- `ACCOUNT` — account type, opening date, balance and status
- `ACCOUNT_HOLDER` — relationship between customers and accounts
- `TRANSACTION` — deposits, withdrawals and transaction status
- `LOAN` — loan details associated with a customer and branch (if enabled)
- `LOAN_PAYMENT` — payments associated with a loan (if enabled)

Note: `TRANSACTION` can be a reserved word in MySQL. If the table is named `transaction`, use backticks around it in SQL queries: `` `transaction` ``.

## Security and Project Scope
- `.env` must remain local and be excluded by `.gitignore`.
- Do not commit passwords, access tokens, or real customer data.
- Use fictional data for demonstrations.
- This is a learning prototype; it is not production banking software and does not implement the controls required for real financial services.

## Academic Project
**Project name:** Project Kashi  
**Purpose:** Demonstrate frontend/backend integration and database persistence using HTML, Flask and MySQL.
