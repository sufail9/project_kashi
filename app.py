from flask import Flask, render_template, request, redirect, url_for
from db_config import get_db_connection
from decimal import Decimal, InvalidOperation

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    # Display the registration form
    if request.method == "GET":
        return render_template("register.html")

    # Get information submitted through the form
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    dob = request.form.get("dob") or None
    gender = request.form.get("gender") or None
    mobile = request.form.get("mobile", "").strip()
    email = request.form.get("email", "").strip() or None
    address = request.form.get("address", "").strip() or None
    city = request.form.get("city", "").strip() or None

    # Check required fields
    if not first_name or not last_name or not mobile:
        return "First name, last name, and mobile number are required.", 400

    connection = None
    cursor = None

    try:
        # Connect to MySQL
        connection = get_db_connection()
        cursor = connection.cursor()

        # Insert customer information into MySQL
        sql = """
            INSERT INTO CUSTOMER
            (
                FirstName,
                LastName,
                DateOfBirth,
                Gender,
                Mobile,
                Email,
                Address,
                City,
                RegistrationDate
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURDATE())
        """

        values = (
            first_name,
            last_name,
            dob,
            gender,
            mobile,
            email,
            address,
            city
        )

        cursor.execute(sql, values)
        connection.commit()

        # Display success message
        return """
            <h1>Registration Successful!</h1>
            <p>The customer has been saved to the database.</p>
            <p><a href="/register">Register Another Customer</a></p>
            <p><a href="/">Return to Homepage</a></p>
        """

    except Exception as error:
        if connection is not None:
            connection.rollback()

        print("Customer registration failed:", error)

        return (
            "Registration failed. Please check the VS Code terminal "
            "for the error details."
        ), 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/open_account", methods=["GET", "POST"])
def open_account():
    connection = None
    cursor = None

    if request.method == "POST":
        customer_id = request.form.get("customer_id", "").strip()
        account_type = request.form.get("account_type", "")
        initial_deposit = request.form.get("initial_deposit", "0").strip()

        # Validate the form
        if not customer_id or not account_type:
            return "Customer ID and account type are required.", 400

        try:
            customer_id = int(customer_id)
            initial_deposit = float(initial_deposit)

            if customer_id <= 0 or initial_deposit < 0:
                return "Enter a valid Customer ID and deposit amount.", 400

            if account_type not in ["Saving", "Current", "Salary"]:
                return "Invalid account type.", 400

            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            # Check whether the customer exists
            cursor.execute(
                "SELECT CustomerID FROM customer WHERE CustomerID = %s",
                (customer_id,)
            )
            customer = cursor.fetchone()

            if not customer:
                return "Customer not found. Please register the customer first.", 404

            # Get the existing branch
            cursor.execute(
                "SELECT BranchID FROM branch LIMIT 1"
            )
            branch = cursor.fetchone()

            if not branch:
                return "No bank branch is available.", 400

            # Generate a unique account number
            import secrets
            account_number = "KASHI" + secrets.token_hex(6).upper()

            # Create the account
            cursor.execute(
                """
                INSERT INTO account
                    (AccountNumber, AccountType, OpeningDate,
                     Balance, Status, BranchID)
                VALUES
                    (%s, %s, CURDATE(), %s, 'Active', %s)
                """,
                (
                    account_number,
                    account_type,
                    initial_deposit,
                    branch["BranchID"]
                )
            )

            account_id = cursor.lastrowid

            # Link the account to its customer
            cursor.execute(
                """
                INSERT INTO account_holder
                    (CustomerID, AccountID, HolderSince, HolderType)
                VALUES
                    (%s, %s, CURDATE(), 'Primary')
                """,
                (customer_id, account_id)
            )

            connection.commit()

            return (
                f"Account created successfully! "
                f"Account Number: {account_number}. "
                f"Initial Balance: ₹{initial_deposit:,.2f}"
            )

        except ValueError:
            return "Please enter a valid Customer ID and deposit amount.", 400

        except Exception as error:
            if connection:
                connection.rollback()
            print("Account creation error:", error)
            return "Unable to create the account. Check the VS Code terminal for details.", 500

        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    return render_template("open_account.html")

@app.route("/customers")
def view_customers():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        sql = """
            SELECT
                c.CustomerID,
                c.FirstName,
                c.LastName,
                c.Mobile,
                c.Email,
                a.AccountNumber,
                a.AccountType,
                a.Balance,
                a.Status
            FROM customer c
            LEFT JOIN account_holder ah
                ON c.CustomerID = ah.CustomerID
            LEFT JOIN account a
                ON ah.AccountID = a.AccountID
            ORDER BY c.CustomerID DESC
        """

        cursor.execute(sql)
        customers = cursor.fetchall()

        return render_template(
            "customers.html",
            customers=customers
        )

    except Exception as error:
        print("Error fetching customer details:", error)
        return "Unable to load customer details. Check the VS Code terminal.", 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


