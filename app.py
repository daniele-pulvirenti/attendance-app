from flask import Flask, request, session, redirect, render_template, url_for
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, date
import bcrypt
import requests
import json
from services.excel_service import generate_excel

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

    return render_template("login.html", error="...")


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
    view = session.get("view", "worker")

    # ===== PRENDI TUTTE LE REQUEST PENDING =====
    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/absences?status=eq.pending",
        headers=HEADERS
    )

    all_pending = res.json() if res.status_code == 200 else []

    pending_by_sector = {}
    for r in all_pending:
        s = r.get("sector")
        if s:
            pending_by_sector[s] = pending_by_sector.get(s, 0) + 1

    # ================= MANAGER =================
    if view == "manager":

        selected_sector = request.args.get("sector", "all")

        params = {"select": "*"}

        if selected_sector != "all":
            params["sector"] = f"eq.{selected_sector}"

        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/absences",
            headers=HEADERS,
            params=params
        )

        data = res.json() if res.status_code == 200 else []

        # ===== CALENDAR EVENTS =====
        events = []
        for d in data:

            if d.get("type") == "ferie":
                end_date = datetime.strptime(d["date_to"], "%Y-%m-%d") + timedelta(days=1)
                end_date = end_date.strftime("%Y-%m-%d")
            else:
                end_date = d["date_from"]

            events.append({
                "id": d["id"],
                "title": f"{d.get('worker_name')} - {d.get('type')}",
                "start": d["date_from"],
                "end": end_date,
                "color":
                    "#f59e0b" if d["status"] == "pending"
                    else "#22c55e" if d["status"] == "approved"
                    else "#ef4444",
                "extendedProps": d
            })

        events_json = json.dumps(events)

        return render_template(
            "dashboard_manager.html",
            user=user,
            data=data,
            events=events_json,
            pending_by_sector=pending_by_sector,
            selected_sector=selected_sector
        )

    # ================= WORKER =================
    else:

        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/absences?worker_name=eq.{user['username']}",
            headers=HEADERS
        )

        data = res.json() if res.status_code == 200 else []

        return render_template(
            "dashboard_worker.html",
            user=user,
            data=data
        )


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

# ================= APPROVE/REJECT =================
@app.route("/approve/<id>")
def approve(id):

    requests.patch(
        f"{SUPABASE_URL}/rest/v1/absences?id=eq.{id}",
        headers=HEADERS,
        json={"status": "approved"}
    )

    return ("ok", 200)


@app.route("/reject/<id>")
def reject(id):

    requests.patch(
        f"{SUPABASE_URL}/rest/v1/absences?id=eq.{id}",
        headers=HEADERS,
        json={"status": "rejected"}
    )

    return ("ok", 200)

# ================= SWITCH VIEW =================
@app.route("/switch_view/<view>")
def switch_view(view):

    if "user" not in session:
        return redirect("/")

    session["view"] = view
    return redirect("/dashboard")

# ================= EXPORT EXCEL =================
@app.route("/export_excel")
def export_excel():

    if "user" not in session:
        return redirect("/")

    user = session["user"]

    if user.get("role") != "manager":
        return "Non autorizzato", 403

    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    params = {
        "date_from": f"gte.{date_from}",
        "date_to": f"lte.{date_to}",
        "select": "*",
        "order": "sector"
    }

    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/absences",
        headers=HEADERS,
        params=params
    )

    data = res.json() if res.status_code == 200 else []

    # 👇 USA IL SERVICE
    file_stream = generate_excel(data)

    return send_file(
        file_stream,
        as_attachment=True,
        download_name=f"report_{date_from}_{date_to}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ================= SETTINGS =================
@app.route("/settings", methods=["GET", "POST"])
def settings():

    if "user" not in session:
        return redirect("/")

    user = session["user"]
    user_id = user["id"]

    message = ""
    success = False

    if request.method == "POST":

        new_email = request.form.get("email")
        current_password = request.form.get("current_password")
        new_password = request.form.get("password")
        confirm = request.form.get("confirm")

        update_data = {}

        # ===== EMAIL =====
        if new_email:

            check = requests.get(
                f"{SUPABASE_URL}/rest/v1/users?email=eq.{new_email}",
                headers=HEADERS
            ).json()

            if check and check[0]["id"] != user_id:
                return render_template("settings.html", message="Email già usata", success=False)

            update_data["email"] = new_email

        # ===== PASSWORD =====
        if new_password:

            if not current_password:
                return render_template("settings.html", message="Inserisci password attuale", success=False)

            res = requests.get(
                f"{SUPABASE_URL}/rest/v1/users?id=eq.{user_id}",
                headers=HEADERS
            ).json()

            stored_hash = res[0]["password"]

            if not bcrypt.checkpw(current_password.encode(), stored_hash.encode()):
                return render_template("settings.html", message="Password errata", success=False)

            if new_password != confirm:
                return render_template("settings.html", message="Password non uguali", success=False)

            hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
            update_data["password"] = hashed

        # ===== UPDATE =====
        if update_data:

            res = requests.patch(
                f"{SUPABASE_URL}/rest/v1/users?id=eq.{user_id}",
                headers=HEADERS,
                json=update_data
            )

            if res.status_code in [200, 204]:
                message = "✔️ Salvato"
                success = True
            else:
                message = "Errore salvataggio"

    return render_template("settings.html", message=message, success=success)
