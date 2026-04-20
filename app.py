from flask import Flask, request, session, redirect, render_template_string
import requests
import os
from dotenv import load_dotenv
import bcrypt

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_key")

SUPABASE_URL = "https://dlhayirunoremlpkyxlo.supabase.co"
SUPABASE_KEY = "sb_publishable_DZ69ih5L9IqvJmt44VUK4w_8uelJ5xU"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

LOGIN_HTML = """
<h2>Login Sistema Presenze</h2>
<form method="post">
  Username: <input name="username"><br>
  Password: <input name="password" type="password"><br>
  <button type="submit">Login</button>
</form>
"""

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?username=eq.{username}",
            headers=HEADERS
        )

        user = res.json()

        if user:

            db_user = user[0]

            if bcrypt.checkpw(
                password.encode(),
                db_user["password"].encode()
            ):
                session["user"] = db_user
                return redirect("/dashboard")

        return "Login errato"

    return render_template_string(LOGIN_HTML)

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/")

    user = session["user"]

    html = ""

    # CAPO
    if user["role"] == "manager":

        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/absences?select=*",
            headers=HEADERS
        )

        data = res.json()

        html += f"<h2>Dashboard Capo - {user['username']}</h2>"
        html += "<a href='/logout'>Logout</a><hr>"
        html += "<h3>Richieste da approvare</h3>"

        for d in data:

            color = "orange" if d["status"] == "pending" else "green" if d["status"] == "approved" else "red"

            html += f"""
            <div style="margin-bottom:10px; padding:10px; border:1px solid #ccc;">
                <b>{d['worker_name']}</b> - {d['date']}<br>
                Tipo: {d.get('type','')}<br>
                Orario: {d.get('start_time','')} - {d.get('end_time','')}<br>
                Stato: <span style="color:{color}">{d['status']}</span><br>

                <a href="/approve/{d['id']}">✔ Approva</a> |
                <a href="/reject/{d['id']}">✖ Rifiuta</a>
            </div>
            """

    # LAVORATORE
    else:

        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/absences?worker_name=eq.{user['username']}",
            headers=HEADERS
        )

        data = res.json()

        html += f"<h2>Benvenuto {user['username']}</h2>"
        html += "<a href='/logout'>Logout</a><hr>"

        html += """
        <h3>Inserisci assenza</h3>
        <form method="post" action="/add_absence">

          Tipo:
          <select name="type">
            <option value="ferie">Ferie</option>
            <option value="permesso">Permesso</option>
          </select><br><br>

          Data: <input type="date" name="date"><br><br>

          Dalle: <input type="time" name="start_time"><br><br>

          Alle: <input type="time" name="end_time"><br><br>

          <button type="submit">Salva</button>
        </form>
        <hr>
        """

        html += "<h3>Le tue assenze</h3><ul>"

        for d in data:
            html += f"<li>{d['worker_name']} | {d['date']} | {d.get('type','')} | {d.get('start_time','')} - {d.get('end_time','')}</li>"

        html += "</ul>"

    return html

# ---------------- ADD ----------------
@app.route("/add_absence", methods=["POST"])
def add_absence():

    if "user" not in session:
        return redirect("/")

    user = session["user"]

    data = {
        "worker_name": user["username"],
        "date": request.form["date"],
        "type": request.form["type"],
        "start_time": request.form["start_time"],
        "end_time": request.form["end_time"],
        "status": "pending"
    }

    requests.post(
        f"{SUPABASE_URL}/rest/v1/absences",
        headers=HEADERS,
        json=data
    )

    return redirect("/dashboard")

# ---------------- APPROVE ----------------
@app.route("/approve/<id>")
def approve(id):

    requests.patch(
        f"{SUPABASE_URL}/rest/v1/absences?id=eq.{id}",
        headers=HEADERS,
        json={"status": "approved"}
    )

    return redirect("/dashboard")

# ---------------- REJECT ----------------
@app.route("/reject/<id>")
def reject(id):

    requests.patch(
        f"{SUPABASE_URL}/rest/v1/absences?id=eq.{id}",
        headers=HEADERS,
        json={"status": "rejected"}
    )

    return redirect("/dashboard")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
