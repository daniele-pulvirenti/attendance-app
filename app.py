from flask import Flask, request, session, redirect, render_template, url_for
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, date
import bcrypt
import requests
import json

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

app.permanent_session_lifetime = timedelta(minutes=30)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}


# ================= SESSION TIMEOUT =================
@app.before_request
def check_session():
    if request.endpoint in ("login", "static"):
        return

    if "user" in session:
        now = datetime.utcnow()
        last = session.get("last_activity")

        if last:
            elapsed = now - datetime.fromisoformat(last)
            if elapsed.total_seconds() > 1800:
                session.clear()
                return redirect("/")

        session["last_activity"] = now.isoformat()


# ================= LOGIN =================
@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?username=eq.{username}",
            headers=HEADERS
        )

        if res.status_code != 200:
            return "Errore server"

        users = res.json()

        if not users:
            return render_template("login.html", error="Utente non trovato")

        user = users[0]

        if bcrypt.checkpw(password.encode(), user["password"].encode()):

            session.permanent = True
            session["user"] = user
            session["view"] = user.get("role", "worker")
            session["last_activity"] = datetime.utcnow().isoformat()

            return redirect("/dashboard")

        return render_template("login.html", error="Password errata")

    return render_template("login.html")


# ================= REGISTER =================
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        sector = request.form.get("sector")

        if not all([username, email, password, sector]):
            return "Campi mancanti"

        check = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?username=eq.{username}",
            headers=HEADERS
        )

        if check.json():
            return "Username già esistente"

        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        requests.post(
            f"{SUPABASE_URL}/rest/v1/users",
            headers=HEADERS,
            json={
                "username": username,
                "email": email,
                "password": hashed,
                "role": "worker",
                "sector": sector
            }
        )

        return redirect("/")

    return render_template("register.html")


# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/")

    user = session["user"]
    view = session.get("view")

    if view == "manager":
        return render_template("dashboard_manager.html", user=user)

    return render_template("dashboard_worker.html", user=user)


# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ================= HEALTH =================
@app.route("/health")
def health():
    return "OK"


if __name__ == "__main__":
    app.run(debug=True)
