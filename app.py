from flask import Flask, request, session, redirect, render_template_string, url_for
import requests
import os
from dotenv import load_dotenv
import bcrypt
import secrets
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
import json

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_key")

# SESSION TIMEOUT
app.permanent_session_lifetime = timedelta(minutes=30)

@app.before_request
def check_session_timeout():
    if request.endpoint in ("login", "static"):
        return

    if "user" in session:
        now = datetime.utcnow()
        last = session.get("last_activity")

        if last:
            elapsed = now - datetime.fromisoformat(last)
            if elapsed.total_seconds() > 1800:
                session.clear()
                return redirect(url_for("login"))

        session["last_activity"] = now.isoformat()


SUPABASE_URL = "https://supabase.com"
SUPABASE_KEY = "sb_publishable_DZ69ih5L9IqvJmt44VUK4w_8uelJ5xU"

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

        user_data = res.json()

        if not user_data:
            return "Utente non trovato"

        db_user = user_data[0]

        if bcrypt.checkpw(password.encode(), db_user["password"].encode()):

            session.permanent = True
            session["user"] = db_user
            session["last_activity"] = datetime.utcnow().isoformat()

            session["view"] = "manager" if db_user.get("role") == "manager" else "worker"

            return redirect("/dashboard")

        return "Password errata"

    return "LOGIN HTML QUI"


# ---------------- SWITCH VIEW ----------------
@app.route("/switch_view/<view>")
def switch_view(view):
    if "user" in session and session["user"].get("role") == "manager":
        session["view"] = view
    return redirect("/dashboard")


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/")

    user = session["user"]
    view = session.get("view", "worker")

    html = ""

    # SWITCH
    if user.get("role") == "manager":
        html += f"""
        <div style="padding:10px;background:#0f172a;color:white;display:flex;gap:10px;">
            <a href="/switch_view/manager"><button style="background:{'#22c55e' if view=='manager' else '#334155'}">Manager</button></a>
            <a href="/switch_view/worker"><button style="background:{'#3b82f6' if view=='worker' else '#334155'}">Worker</button></a>
        </div>
        """

    # ================= MANAGER =================
    if view == "manager" and user["role"] == "manager":

        sector = request.args.get("sector", "all")

        params = {"select": "*"}
        if sector != "all":
            params["sector"] = f"eq.{sector}"

        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/absences",
            headers=HEADERS,
            params=params
        )

        data = res.json()

        events = []

        for d in data:

            if d.get("type") == "ferie":
                end_date = (
                    datetime.strptime(d["date_to"], "%Y-%m-%d") + timedelta(days=1)
                ).strftime("%Y-%m-%d")
            else:
                end_date = d["date_from"]

            events.append({
                "id": d["id"],
                "title": f"{d['worker_name']} - {d['type']}",
                "start": d["date_from"],
                "end": end_date,
                "color": (
                    "#f59e0b" if d["status"] == "pending"
                    else "#22c55e" if d["status"] == "approved"
                    else "#ef4444"
                ),
                "extendedProps": d
            })

        html += f"""
        <h2>Manager Dashboard</h2>

        <a href="/logout">Logout</a>

        <hr>

        <div style="display:flex;gap:10px;">
            <a href="/dashboard?sector=all"><button>Tutti</button></a>
            <a href="/dashboard?sector=Dogane"><button>Dogane</button></a>
            <a href="/dashboard?sector=Accise"><button>Accise</button></a>
            <a href="/dashboard?sector=Unica"><button>Unica</button></a>
        </div>

        <link href="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.11/index.global.min.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.11/index.global.min.js"></script>

        <div id="calendar" style="background:white;padding:10px;border-radius:10px;"></div>

        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            let calendar = new FullCalendar.Calendar(document.getElementById('calendar'), {{
                initialView: 'dayGridMonth',
                locale: 'it',
                firstDay: 1,
                events: {json.dumps(events)},
                eventClick: function(info) {{
                    let e = info.event.extendedProps;
                    alert(e.worker_name + "\\n" + e.type + "\\n" + e.status);
                }}
            }});
            calendar.render();
        }});
        </script>

        <hr>
        """

        for d in data:
            html += f"""
            <div style="background:#0f172a;color:white;padding:10px;margin:10px;border-radius:8px;">
                <b>{d['worker_name']}</b><br>
                {d['type']} - {d['date_from']}<br>
                Stato: {d['status']}<br><br>
                <a href="/approve/{d['id']}">✔ Approva</a> |
                <a href="/reject/{d['id']}">✖ Rifiuta</a>
            </div>
            """

        return render_template_string(html)

    # ================= WORKER =================
    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/absences?worker_name=eq.{user['username']}",
        headers=HEADERS
    )

    data = res.json()

    html += f"""
    <h2>Benvenuto {user['first_name']}</h2>

    <h3>Inserisci assenza</h3>

    <form method="post" action="/add_absence">
        <select name="type">
            <option value="ferie">Ferie</option>
            <option value="permesso">Permesso</option>
        </select>

        <input type="date" name="date">
        <input type="date" name="date_from">
        <input type="date" name="date_to">

        <input type="time" name="start_time">
        <input type="time" name="end_time">

        <button type="submit">Invia</button>
    </form>

    <hr>
    """

    for d in data:
        html += f"""
        <div style="background:#111827;color:white;padding:10px;margin:10px;border-radius:8px;">
            {d['type']} - {d['date_from']}<br>
            Stato: {d['status']}
        </div>
        """

    return render_template_string(html)


# ---------------- ADD ----------------
@app.route("/add_absence", methods=["POST"])
def add_absence():

    if "user" not in session:
        return redirect("/")

    user = session["user"]
    view = session.get("view")

    t = request.form["type"]

    if t == "ferie":
        d_from = request.form["date_from"]
        d_to = request.form["date_to"]
        s_t = None
        e_t = None
    else:
        d_from = d_to = request.form["date"]
        s_t = request.form["start_time"]
        e_t = request.form["end_time"]

    payload = {
        "worker_name": user["username"],
        "sector": user["sector"],
        "date_from": d_from,
        "date_to": d_to,
        "type": t,
        "start_time": s_t,
        "end_time": e_t,
        "status": "approved" if view == "manager" else "pending"
    }

    requests.post(
        f"{SUPABASE_URL}/rest/v1/absences",
        headers=HEADERS,
        json=payload
    )

    return redirect("/dashboard")


# ---------------- APPROVE / REJECT ----------------
@app.route("/approve/<id>")
def approve(id):
    requests.patch(f"{SUPABASE_URL}/rest/v1/absences?id=eq.{id}",
                   headers=HEADERS,
                   json={"status": "approved"})
    return redirect("/dashboard")


@app.route("/reject/<id>")
def reject(id):
    requests.patch(f"{SUPABASE_URL}/rest/v1/absences?id=eq.{id}",
                   headers=HEADERS,
                   json={"status": "rejected"})
    return redirect("/dashboard")


# ---------------- DELETE ----------------
@app.route("/delete/<int:id>")
def delete(id):
    requests.delete(f"{SUPABASE_URL}/rest/v1/absences?id=eq.{id}",
                    headers=HEADERS)
    return redirect("/dashboard")


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
