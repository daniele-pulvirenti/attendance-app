from flask import Flask, request, session, redirect, render_template_string
import requests
import os
from dotenv import load_dotenv
import bcrypt

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_key")

SUPABASE_URL = "https://dlhayirunoremlpkyxlo.supabase.co"
SUPABASE_KEY = "INSERISCI_LA_TUA_KEY"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

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
        if not user:
            return "Utente non trovato"

        db_user = user[0]
        if bcrypt.checkpw(password.encode(), db_user["password"].encode()):
            session["user"] = db_user
            return redirect("/dashboard")

        return "Login errato"

    return """
    <h2>Login Sistema Presenze</h2>
    <form method="post">
      Username: <input name="username"><br>
      Password: <input name="password" type="password"><br>
      <button type="submit">Login</button>
    </form>
    """

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")

    user = session["user"]

    # ================= CAPO =================
    if user["role"] == "manager":

        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/absences?select=*",
            headers=HEADERS
        )
        data = res.json()

        html = f"<h2>Dashboard Capo - {user['username']}</h2><a href='/logout'>Logout</a><hr>"

        for d in data:
            color = "#22c55e" if d["status"]=="approved" else "#ef4444" if d["status"]=="rejected" else "#f59e0b"

            if d["type"] == "ferie":
                date_display = f"{d['date_from']} → {d['date_to']}"
                time_display = "09:00 - 18:00"
            else:
                date_display = d["date_from"]
                time_display = f"{d['start_time']} - {d['end_time']}"

            html += f"""
            <div style="background:#0f172a;padding:12px;border-radius:10px;margin-bottom:10px;color:white;">
                <b>{d['worker_name']}</b><br>
                📅 {date_display}<br>
                🏷 {d['type']}<br>
                ⏰ {time_display}<br>
                Stato: <span style="color:{color}">{d['status']}</span><br><br>
                <a href="/approve/{d['id']}">✔ Approva</a> |
                <a href="/reject/{d['id']}">✖ Rifiuta</a>
            </div>
            """

        return html

    # ================= LAVORATORE =================
    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/absences?worker_name=eq.{user['username']}",
        headers=HEADERS
    )
    data = res.json()

    return render_template_string("""
    <h2>Benvenuto {{user.username}}</h2>
    <a href="/logout">Logout</a><hr>

    <form method="post" action="/add_absence">
        Tipo:
        <select name="type" id="type" onchange="toggle()">
            <option value="ferie">Ferie</option>
            <option value="permesso">Permesso</option>
        </select><br><br>

        <div id="range">
            Dal: <input type="date" name="date_from"><br>
            Al: <input type="date" name="date_to"><br>
        </div>

        <div id="single" style="display:none;">
            Data: <input type="date" name="date"><br>
            Dalle: <input type="time" name="start_time"><br>
            Alle: <input type="time" name="end_time"><br>
        </div>

        <button type="submit">Invia</button>
    </form>

    <hr><h3>Le tue assenze</h3>

    {% for d in data %}
        <div style="background:#1e293b;color:white;padding:10px;margin:8px;border-radius:8px;">
            {{d.type}} |
            {{d.date_from}} → {{d.date_to}} |
            {{d.status}}
        </div>
    {% endfor %}

    <script>
    function toggle(){
        let t = document.getElementById("type").value;
        document.getElementById("range").style.display = (t=="ferie")?"block":"none";
        document.getElementById("single").style.display = (t=="permesso")?"block":"none";
    }
    toggle();
    </script>
    """, data=data, user=user)

# ---------------- ADD ----------------
@app.route("/add_absence", methods=["POST"])
def add_absence():
    user = session["user"]
    t = request.form["type"]

    if t == "ferie":
        date_from = request.form["date_from"]
        date_to = request.form["date_to"]
        start_time = None
        end_time = None
    else:
        date_from = request.form["date"]
        date_to = request.form["date"]
        start_time = request.form["start_time"]
        end_time = request.form["end_time"]

    requests.post(
        f"{SUPABASE_URL}/rest/v1/absences",
        headers=HEADERS,
        json={
            "worker_name": user["username"],
            "type": t,
            "date_from": date_from,
            "date_to": date_to,
            "start_time": start_time,
            "end_time": end_time,
            "status": "pending"
        }
    )
    return redirect("/dashboard")

# ---------------- APPROVE / REJECT ----------------
@app.route("/approve/<id>")
def approve(id):
    requests.patch(
        f"{SUPABASE_URL}/rest/v1/absences?id=eq.{id}",
        headers=HEADERS,
        json={"status":"approved"}
    )
    return redirect("/dashboard")

@app.route("/reject/<id>")
def reject(id):
    requests.patch(
        f"{SUPABASE_URL}/rest/v1/absences?id=eq.{id}",
        headers=HEADERS,
        json={"status":"rejected"}
    )
    return redirect("/dashboard")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