@app.route("/deposit", methods=["GET", "POST"])
def deposit_money():
    connection = None
    cursor = None

    if request.method == "POST":
        account_id_text = request.form.get("account_id", "").strip()
        amount_text = request.form.get("amount", "").strip()

        if not account_id_text or not amount_text:
            return "Account ID and deposit amount are required.", 400

        try:
            account_id = int(account_id_text)
            amount = Decimal(amount_text)

            if account_id <= 0:
                return "Enter a valid Account ID.", 400

            if not amount.is_finite() or amount <= 0:
                return "Deposit amount must be greater than ₹0.", 400

            if amount.as_tuple().exponent < -2:
                return "Enter an amount with at most two decimal places.", 400

        except (ValueError, InvalidOperation):
            return "Enter a valid Account ID and deposit amount.", 400

        try:
            connection = get_db_connection()
            connection.start_transaction()

            cursor = connection.cursor(dictionary=True)

            # Find and lock the account
            cursor.execute(
                """
                SELECT AccountID, AccountNumber, Balance, Status
                FROM account
                WHERE AccountID = %s
                FOR UPDATE
                """,
                (account_id,)
            )

            account = cursor.fetchone()

            if not account:
                connection.rollback()
                return "Account ID not found.", 404

            if account["Status"] != "Active":
                connection.rollback()
                return "Deposits are allowed only into active accounts.", 400

            # Update account balance
            cursor.execute(
                """
                UPDATE account
                SET Balance = Balance + %s
                WHERE AccountID = %s
                """,
                (amount, account_id)
            )

            # Record the deposit
            cursor.execute(
                """
                INSERT INTO `transaction`
                    (AccountID, TransactionType, Amount,
                     TransactionDate, Description, TransactionStatus)
                VALUES
                    (%s, 'DEPOSIT', %s, NOW(),
                     'Account deposit', 'SUCCESS')
                """,
                (account_id, amount)
            )

            # Retrieve updated balance
            cursor.execute(
                """
                SELECT Balance
                FROM account
                WHERE AccountID = %s
                """,
                (account_id,)
            )

            updated_account = cursor.fetchone()
            new_balance = updated_account["Balance"]

            connection.commit()

            return f"""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport"
                          content="width=device-width, initial-scale=1.0">
                    <title>Deposit Successful</title>
                    <style>
                        body {{
                            margin: 0;
                            padding: 30px;
                            background: #f3f6fb;
                            font-family: Arial, sans-serif;
                            color: #243247;
                        }}
                        .card {{
                            max-width: 550px;
                            margin: 60px auto;
                            padding: 35px;
                            background: white;
                            border-radius: 14px;
                            text-align: center;
                            box-shadow: 0 5px 22px rgba(20,45,78,.08);
                        }}
                        h1 {{ color: #087f69; }}
                        .amount {{
                            font-size: 27px;
                            font-weight: bold;
                            color: #087f69;
                            margin: 18px 0;
                        }}
                        a {{
                            display: inline-block;
                            margin: 8px;
                            padding: 12px 18px;
                            border-radius: 7px;
                            background: #087f8c;
                            color: white;
                            text-decoration: none;
                        }}
                    </style>
                </head>
                <body>
                    <div class="card">
                        <h1>Deposit Successful!</h1>
                        <p>Your deposit has been recorded.</p>
                        <p>Account ID: <strong>{account_id}</strong></p>
                        <p>Deposited Amount</p>
                        <div class="amount">₹{amount:,.2f}</div>
                        <p>Updated Balance</p>
                        <div class="amount">₹{Decimal(str(new_balance)):,.2f}</div>
                        <a href="/deposit">Make Another Deposit</a>
                        <a href="/">Back to Home</a>
                    </div>
                </body>
                </html>
            """

        except Exception as error:
            if connection:
                connection.rollback()

            print("Deposit failed:", error)

            return "Deposit failed. Check the VS Code terminal for details.", 500

        finally:
            if cursor:
                cursor.close()

            if connection and connection.is_connected():
                connection.close()

    return render_template("deposit.html")

