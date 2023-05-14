import os

from cs50 import SQL
from flask import Flask, jsonify, url_for, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")
# use phpLiteAdmin to add tables


# Set the secret key to some random bytes. Keep this really secret!
# export API_KEY=pk_b97672c7277a4a0c88879de80dacdef1

# Make sure API key is set
if not os.environ.get("STOCK_API_KEY"):
    raise RuntimeError("STOCK_API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user_id = session["user_id"]

    # Get the user's transaction
    transactions_data = db.execute(
        "SELECT symbol, SUM(shares) AS shares, price FROM transactions WHERE user_id = ? GROUP BY symbol;", user_id)

    # Get the user's remaining cash
    user_cash = db.execute("SELECT cash FROM users WHERE id = ?;", user_id)

    cash = user_cash[0]["cash"]

    # Get sum of all
    sum = 0
    for i in range(len(transactions_data)):

        sum = sum + (transactions_data[i]["shares"]
                     * transactions_data[i]["price"])

    # Adding the cash
    sum += cash

    return render_template("index.html", cash=cash, total=sum, stocks=transactions_data)


@ app.route("/buy", methods=["GET", "POST"])
@ login_required
def buy():
    """Buy shares of stock"""
    # If the form is posted
    if request.method == "POST":

        # Getting the inputs
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        if not shares.isnumeric():
            return apology("must provide a number!")

        shares = int(shares)

        # Lookup the symbol
        stock = lookup(symbol)

        # Checking for wrong inputs
        if not symbol:
            return apology("must provide symbol")
        if not stock:
            return apology("The symbol does not exist")
        if not shares:
            return apology("must provide number of shares")
        if shares < 0:
            return apology("must provide a positive number of shares")
        # if not isinstance(shares, int):
        #    return apology("must provide full shares")

        company_name = stock["name"]
        company_symbol = stock["symbol"]
        price = stock["price"]

        # Get the current user's id
        user_id = session["user_id"]
        # user_id = session.get("user_id")

        # Get the curretn user's remaining cash
        cash = db.execute(
            "SELECT cash FROM users WHERE id = ?;", user_id)
        cash = cash[0]["cash"]

        if price * shares > cash:
            return apology("You have insufficient cash!")

        # Updating user's cash after successful purchase
        updt_cash = cash - price * shares

        db.execute("UPDATE users SET cash = ? WHERE id = ?",
                   updt_cash, user_id)

        # Updating user's trasnactions table
        date = datetime.datetime.now()

        db.execute("INSERT INTO transactions(user_id, symbol, shares, price, date) VALUES(?, ?, ?, ?, ?);",
                   user_id, company_symbol, shares, price, date)
        flash("Your buy order is all set!")

        return redirect("/")

    else:
        return render_template("buy.html")


@ app.route("/addcash", methods=["GET", "POST"])
@ login_required
def addcash():
    """Show history of transactions"""
    user_id = session["user_id"]

    if request.method == "POST":
        new_cash = int(request.form.get("new_cash"))

        if not new_cash:
            return apology("Must Input Amount!")
        if new_cash < 0:
            return apology("Must Input Positive Amount!")
        if not new_cash.isdigt():
            return apology("must provide a number!")

        # Get the current user's cash
        cash = db.execute(
            "SELECT cash FROM users WHERE id = ?;", user_id)
        user_cash = cash[0]["cash"]

        # Updating user's cash
        updt_cash = user_cash + new_cash

        db.execute("UPDATE users SET cash = ? WHERE id = ?",
                   updt_cash, user_id)

        flash("A deposit of " + usd(new_cash) +
              " was receiced in your account!")

        return redirect("/")

    else:
        return render_template("addcash.html")


@ app.route("/history")
@ login_required
def history():
    """Show history of transactions"""
    user_id = session["user_id"]

    transactions = db.execute(
        "SELECT * FROM transactions WHERE user_id = ?;", user_id)

    return render_template("history.html", transactions=transactions)


@ app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?",
                          request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@ app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@ app.route("/quote", methods=["GET", "POST"])
@ login_required
def quote():
    """Get stock quote."""

    if request.method == "POST":
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("must provide symbol")

        stock = lookup(symbol.upper())

        if not stock:
            return apology("The symbol does not exist")

        return render_template("quoted.html", name=stock["name"], price=stock["price"], symbol=stock["symbol"])

    else:
        return render_template("quote.html")


@ app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirmation")

        if not username:
            return apology("must provide username")
        if not password:
            return apology("must provide password")
        if not confirm_password:
            return apology("must confirm password")

        # Instead this line you can later do try inserting into the db then except
        # do the apology. This works because the username column is defined as
        # Unique in the database so it won't work.
        if db.execute("SELECT * FROM users WHERE username = ?", username):
            return apology("Username already exists!")

        if password != confirm_password:
            return apology("Passwords should match!")

        db.execute("INSERT INTO users (username, hash) VALUES(?, ?);",
                   username, generate_password_hash(password))
        flash('You have successfully registered!')

        return redirect(url_for('login'))

    else:
        return render_template("register.html")


@ app.route("/sell", methods=["GET", "POST"])
@ login_required
def sell():
    """Sell shares of stock"""

    if request.method == "POST":
        # Getting the inputs
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")
        if not shares.isnumeric():
            return apology("must provide a number!")

        shares = int(shares)

        # Lookup the symbol
        stock = lookup(symbol)

        # Checking for wrong inputs
        if not symbol:
            return apology("must provide symbol")
        if not stock:
            return apology("The symbol does not exist")
        if not shares:
            return apology("must provide number of shares")

        if shares < 0:
            return apology("must provide a positive number of shares")
        if not isinstance(shares, int):
            return apology("must provide full shares")

        company_name = stock["name"]
        company_symbol = stock["symbol"]
        price = stock["price"]

        # Get the current user's id
        user_id = session["user_id"]
        # user_id = session.get("user_id")

        # Get the curretn user's remaining cash
        cash = db.execute(
            "SELECT cash FROM users WHERE id = ?;", user_id)
        cash = cash[0]["cash"]

        # Check if user has enough shares to sell
        user_shares = db.execute(
            "SELECT shares FROM transactions WHERE user_id = ? AND symbol = ? GROUP BY symbol HAVING SUM(shares) > 0;", user_id, symbol)
        user_shares_real = user_shares[0]["shares"]

        if shares > user_shares_real:
            return apology("You DO NOT Have This Amount of Shares!")
        # Updating user's cash after successful purchase
        updt_cash = cash + price * shares

        db.execute("UPDATE users SET cash = ? WHERE id = ?",
                   updt_cash, user_id)

        # Updating user's trasnactions table
        date = datetime.datetime.now()

        db.execute("INSERT INTO transactions(user_id, symbol, shares, price, date) VALUES(?, ?, ?, ?, ?);",
                   user_id, company_symbol, -1 * shares, price, date)
        flash("Your sell order is all set!")

        return redirect("/")

    else:
        user_id = session["user_id"]
        user_symbols = db.execute(
            "SELECT symbol from transactions WHERE user_id = ?;", user_id)

        return render_template("sell.html", symbols=set([row["symbol"] for row in user_symbols]))
