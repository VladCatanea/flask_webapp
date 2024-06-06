import sqlite3

con = sqlite3.connect('my_database.db')

cur = con.cursor()

# cur.execute("DELETE FROM products")
# cur.execute("DELETE FROM reviews")
# cur.execute("DELETE FROM users")
print(cur.execute("SELECT name FROM sqlite_schema").fetchall())
print(cur.execute("SELECT * FROM users").fetchall())
print(cur.execute("SELECT * FROM products").fetchall())
print(cur.execute("SELECT * FROM reviews").fetchall())

con.commit()
con.close()