import os
import pandas as pd
from flask import Blueprint, jsonify, request, current_app, render_template
from app.db import get_conn, BASE

bp = Blueprint("main", __name__)

@bp.route("/")
def home():
    return render_template("index.html")

@bp.route("/analytics")
def analytics():
    return render_template("analytics.html")

@bp.route("/about")
def about():
    return render_template("about.html")

@bp.route("/api/products")
def products():
    q = request.args.get("q", "").strip().lower()
    conn = get_conn()
    rows = conn.execute(
        "SELECT product_id, name FROM products WHERE name LIKE ? ORDER BY popularity DESC",
        (f"%{q}%",)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@bp.route("/api/recommend", methods=["POST"])
def recommend():
    data = request.get_json(silent=True) or {}
    cart = data.get("cart", [])
    n = int(data.get("n", 5))
    return jsonify(current_app.config["RECOMMENDER"].recommend(cart, n))

@bp.route("/api/checkout", methods=["POST"])
def checkout():
    cart = (request.get_json(silent=True) or {}).get("cart", [])
    if not cart:
        return jsonify(error="Cart is empty"), 400
    conn = get_conn()
    tid = conn.execute("INSERT INTO transactions DEFAULT VALUES").lastrowid
    for name in cart:
        row = conn.execute("SELECT product_id FROM products WHERE name = ?",
                           (name.strip().lower(),)).fetchone()
        if row:
            conn.execute("INSERT INTO transaction_items(transaction_id, product_id) VALUES (?, ?)",
                         (tid, row["product_id"]))
    conn.commit()
    conn.close()
    return jsonify(transaction_id=tid, items=len(cart))

@bp.route("/api/rules")
def rules():
    sort = request.args.get("sort", "lift")
    if sort not in ("lift", "confidence", "support"):
        sort = "lift"
    limit = int(request.args.get("limit", 20))
    conn = get_conn()
    rows = conn.execute(f"SELECT antecedents, consequents, support, confidence, lift "
                        f"FROM rules ORDER BY {sort} DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@bp.route("/api/stats")
def stats():
    d = os.path.join(BASE, "data", "processed")
    return jsonify(
        benchmark=pd.read_csv(os.path.join(d, "benchmark.csv")).to_dict("records"),
        evaluation=pd.read_csv(os.path.join(d, "eval_results.csv")).to_dict("records"))