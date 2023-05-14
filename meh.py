from cs50 import SQL
import datetime

db = SQL("sqlite:///finance.db")

transactions_data = db.execute(
        "SELECT * FROM users;")

date = datetime.datetime.now()
print(type(date))

x = 5

print(type(x))