@app.route("/withdraw", methods=["GET", "POST"])
def withdraw_money():
    connection = None
    cursor = None

    if request.method == "POST":
        account_id_text = request.form.get("account_id", "").strip()
        amount_text = request.form.get("amount", "").strip()

        if not account_id_text or not amount_text:
            return "Account ID and withdrawal amount are required.", 400

        try:
            account_id = int(account_id_text)
            amount = Decimal(amount_text)

            if account_id <= 0:
                return "Enter a valid Account ID.", 400

            if not amount.is_finite() or amount <= 0:
                return "Withdrawal amount must be greater than ₹0.", 400

            if amount.as_tuple().exponent < -2:
                return "Enter an amount with at most two decimal places.", 400

        except (ValueError, InvalidOperation):
            return "Enter a valid Account ID and withdrawal amount.", 400

        try:
            connection = get_db_connection()
            connection.start_transaction()

            cursor = connection.cursor(dictionary=True)

            # Find and lock the account during withdrawal
            cursor.execute(
                """
                SELECT AccountID, Balance, Status
                FROM account
                WHERE AccountID = %s
                FOR UPDATE
                """,
                (account_id,)
            )

            account = cursor.fetchone()

            if not account:
                connection.rollback()
                return "Account ID not found.", 404

            if account["Status"] != "Active":
                connection.rollback()
                return "Withdrawals are allowed only from active accounts.", 400

            current_balance = Decimal(str(account["Balance"]))

            # Check whether enough money is available
            if amount > current_balance:
                connection.rollback()
                return (
                    f"Insufficient balance. "
                    f"Available balance: ₹{current_balance:,.2f}"
                ), 400

            # Update the account balance
            cursor.execute(
                """
                UPDATE account
                SET Balance = Balance - %s
                WHERE AccountID = %s
                """,
                (amount, account_id)
            )

            # Record the withdrawal
            cursor.execute(
                """
                INSERT INTO `transaction`
                    (AccountID, TransactionType, Amount,
                     TransactionDate, Description, TransactionStatus)
                VALUES
                    (%s, 'WITHDRAWAL', %s, NOW(),
                     'Cash withdrawal', 'SUCCESS')
                """,
                (account_id, amount)
            )

            # Get the updated balance
            cursor.execute(
                """
                SELECT Balance
                FROM account
                WHERE AccountID = %s
                """,
                (account_id,)
            )

            updated_account = cursor.fetchone()
            new_balance = Decimal(str(updated_account["Balance"]))

            connection.commit()

            return f"""
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport"
                          content="width=device-width, initial-scale=1.0">
                    <title>Withdrawal Successful | Project Kashi</title>
                    <style>
                        body {{
                            margin: 0;
                            padding: 30px;
                            background: #f3f6fb;
                            font-family: Arial, sans-serif;
                            color: #243247;
                        }}
                        .card {{
                            max-width: 550px;
                            margin: 60px auto;
                            padding: 35px;
                            background: white;
                            border-radius: 14px;
                            text-align: center;
                            box-shadow: 0 5px 22px rgba(20,45,78,.08);
                        }}
                        h1 {{ color: #b95d1d; }}
                        .amount {{
                            font-size: 27px;
                            font-weight: bold;
                            color: #b95d1d;
                            margin: 18px 0;
                        }}
                        a {{
                            display: inline-block;
                            margin: 8px;
                            padding: 12px 18px;
                            border-radius: 7px;
                            background: #142d4e;
                            color: white;
                            text-decoration: none;
                        }}
                    </style>
                </head>
                <body>
                    <div class="card">
                        <h1>Withdrawal Successful!</h1>
                        <p>Your withdrawal has been recorded.</p>
                        <p>Account ID: <strong>{account_id}</strong></p>
                        <p>Withdrawn Amount</p>
                        <div class="amount">₹{amount:,.2f}</div>
                        <p>Remaining Balance</p>
                        <div class="amount">₹{new_balance:,.2f}</div>
                        <a href="/withdraw">Withdraw Again</a>
                        <a href="/">Back to Home</a>
                    </div>
                </body>
                </html>
            """

        except Exception as error:
            if connection:
                connection.rollback()

            print("Withdrawal failed:", error)

            return (
                "Withdrawal failed. Check the VS Code terminal for details."
            ), 500

        finally:
            if cursor:
                cursor.close()

            if connection and connection.is_connected():
                connection.close()

    return render_template("withdraw.html")


@app.route("/transaction_history", methods=["GET"])
def transaction_history():
    connection = None
    cursor = None

    account_id = request.args.get("account_id", "").strip()
    transactions = []
    searched = False

    if account_id:
        searched = True

        try:
            account_id = int(account_id)

            if account_id <= 0:
                return "Please enter a valid Account ID.", 400

            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            # Check whether the account exists
            cursor.execute(
                "SELECT AccountID FROM account WHERE AccountID = %s",
                (account_id,)
            )

            account = cursor.fetchone()

            if not account:
                return "Account ID not found. Please check the ID.", 404

            # Retrieve transaction history
            cursor.execute(
                """
                SELECT
                    TransactionID,
                    TransactionType,
                    Amount,
                    TransactionDate,
                    Description,
                    TransactionStatus
                FROM `transaction`
                WHERE AccountID = %s
                ORDER BY TransactionDate DESC, TransactionID DESC
                """,
                (account_id,)
            )

            transactions = cursor.fetchall()

        except ValueError:
            return "Please enter a valid Account ID.", 400

        except Exception as error:
            print("Transaction history error:", error)
            return "Unable to load transaction history. Check the VS Code terminal.", 500

        finally:
            if cursor:
                cursor.close()

            if connection:
                connection.close()

    return render_template(
        "transaction_history.html",
        transactions=transactions,
        account_id=account_id,
        searched=searched
    )

