from flask import Flask, request, session, redirect, render_template_string, jsonify
import requests
import os
from dotenv import load_dotenv
import bcrypt
import secrets
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_key")

SUPABASE_URL = "https://dlhayirunoremlpkyxlo.supabase.co"
SUPABASE_KEY = "sb_publishable_DZ69ih5L9IqvJmt44VUK4w_8uelJ5xU"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

# ---------------- LOGIN HTML ----------------
LOGIN_HTML = """
<h2>Login Sistema Presenze</h2>
<form method="post">
  Username: <input name="username"><br>
  Password: <input name="password" type="password"><br>
  <button type="submit">Login</button>
  <br><br>
  <a href="/register">Registrati</a><br>
  <a href="/forgot">Password smarrita?</a>
</form>
"""

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        sector = request.form.get("sector")

        if not username or not email or not password or not sector:
            return "Tutti i campi sono obbligatori"

        check = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?username=eq.{username}",
            headers=HEADERS
        )

        if check.json():
            return "Username già registrato"

        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        data = {
            "username": username,
            "email": email,
            "password": hashed,
            "role": "worker",
            "sector": sector
        }

        res = requests.post(
            f"{SUPABASE_URL}/rest/v1/users",
            headers=HEADERS,
            json=data
        )

        if res.status_code not in [200, 201]:
            return "Errore registrazione"

        return "<h3>Registrazione completata ✅</h3><a href='/'>Login</a>"

    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/users_available_free?select=username,sector",
        headers=HEADERS
    )

    users = res.json()

    return render_template_string("""
    <h2>Registrazione</h2>

    <form method="post">

        Username:
        <select name="username" id="username" onchange="fillSector()" required>
            <option value="">Seleziona username</option>
            {% for u in users %}
                <option value="{{ u.username }}" data-sector="{{ u.sector }}">
                    {{ u.username }}
                </option>
            {% endfor %}
        </select>

        <input type="hidden" name="sector" id="sector">

        <br><br>

        Email:
        <input name="email" type="email" required><br><br>

        Password:
        <input name="password" type="password" required><br><br>

        <button type="submit">Registrati</button>

    </form>

    <script>
    function fillSector(){
        let s = document.getElementById("username");
        let sector = s.options[s.selectedIndex].dataset.sector;
        document.getElementById("sector").value = sector;
    }
    </script>
    """, users=users)

# ---------------- EMAIL ----------------
def send_email(to, link):
    msg = MIMEText(f"Reset password:\n{link}")
    msg["Subject"] = "Reset Password"
    msg["From"] = "noreply.team104@gmail.com"
    msg["To"] = to

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login("noreply.team104@gmail.com", "turf tlus ngor onwr")
        server.send_message(msg)

# ---------------- FORGOT ----------------
@app.route("/forgot", methods=["GET", "POST"])
def forgot():

    if request.method == "POST":

        email = request.form["email"]

        check = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?email=eq.{email}",
            headers=HEADERS
        )

        if not check.json():
            return "Email non registrata"

        token = secrets.token_urlsafe(32)

        requests.patch(
            f"{SUPABASE_URL}/rest/v1/users?email=eq.{email}",
            headers=HEADERS,
            json={"reset_token": token}
        )

        send_email(email, f"https://attendance-app-9ozz.onrender.com/reset/{token}")

        return "<h3>Email inviata 📩</h3><a href='/'>Login</a>"

    return """
    <h2>Password smarrita</h2>
    <form method="post">
        Email: <input name="email">
        <button>Invia</button>
    </form>
    """

# ---------------- RESET ----------------
@app.route("/reset/<token>", methods=["GET", "POST"])
def reset_password(token):

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    if request.method == "POST":

        hashed = bcrypt.hashpw(
            request.form["password"].encode(),
            bcrypt.gensalt()
        ).decode()

        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?reset_token=eq.{token}",
            headers=headers
        )

        users = res.json()
        if not users:
            return "Token non valido"

        user_id = users[0]["id"]

        requests.patch(
            f"{SUPABASE_URL}/rest/v1/users?id=eq.{user_id}",
            headers=headers,
            json={"password": hashed, "reset_token": None}
        )

        return "<h3>Password aggiornata ✅</h3><a href='/'>Login</a>"

    return """
    <form method="POST">
        Nuova password:
        <input type="password" name="password">
        <button>Reset</button>
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

        user_data = res.json()

        if not user_data:
            return "Utente non trovato"

        user = user_data[0]

        if bcrypt.checkpw(password.encode(), user["password"].encode()):
            session["user"] = user
            return redirect("/dashboard")

        return "Login errato"

    return LOGIN_HTML

# ---------------- API EVENTS (NUOVO) ----------------
@app.route("/api/events")
def api_events():

    if "user" not in session:
        return jsonify([])

    user = session["user"]

    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/absences?select=*",
        headers=HEADERS
    )

    data = res.json()

    events = []

    for d in data:

        end = d["date_to"] or d["date_from"]

        events.append({
            "id": d["id"],
            "title": f"{d['worker_name']} - {d['type']}",
            "start": d["date_from"],
            "end": end,
            "status": d["status"],
            "type": d["type"]
        })

    return jsonify(events)

# ---------------- DASHBOARD (PULITA) ----------------
@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/")

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<link href="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.11/index.global.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.11/index.global.min.js"></script>
</head>

<body style="background:#0f172a;color:white;">

<h2>Dashboard</h2>

<a href="/logout">Logout</a>

<div id="calendar"></div>

<script>

document.addEventListener("DOMContentLoaded", async function () {

    const calendarEl = document.getElementById("calendar");

    const res = await fetch("/api/events");
    const events = await res.json();

    const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: "dayGridMonth",
        locale: "it",
        events: events.map(e => ({
            id: e.id,
            title: e.title,
            start: e.start,
            end: e.end,
            color:
                e.status === "approved" ? "green" :
                e.status === "rejected" ? "red" :
                "orange"
        }))
    });

    calendar.render();
});

</script>

</body>
</html>
""")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
