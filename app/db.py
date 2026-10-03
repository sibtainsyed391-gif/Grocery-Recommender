import os
import sqlite3
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE, "database", "grocery.db")
SCHEMA = os.path.join(BASE, "database", "schema.sql")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def build_db():
    from recommender import Recommender   # works when run as: python app/db.py
    rec = Recommender()
    conn = get_conn()
    conn.executescript(open(SCHEMA).read())
    conn.execute("DELETE FROM products")
    conn.execute("DELETE FROM rules")
    conn.executemany("INSERT INTO products(name, popularity) VALUES (?, ?)",
                     [(n, rec.base_p[n]) for n in rec.products])
    r = pd.read_csv(os.path.join(BASE, "data", "processed", "rules.csv"))
    conn.executemany(
        "INSERT INTO rules(antecedents, consequents, support, confidence, lift) VALUES (?,?,?,?,?)",
        r[["antecedents", "consequents", "support", "confidence", "lift"]].values.tolist())
    conn.commit()
    print("Products:", conn.execute("SELECT COUNT(*) FROM products").fetchone()[0],
          "| Rules:", conn.execute("SELECT COUNT(*) FROM rules").fetchone()[0])
    conn.close()

if __name__ == "__main__":
    build_db()