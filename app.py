from flask import Flask, request, session, redirect, render_template_string
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# 🔐 meglio da env (Render + sicurezza)
app.secret_key = os.getenv("SECRET_KEY", "dev_key")

# ☁️ SUPABASE CORRETTO
SUPABASE_URL = "https://dlhayirunoremlpkyxlo.supabase.co"
SUPABASE_KEY = "sb_publishable_DZ69ih5L9IqvJmt44VUK4w_8uelJ5xU"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# ---------------- LOGIN PAGE ----------------
LOGIN_HTML = """
<h2>Login Sistema Presenze</h2>
<form method="post">
  Username: <input name="username"><br>
  Password: <input name="password" type="password"><br>
  <button type="submit">Login</button>
</form>
"""

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?username=eq.{username}&password=eq.{password}",
            headers=HEADERS
        )

        user = res.json()

        if user:
            session["user"] = user[0]
            return redirect("/dashboard")

        return "Login errato"

    return render_template_string(LOGIN_HTML)

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/")

    user = session["user"]

    if user["role"] == "manager":
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/absences?select=*",
            headers=HEADERS
        )
    else:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/absences?worker_name=eq.{user['username']}",
            headers=HEADERS
        )

    data = res.json()

    html = f"<h2>Benvenuto {user['username']}</h2>"
    html += "<a href='/logout'>Logout</a><hr>"
    html += "<h3>Assenze</h3><ul>"

    for d in data:
        html += f"<li>{d['worker_name']} - {d['date']}</li>"

    html += "</ul>"

    return html

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
