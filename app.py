import os
import secrets
import datetime
import psycopg2
from flask import Flask, request, redirect, url_for, render_template, session, jsonify

app = Flask(__name__)

# config
app.secret_key = os.getenv("FLASK_SECRET", "change-me")
DATABASE_URL = os.getenv("DATABASE_URL")  # we'll set this in Render
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "admin123")

def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    con = get_db()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS keys (
            key TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            expires_at TIMESTAMP,
            redeemed_by_discord_id TEXT,
            redeemed_at TIMESTAMP
        );
    """)
    con.commit()
    con.close()

init_db()

def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrap(*args, **kwargs):
        if "logged_in" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrap

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username")
        p = request.form.get("password")
        if u == ADMIN_USER and p == ADMIN_PASS:
            session["logged_in"] = True
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def dashboard():
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT key, status, created_at, expires_at, redeemed_by_discord_id FROM keys ORDER BY created_at DESC LIMIT 50;")
    rows = cur.fetchall()
    con.close()
    keys = []
    for r in rows:
        keys.append({
            "key": r[0],
            "status": r[1],
            "created_at": r[2],
            "expires_at": r[3],
            "redeemed_by_discord_id": r[4],
        })
    return render_template("dashboard.html", keys=keys)

@app.route("/generate", methods=["POST"])
@login_required
def generate():
    valid_for = int(request.form.get("valid_for", 3600))  # seconds
    k = secrets.token_urlsafe(16)
    now = datetime.datetime.utcnow()
    expires_at = now + datetime.timedelta(seconds=valid_for)
    con = get_db()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO keys (key, status, created_at, expires_at) VALUES (%s, %s, %s, %s);",
        (k, "unused", now, expires_at)
    )
    con.commit()
    con.close()
    return redirect(url_for("dashboard"))

# this is for your discord bot to redeem keys
API_SECRET = os.getenv("API_SECRET", "devsecret")

@app.route("/api/redeem", methods=["POST"])
def api_redeem():
    if request.headers.get("X-API-KEY") != API_SECRET:
        return jsonify({"ok": False, "message": "unauthorized"}), 401

    data = request.get_json(force=True)
    key = data.get("key")
    discord_id = data.get("discord_id")

    if not key or not discord_id:
        return jsonify({"ok": False, "message": "missing key or discord_id"}), 400

    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT status, expires_at FROM keys WHERE key=%s;", (key,))
    row = cur.fetchone()
    if not row:
        con.close()
        return jsonify({"ok": False, "message": "key not found"}), 404

    status, expires_at = row

    # expired?
    if expires_at and datetime.datetime.utcnow() > expires_at:
        cur.execute("UPDATE keys SET status='revoked' WHERE key=%s;", (key,))
        con.commit()
        con.close()
        return jsonify({"ok": False, "message": "key expired"}), 400

    if status != "unused":
        con.close()
        return jsonify({"ok": False, "message": f"key is {status}"}), 400

    # mark used
    now = datetime.datetime.utcnow()
    cur.execute(
        "UPDATE keys SET status='used', redeemed_by_discord_id=%s, redeemed_at=%s WHERE key=%s;",
        (discord_id, now, key)
    )
    con.commit()
    con.close()

    return jsonify({"ok": True, "message": "key redeemed"}), 200

if __name__ == "__main__":
    # local run
    app.run(host="0.0.0.0", port=5000, debug=True)
