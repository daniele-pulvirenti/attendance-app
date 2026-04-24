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

# Configurazione sessione
app.permanent_session_lifetime = timedelta(minutes=30)

@app.before_request
def check_session_timeout():
    # escludi login e statici
    if request.endpoint in ("login", "static"):
        return
    if "user" in session:
        now = datetime.utcnow()
        last_activity = session.get("last_activity")
        if last_activity:
            elapsed = now - datetime.fromisoformat(last_activity)
            if elapsed.total_seconds() > 1800:
                session.clear()
                return redirect(url_for("login"))
        session["last_activity"] = now.isoformat()

SUPABASE_URL = "https://supabase.co"
SUPABASE_KEY = "sb_publishable_DZ69ih5L9IqvJmt44VUK4w_8uelJ5xU"
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Ferie & Permessi Team104</title>
    <style>
        body { margin: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; height: 100vh; display: flex; justify-content: center; align-items: center; background: url('https://unsplash.com') no-repeat center center/cover; }
        .login-card { backdrop-filter: blur(12px); background: rgba(0, 0, 0, 0.65); padding: 40px; border-radius: 18px; width: 360px; color: white; box-shadow: 0 0 30px rgba(0,0,0,0.6); text-align: center; }
        .login-card h2 { margin-bottom: 10px; font-size: 28px; letter-spacing: 1px; color: #38bdf8; }
        .logo { width: 100px; margin-bottom: 20px; }
        input { width: 100%; padding: 12px; margin-bottom: 18px; border: none; border-radius: 8px; outline: none; font-size: 14px; }
        input[type="text"], input[type="password"] { background: #f1f5f9; }
        button { width: 100%; padding: 12px; border: none; border-radius: 8px; background-color: #38bdf8; color: black; font-weight: bold; cursor: pointer; transition: 0.3s; }
        button:hover { background-color: #0ea5e9; }
        .links { margin-top: 15px; font-size: 14px; color: #94a3b8; }
        .links a { color: #38bdf8; text-decoration: none; }
        .footer { margin-top: 25px; font-size: 12px; color: #94a3b8; }
        .team { color: #38bdf8; font-weight: bold; }
    </style>
</head>
<body>
    <form method="post" class="login-card">
        <img src="/static/images/logo.jpeg" alt="Logo" class="logo">
        <h2>Login Ferie&Permessi</h2>
        Username: <input name="username" required><br>
        Password: <input name="password" type="password" required><br>
        <button type="submit">Login</button>
        <div class="links">
            <a href="/register">Registrati</a> | <a href="/forgot">Password smarrita?</a>
        </div>
        <div class="footer">Powered by <span class="team">Team104</span></div>
    </form>
</body>
</html>
"""

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        sector = request.form.get("sector")
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        if not username or not email or not password or not sector:
            return "Tutti i campi sono obbligatori"
        check = requests.get(f"{SUPABASE_URL}/rest/v1/users?username=eq.{username}", headers=HEADERS)
        if check.json():
            return "Username già registrato"
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        data = {"username": username, "email": email, "password": hashed, "role": "worker", "sector": sector, "first_name": first_name, "last_name": last_name}
        res = requests.post(f"{SUPABASE_URL}/rest/v1/users", headers=HEADERS, json=data)
        if res.status_code not in [200, 201]:
            return "Errore registrazione"
        return "<h3>Registrazione completata ✅ </h3><a href='/'>Torna al login</a>"

    res = requests.get(f"{SUPABASE_URL}/rest/v1/users_available_free?select=username,sector,first_name,last_name", headers=HEADERS)
    users = res.json()
    return render_template_string("""
<!DOCTYPE html>
<html lang="it">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { margin: 0; font-family: Arial; background: url('https://unsplash.com') no-repeat center center/cover; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .card { background: rgba(15, 23, 42, 0.92); padding: 25px; border-radius: 14px; width: 90%; max-width: 420px; color: white; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        input, select { width: 100%; padding: 10px; border-radius: 8px; border: none; margin-bottom: 10px; }
        button { width: 100%; padding: 10px; background: #3b82f6; color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; }
    </style>
</head>
<body>
<div class="card">
    <h2>Registrazione</h2>
    <form method="post">
        <label>Username</label>
        <select name="username" id="username" onchange="fillSector()" required>
            <option value="">Seleziona username</option>
            {% for u in users %}
            <option value="{{ u.username }}" data-sector="{{ u.sector }}" data-first="{{ u.first_name }}" data-last="{{ u.last_name }}"> {{ u.username }} </option>
            {% endfor %}
        </select>
        <input type="hidden" name="sector" id="sector">
        <input type="hidden" name="first_name" id="first_name">
        <input type="hidden" name="last_name" id="last_name">
        <label>Email</label><input name="email" type="email" required>
        <label>Password</label><input name="password" type="password" required>
        <button type="submit">Registrati</button>
    </form>
    <div style="text-align:center; margin-top:12px;"><a href="/" style="color:#38bdf8; text-decoration:none;">← Torna al login</a></div>
</div>
<script>
function fillSector() {
    let select = document.getElementById("username");
    let option = select.options[select.selectedIndex];
    document.getElementById("sector").value = option.dataset.sector || "";
    document.getElementById("first_name").value = option.dataset.first || "";
    document.getElementById("last_name").value = option.dataset.last || "";
}
</script>
</body>
</html>
""", users=users)

def send_email(to, link):
    msg = MIMEText(f"Clicca qui per reimpostare la password:\n{link}")
    msg["Subject"] = "Reset Password"
    msg["From"] = "noreply.team104@gmail.com"
    msg["To"] = to
    with smtplib.SMTP_SSL("://gmail.com", 465) as server:
        server.login("noreply.team104@gmail.com", "turf tlus ngor onwr")
        server.send_message(msg)

@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        email = request.form["email"]
        check = requests.get(f"{SUPABASE_URL}/rest/v1/users?email=eq.{email}", headers=HEADERS)
        if not check.json(): return "Email non registrata"
        token = secrets.token_urlsafe(32)
        requests.patch(f"{SUPABASE_URL}/rest/v1/users?email=eq.{email}", headers=HEADERS, json={"reset_token": token})
        send_email(email, f"https://onrender.com{token}")
        return "<h3>Ti abbiamo inviato una mail 📩 </h3><a href='/'>Torna al login</a>"
    return render_template_string("""
        <body style="background:#0f172a; color:white; font-family:sans-serif; display:flex; justify-content:center; align-items:center; height:100vh;">
            <div style="background:#1e293b; padding:30px; border-radius:15px; text-align:center;">
                <h2>Password smarrita</h2>
                <form method="post"><input name="email" type="email" placeholder="Tua email" style="padding:10px; border-radius:5px;"><br><br><button style="padding:10px 20px; background:#3b82f6; color:white; border:none; border-radius:5px;">Invia link reset</button></form>
                <br><a href="/" style="color:#38bdf8;">Torna al login</a>
            </div>
        </body>
    """)

@app.route("/reset/<token>", methods=["GET", "POST"])
def reset_password(token):
    if request.method == "POST":
        new_password = request.form["password"].encode("utf-8")
        hashed = bcrypt.hashpw(new_password, bcrypt.gensalt()).decode("utf-8")
        res = requests.get(f"{SUPABASE_URL}/rest/v1/users?reset_token=eq.{token}", headers=HEADERS)
        users = res.json()
        if not users: return "Token non valido"
        user_id = users[0]["id"]
        requests.patch(f"{SUPABASE_URL}/rest/v1/users?id=eq.{user_id}", headers=HEADERS, json={"password": hashed, "reset_token": None})
        return "<h3>Password aggiornata! ✅</h3><a href='/'>Login</a>"
    return render_template_string("""
        <body style="background:#0f172a; color:white; font-family:sans-serif; display:flex; justify-content:center; align-items:center; height:100vh;">
            <form method="POST" style="background:#1e293b; padding:30px; border-radius:15px; text-align:center;">
                <h3>Nuova password</h3>
                <input type="password" name="password" required placeholder="Nuova password" style="padding:10px;"><br><br>
                <button type="submit" style="padding:10px; background:#22c55e; color:white; border:none; border-radius:5px;">Reset Password</button>
            </form>
        </body>
    """)

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        # Chiamata a Supabase
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?username=eq.{username}", 
            headers=HEADERS
        )
        
        # Controllo se la risposta è valida
        if res.status_code != 200:
            return f"Errore Database: {res.text}"
            
        try:
            user_list = res.json()
        except Exception:
            return "Errore nella lettura dei dati dal server."

        # Se la lista è vuota, l'utente non esiste
        if not user_list or len(user_list) == 0:
            return "Utente non trovato"

        db_user = user_list[0] # Prendo il primo utente della lista

        # Verifica Password
        if bcrypt.checkpw(password.encode(), db_user["password"].encode()):
            session.permanent = True
            session["user"] = db_user
            session["last_activity"] = datetime.utcnow().isoformat()
            
            # Impostazione vista iniziale
            role = db_user.get("role", "worker")
            session["view"] = "manager" if role == "manager" else "worker"
            
            return redirect("/dashboard")
        
        return "Password errata"
        
    return render_template_string(LOGIN_HTML)


@app.route("/switch_view/<view>")
def switch_view(view):
    if "user" in session and session["user"].get("role") == "manager":
        session["view"] = view
    return redirect("/dashboard")

@app.route("/dashboard")
def dashboard():
    if "user" not in session: return redirect("/")
    
    user = session["user"]
    view = session.get("view", "worker")
    sector_query = request.args.get("sector", "all")
    
    # --- 1. BARRA SWITCH (Sempre visibile per Manager) ---
    html = ""
    if user.get("role") == "manager":
        html += f"""
        <div style="margin-bottom:15px; padding:10px; background:#0f172a; border-radius:8px; display:flex; gap:10px; align-items:center; font-family:sans-serif;">
            <b style="color:white;">Vista:</b>
            <a href="/switch_view/manager" style="text-decoration:none;"><button style="cursor:pointer; padding:6px 12px; background:{'#22c55e' if view=='manager' else '#334155'}; color:white; border:none; border-radius:6px; font-weight:bold;">👔 Manager</button></a>
            <a href="/switch_view/worker" style="text-decoration:none;"><button style="cursor:pointer; padding:6px 12px; background:{'#3b82f6' if view=='worker' else '#334155'}; color:white; border:none; border-radius:6px; font-weight:bold;">👷 Lavoratore</button></a>
        </div>"""

    # --- 2. RECUPERO PENDING GLOBALE (Per i badge notifiche) ---
    res_pending = requests.get(f"{SUPABASE_URL}/rest/v1/absences?status=eq.pending", headers=HEADERS)
    all_pending = res_pending.json()
    pending_by_sector = {}
    for req in all_pending:
        s = req["sector"]
        pending_by_sector[s] = pending_by_sector.get(s, 0) + 1

    # ================= CASE: MANAGER VIEW =================
    if view == "manager" and user["role"] == "manager":
        params = {"select": "*"}
        if sector_query != "all": params["sector"] = f"eq.{sector_query}"
        res = requests.get(f"{SUPABASE_URL}/rest/v1/absences", headers=HEADERS, params=params)
        data = res.json()

        # Preparazione Eventi FullCalendar
        events = []
        for d in data:
            if d.get("type") == "ferie":
                end_date = (datetime.strptime(d["date_to"], "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
            else:
                end_date = d["date_from"]
            events.append({
                "id": d["id"], "title": f"{d['worker_name']} - {d['type'].capitalize()}", "start": d["date_from"], "end": end_date,
                "color": "#f59e0b" if d["status"]=="pending" else "#22c55e" if d["status"]=="approved" else "#ef4444",
                "extendedProps": d
            })

        html += """
        <style>
            body { background:#020617; color:white; font-family:sans-serif; padding:20px; }
            .sector-btn { background:#2d89ef; color:white; padding:8px 14px; border:none; border-radius:6px; font-weight:bold; cursor:pointer; }
            .alert-btn { background:#e74c3c !important; animation:pulse 1.2s infinite; }
            .selected-btn { background:#0ea5e9 !important; border:2px solid white; transform:scale(1.05); }
            @keyframes pulse { 0% { box-shadow:0 0 0 0 rgba(231,76,60,0.7); } 70% { box-shadow:0 0 0 10px rgba(231,76,60,0); } 100% { box-shadow:0 0 0 0 rgba(231,76,60,0); } }
        </style>
        <div style="margin-bottom:15px; display:flex; gap:8px; flex-wrap:wrap;">"""
        for s in ["all", "Dogane", "Syllabus", "Unica", "Accise", "Fabbisogni", "Bonus"]:
            count = pending_by_sector.get(s, 0)
            btn_class = f"sector-btn {'selected-btn' if sector_query==s else ''} {'alert-btn' if count > 0 else ''}"
            badge = f" 🔔 {count}" if count > 0 else ""
            html += f'<a href="/dashboard?sector={s}"><button class="{btn_class}">{s}{badge}</button></a>'
        
        html += f"""</div><a href='/logout' style='color:#cbd5e1;'>Logout</a><hr>
        <link href='https://jsdelivr.net' rel='stylesheet' />
        <script src='https://jsdelivr.net'></script>
        <div id='calendar' style='background:white; color:black; padding:10px; border-radius:10px;'></div>
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                var calendar = new FullCalendar.Calendar(document.getElementById('calendar'), {{
                    initialView: 'dayGridMonth', locale: 'it', firstDay: 1, events: {json.dumps(events)},
                    eventClick: function(info) {{
                        let e = info.event.extendedProps;
                        let h = `<h3>${{e.worker_name}}</h3><p>Tipo: ${{e.type}}</p><p>Stato: ${{e.status}}</p><br>
                        <button onclick="location.href='/approve/${{info.event.id}}'" style="background:#22c55e; color:white; border:none; padding:10px; border-radius:5px; cursor:pointer;">Approv</button>
                        <button onclick="location.href='/reject/${{info.event.id}}'" style="background:#ef4444; color:white; border:none; padding:10px; border-radius:5px; cursor:pointer;">Reject</button>`;
                        document.getElementById('modalBody').innerHTML = h; document.getElementById('eventModal').style.display = 'flex';
                    }}
                }}); calendar.render();
            }});
        </script>
        <div id="eventModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.6); justify-content:center; align-items:center; z-index:9999;">
            <div style="background:white; padding:20px; border-radius:10px; width:350px; color:black; position:relative;">
                <span onclick="document.getElementById('eventModal').style.display='none'" style="position:absolute; top:10px; right:15px; cursor:pointer;">✖</span>
                <div id="modalBody"></div>
            </div>
        </div>
        <h3 style="margin-top:20px;">Lista Richieste (Settore: {sector_query})</h3>"""

        # Lista richieste Manager
        for d in data:
            color = "#f59e0b" if d["status"] == "pending" else "#22c55e" if d["status"] == "approved" else "#ef4444"
            html += f"""<div style="background:#0f172a; padding:12px; border-radius:10px; margin-bottom:10px; border:1px solid #1e293b;">
                <b>{d["worker_name"]}</b> ({d["type"]})<br>📅 {d["date_from"]} {"→ "+d["date_to"] if d.get("date_to") else ""}<br>
                Stato: <span style="color:{color}">{d["status"]}</span><br><br>
                <a href="/approve/{d['id']}" style="color:#22c55e; text-decoration:none;">✔ Approva</a> | <a href="/reject/{d['id']}" style="color:#ef4444; text-decoration:none;">✖ Rifiuta</a>
            </div>"""
        return render_template_string(html)

    # ================= CASE: WORKER VIEW =================
    else:
        res = requests.get(f"{SUPABASE_URL}/rest/v1/absences?worker_name=eq.{user['username']}", headers=HEADERS)
        data = res.json()
        
        html += f"""
        <style>body{{background:#020617; color:white; font-family:sans-serif; padding:20px;}} input, select{{width:100%; padding:8px; border-radius:5px; border:none; margin:5px 0;}}</style>
        <h2 style="color:#38bdf8">Benvenuto {user['first_name']}</h2>
        <a href='/logout' style="color:#cbd5e1;">Logout</a><hr>
        <div style="background:#111827; padding:15px; border-radius:10px; border:1px solid #1e293b;">
            <h3>➕ Inserisci assenza</h3>
            <form method="post" action="/add_absence">
                Tipo: <select name="type" id="type" onchange="toggleForm()">
                    <option value="ferie">Ferie</option><option value="permesso">Permesso</option>
                </select><br>
                <div id="singleDate">Data: <input type="date" name="date" class="d-check"></div>
                <div id="rangeDate" style="display:none;">
                    Dal: <input type="date" name="date_from" class="d-check"> Al: <input type="date" name="date_to" class="d-check">
                </div>
                Dalle: <input type="time" name="start_time" value="09:00"> Alle: <input type="time" name="end_time" value="18:00"><br><br>
                <button type="submit" style="background:#3b82f6; color:white; border:none; padding:10px; width:100%; border-radius:5px; cursor:pointer;">Invia Richiesta</button>
            </form>
        </div>
        <script>
            function toggleForm(){{
                let t = document.getElementById("type").value;
                document.getElementById("singleDate").style.display = (t=="ferie"?"none":"block");
                document.getElementById("rangeDate").style.display = (t=="ferie"?"block":"none");
            }}
            document.querySelectorAll(".d-check").forEach(i => {{
                i.addEventListener("change", function(){{
                    let d = new Date(this.value).getDay();
                    if(d==0 || d==6){{ alert("Weekend non selezionabile"); this.value=""; }}
                }});
            }});
        </script>
        <h3 style="margin-top:20px;">Le tue richieste</h3>"""
        
        for d in data:
            status_color = "#f59e0b" if d["status"] == "pending" else "#22c55e" if d["status"] == "approved" else "#ef4444"
            html += f"""<div style="background:#1e293b; padding:12px; border-radius:10px; margin-bottom:8px; border-left:5px solid {status_color};">
                <b>{d['type'].upper()}</b> - {d['date_from']}<br>Stato: <span style="color:{status_color}">{d['status']}</span>
                <div style="margin-top:8px;"><button onclick="location.href='/delete/{d['id']}'" style="background:#ef4444; color:white; border:none; padding:5px 10px; border-radius:4px; cursor:pointer;">Elimina</button></div>
            </div>"""
        return render_template_string(html)

@app.route("/add_absence", methods=["POST"])
def add_absence():
    if "user" not in session: return redirect("/")
    user = session["user"]
    view = session.get("view")
    a_type = request.form["type"]
    
    if a_type == "ferie":
        d_from, d_to = request.form["date_from"], request.form["date_to"]
        s_t, e_t = None, None
    else:
        d_from = d_to = request.form["date"]
        s_t, e_t = request.form["start_time"], request.form["end_time"]

    payload = {
        "worker_name": user["username"], "sector": user["sector"], "date_from": d_from, "date_to": d_to,
        "type": a_type, "start_time": s_t, "end_time": e_t,
        "status": "approved" if view == "manager" else "pending"
    }
    requests.post(f"{SUPABASE_URL}/rest/v1/absences", headers=HEADERS, json=payload)
    return redirect("/dashboard")

@app.route("/approve/<id>")
def approve(id):
    requests.patch(f"{SUPABASE_URL}/rest/v1/absences?id=eq.{id}", headers=HEADERS, json={"status": "approved"})
    return redirect("/dashboard")

@app.route("/reject/<id>")
def reject(id):
    requests.patch(f"{SUPABASE_URL}/rest/v1/absences?id=eq.{id}", headers=HEADERS, json={"status": "rejected"})
    return redirect("/dashboard")

@app.route("/delete/<int:id>")
def delete_absence(id):
    requests.delete(f"{SUPABASE_URL}/rest/v1/absences?id=eq.{id}", headers=HEADERS)
    return redirect("/dashboard")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