@app.route("/account_details", methods=["GET"])
def account_details():
    connection = None
    cursor = None

    account_id = request.args.get("account_id", "").strip()
    account = None
    searched = False

    if account_id:
        searched = True

        try:
            account_id = int(account_id)

            if account_id <= 0:
                return "Please enter a valid Account ID.", 400

            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT
                    a.AccountID,
                    a.AccountNumber,
                    a.AccountType,
                    a.OpeningDate,
                    a.Balance,
                    a.Status,
                    b.BranchName,
                    b.City
                FROM account AS a
                LEFT JOIN branch AS b
                    ON a.BranchID = b.BranchID
                WHERE a.AccountID = %s
                """,
                (account_id,)
            )

            account = cursor.fetchone()

        except ValueError:
            return "Please enter a valid Account ID.", 400

        except Exception as error:
            print("Account details error:", error)
            return "Unable to load account details. Check the VS Code terminal.", 500

        finally:
            if cursor:
                cursor.close()

            if connection:
                connection.close()

    return render_template(
        "account_details.html",
        account=account,
        account_id=account_id,
        searched=searched
    )

@app.route("/customer_details", methods=["GET"])
def customer_details():
    connection = None
    cursor = None

    customer_id = request.args.get("customer_id", "").strip()
    customer = None
    searched = False

    if customer_id:
        searched = True

        try:
            customer_id = int(customer_id)

            if customer_id <= 0:
                return "Please enter a valid Customer ID.", 400

            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT
                    CustomerID,
                    FirstName,
                    LastName,
                    DateOfBirth,
                    Gender,
                    Mobile,
                    Email,
                    Address,
                    City,
                    RegistrationDate
                FROM customer
                WHERE CustomerID = %s
                """,
                (customer_id,)
            )

            customer = cursor.fetchone()

        except ValueError:
            return "Please enter a valid Customer ID.", 400

        except Exception as error:
            print("Customer details error:", error)
            return "Unable to load customer details. Check the VS Code terminal.", 500

        finally:
            if cursor:
                cursor.close()

            if connection:
                connection.close()

    return render_template(
        "customer_details.html",
        customer=customer,
        customer_id=customer_id,
        searched=searched
    )

@app.route("/dashboard")
def dashboard():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Total registered customers
        cursor.execute("""
            SELECT COUNT(*) AS total_customers
            FROM customer
        """)
        total_customers = cursor.fetchone()["total_customers"]

        # Total bank accounts
        cursor.execute("""
            SELECT COUNT(*) AS total_accounts
            FROM account
        """)
        total_accounts = cursor.fetchone()["total_accounts"]

        # Total money currently held in accounts
        cursor.execute("""
            SELECT COALESCE(SUM(Balance), 0) AS total_balance
            FROM account
            WHERE Status = 'Active'
        """)
        total_balance = cursor.fetchone()["total_balance"]

        # Total successful deposits
        cursor.execute("""
            SELECT COALESCE(SUM(Amount), 0) AS total_deposits
            FROM `transaction`
            WHERE TransactionType = 'DEPOSIT'
              AND TransactionStatus = 'SUCCESS'
        """)
        total_deposits = cursor.fetchone()["total_deposits"]

        # Total successful withdrawals
        cursor.execute("""
            SELECT COALESCE(SUM(Amount), 0) AS total_withdrawals
            FROM `transaction`
            WHERE TransactionType = 'WITHDRAWAL'
              AND TransactionStatus = 'SUCCESS'
        """)
        total_withdrawals = cursor.fetchone()["total_withdrawals"]

        # Total recorded transactions
        cursor.execute("""
            SELECT COUNT(*) AS total_transactions
            FROM `transaction`
        """)
        total_transactions = cursor.fetchone()["total_transactions"]

        return render_template(
            "dashboard.html",
            total_customers=total_customers,
            total_accounts=total_accounts,
            total_balance=total_balance,
            total_deposits=total_deposits,
            total_withdrawals=total_withdrawals,
            total_transactions=total_transactions
        )

    except Exception as error:
        print("Dashboard error:", error)
        return "Unable to load dashboard. Check the VS Code terminal.", 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()

            
if __name__ == "__main__":
    app.run(debug=True)
