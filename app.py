from flask import Flask, request, session, redirect, render_template_string
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

LOGIN_HTML = """
<h2>Login Sistema Presenze</h2>
<form method="post">
  Username: <input name="username"><br>
  Password: <input name="password" type="password"><br>
  <button type="submit">Login</button>
  <br>
    <a href="/register">Registrati</a><br>
    <a href="/forgot">Password smarrita?</a>
</form>
"""

@app.route("/register", methods=["GET", "POST"])
def register():

    # ================= POST (SALVATAGGIO UTENTE) =================
    if request.method == "POST":

        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        sector = request.form.get("sector")

        # 🔒 controllo base
        if not username or not email or not password or not sector:
            return "Tutti i campi sono obbligatori"

        # 🔎 evita duplicati username
        check = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?username=eq.{username}",
            headers=HEADERS
        )

        if check.json():
            return "Username già registrato"

        # 🔐 hash password
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

        print("REGISTER STATUS:", res.status_code)
        print("REGISTER RESPONSE:", res.text)

        if res.status_code not in [200, 201]:
            return "Errore registrazione"

        return """
        <h3>Registrazione completata ✅</h3>
        <a href="/">Torna al login</a>
        """

    # ================= GET (MOSTRA FORM) =================

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
    function fillSector() {
        let select = document.getElementById("username");
        let sector = select.options[select.selectedIndex].dataset.sector;
        document.getElementById("sector").value = sector;
    }
    </script>
    """, users=users)
def send_email(to, link):

    msg = MIMEText(f"Clicca qui per reimpostare la password:\n{link}")
    msg["Subject"] = "Reset Password"
    msg["From"] = "noreply.team104@gmail.com"
    msg["To"] = to

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login("noreply.team104@gmail.com", "turf tlus ngor onwr")
        server.send_message(msg)

@app.route("/forgot", methods=["GET", "POST"])
def forgot():

    if request.method == "POST":

        email = request.form["email"]

        # 🔎 controllo che email esista
        check = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?email=eq.{email}",
            headers=HEADERS
        )

        user_data = check.json()

        if not user_data:
            return "Email non registrata"

        # 🔐 genera token
        token = secrets.token_urlsafe(32)
        expires = (datetime.utcnow() + timedelta(minutes=15)).isoformat()

        # 💾 salva token su users
        res = requests.patch(
            f"{SUPABASE_URL}/rest/v1/users?email=eq.{email}",
            headers=HEADERS,
            json={
                "reset_token": token
            }
        )

        print("RESET PATCH STATUS:", res.status_code)
        print("RESET PATCH RESPONSE:", res.text)

        # 🔗 link reset
        reset_link = f"https://attendance-app-9ozz.onrender.com/reset/{token}"

        send_email(email, reset_link)

        return """
        <h3>Ti abbiamo inviato una mail 📩</h3>
        <p>Controlla la tua casella e segui il link per reimpostare la password.</p>

        <a href="/" style="
            display:inline-block;
            margin-top:10px;
            padding:8px 12px;
            background:#3b82f6;
            color:white;
            text-decoration:none;
            border-radius:6px;
        ">
            Torna al login
        </a>
        """

    return """
    <h2>Password smarrita</h2>
    <form method="post">
        Inserisci la tua email:<br>
        <input name="email" required>
        <button type="submit">Invia</button>
    </form>
    """
@app.route("/reset/<token>", methods=["GET", "POST"])
def reset_password(token):

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    if request.method == "POST":

        new_password = request.form["password"].encode("utf-8")
        hashed = bcrypt.hashpw(new_password, bcrypt.gensalt()).decode("utf-8")

        # 🔎 1. CERCO UTENTE COL TOKEN
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?reset_token=eq.{token}",
            headers=headers
        )

        print("RESET GET STATUS:", res.status_code)
        print("RESET GET TEXT:", res.text)

        if res.status_code != 200:
            return "Errore server durante verifica token"

        try:
            users = res.json()
        except:
            return "Errore lettura dati token"

        if not users:
            return "Token non valido o scaduto"

        user_id = users[0]["id"]

        # 🔄 2. UPDATE PASSWORD
        update = requests.patch(
            f"{SUPABASE_URL}/rest/v1/users?id=eq.{user_id}",
            headers=headers,
            json={
                "password": hashed,
                "reset_token": None
            }
        )

        print("UPDATE STATUS:", update.status_code)
        print("UPDATE TEXT:", update.text)

        if update.status_code not in [200, 204]:
            return f"Errore aggiornamento password: {update.text}"

        return """
        <h3>Password aggiornata con successo ✅</h3>

        <a href="/" style="
            display:inline-block;
            margin-top:10px;
            padding:8px 12px;
            background:#3b82f6;
            color:white;
            text-decoration:none;
            border-radius:6px;
        ">
            Torna al login
        </a>
        """

    return """
    <form method="POST">
        <h3>Inserisci nuova password</h3>
        <input type="password" name="password" required>
        <button type="submit">Reset Password</button>
    </form>
    """
# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        # 🔥 QUERY CORRETTA: USERS (NON ABSENCES)
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/users?username=eq.{username}",
            headers=HEADERS
        )

        try:
            user_data = res.json()
        except:
            return "Errore server"

        if not user_data:
            return "Utente non trovato"

        db_user = user_data[0]

        if bcrypt.checkpw(password.encode(), db_user["password"].encode()):
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

    # ================= CAPO =================
    if user["role"] == "manager":

        sector = request.args.get("sector")
    
        params = {
            "select": "*"
        }
    
        if sector and sector != "all":
            params["sector"] = f"eq.{sector}"
    
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/absences",
            headers=HEADERS,
            params=params
        )
    
        print("STATUS:", res.status_code)
        print("URL:", res.url)
        print("RESPONSE:", res.text)
    
        try:
            data = res.json()
        except Exception as e:
            print("JSON ERROR:", e)
            data = []
        print("TIPO DATA:", type(data))
        print("DATA RAW:", data)
        for d in data:
            print("SECTOR DB:", d.get("sector"))
        html = f"""
        <h2 style="color:#38bdf8">Dashboard Capo - {user['username']}</h2>
        
        <div style="margin-bottom:15px; display:flex; gap:8px; flex-wrap:wrap;">
            <a href="/dashboard?sector=all"><button>Tutti</button></a>
            <a href="/dashboard?sector=Dogane"><button>Dogane</button></a>
            <a href="/dashboard?sector=Syllabus"><button>Syllabus</button></a>
            <a href="/dashboard?sector=Unica"><button>Unica</button></a>
            <a href="/dashboard?sector=Accise"><button>Accise</button></a>
            <a href="/dashboard?sector=Fabbisogni"><button>Fabbisogni</button></a>
            <a href="/dashboard?sector=Bonus"><button>Bonus</button></a>
        </div>
        
        <a href='/logout'>Logout</a>
        <hr>
        """

        for d in data:

            color = "#f59e0b" if d["status"] == "pending" else "#22c55e" if d["status"] == "approved" else "#ef4444"
        
            # ----- FIX VISUALIZZAZIONE FERIE / PERMESSI -----
            if d.get("type") == "ferie":
                date_display = f'{d.get("date_from")} → {d.get("date_to")}'
                time_display = "09:00 - 18:00"
            else:
                date_display = d.get("date_from")
                time_display = f'{d.get("start_time")} - {d.get("end_time")}'
        
            html += f"""
            <div style="
                background:#0f172a;
                padding:12px;
                border-radius:10px;
                margin-bottom:10px;
                color:white;
                box-shadow:0 4px 12px rgba(0,0,0,0.4)
            ">
                <b>{d["worker_name"]}</b><br>
                📅 {date_display}<br>
                🏷 {d.get("type","")}<br>
                ⏰ {time_display}<br>
                Stato: <span style="color:{color}">{d["status"]}</span><br><br>
        
                <a href="/approve/{d["id"]}" style="color:#22c55e">✔ Approva</a> |
                <a href="/reject/{d["id"]}" style="color:#ef4444">✖ Rifiuta</a>
            </div>
        """
            
        return html

    # ================= LAVORATORE =================
    else:

        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/absences?worker_name=eq.{user['username']}",
            headers=HEADERS
        )
        data = res.json()

        html = f"""
        <h2 style="color:#38bdf8">Benvenuto {user['username']}</h2>
        <a href='/logout'>Logout</a>
        <hr>

        <h3>➕ Inserisci assenza</h3>

        <form method="post" action="/add_absence" style="
            background:#111827;
            padding:15px;
            border-radius:10px;
            color:white;
        ">

          Tipo:
          <select name="type" id="type" onchange="toggleAddForm()">
            <option value="ferie">Ferie</option>
            <option value="permesso">Permesso</option>
          </select><br><br>

          <div id="singleDate">
            Data: <input type="date" name="date"><br><br>
        </div>
        
        <div id="rangeDate" style="display:none;">
            Dal: <input type="date" name="date_from"><br><br>
            Al: <input type="date" name="date_to"><br><br>
        </div>

          Dalle: <input type="time" name="start_time" id="start" min="09:00" max="18:00"><br><br>
          
          Alle: <input type="time" name="end_time" id="end" min="09:00" max="18:00"><br><br>

        <button id="submitBtn" type="submit" disabled
        style="background:#3b82f6;color:white;padding:6px;border:none;border-radius:6px;opacity:0.5;">
        Invia
        </button>
        </form>

        <script>
        function toggleAddForm(){{

            let type = document.getElementById("type").value;
        
            let start = document.getElementById("start");
            let end = document.getElementById("end");
        
            let singleDate = document.getElementById("singleDate");
            let rangeDate = document.getElementById("rangeDate");
        
            if(type === "ferie"){{
                start.disabled = true;
                end.disabled = true;
                start.value = "";
                end.value = "";
        
                singleDate.style.display = "none";
                rangeDate.style.display = "block";
        
            }} else {{
                start.disabled = false;
                end.disabled = false;
        
                singleDate.style.display = "block";
                rangeDate.style.display = "none";
            }}
        
            validateForm();
        }}

        function blockWeekendDates() {{
    document.querySelectorAll("input[type='date']").forEach(input => {{
        input.addEventListener("input", function () {{
            const day = new Date(this.value).getDay();
            if (day === 0 || day === 6) {{
                alert("Weekend non selezionabile");
                this.value = "";
            }}
        }});
    }});
}}

window.addEventListener("DOMContentLoaded", blockWeekendDates);

        function validateForm(){{

            let type = document.getElementById("type").value;
        
            let start = document.getElementById("start").value;
            let end = document.getElementById("end").value;
        
            let submitBtn = document.getElementById("submitBtn");
        
            let valid = true;
        
            if(type === "ferie"){{
                let from = document.querySelector("input[name='date_from']").value;
                let to = document.querySelector("input[name='date_to']").value;
        
                if(!from || !to) valid = false;
        
            }} else {{
                let date = document.querySelector("input[name='date']").value;
        
                if(!date || !start || !end) valid = false;
            }}
        
            submitBtn.disabled = !valid;
            submitBtn.style.opacity = valid ? "1" : "0.5";
        }}

            document.querySelectorAll("input, select").forEach(el => {{
        el.addEventListener("input", validateForm);
    }});
            window.addEventListener("DOMContentLoaded", function () {{
            toggleAddForm();
        }});
        </script>

        <hr>

        <h3>📌 Le tue assenze</h3>
        <h3 style="color:#38bdf8;margin-bottom:10px;">📅 Calendario assenze</h3>

        <div style="
            display:flex;
            justify-content:space-between;
            align-items:center;
            background:#0f172a;
            padding:10px 15px;
            border-radius:12px;
            color:white;
            margin-bottom:15px;
            box-shadow:0 4px 12px rgba(0,0,0,0.3);
        ">
        
            <button onclick="changeMonth(-1)" style="
                background:#1e40af;
                color:white;
                border:none;
                padding:6px 12px;
                border-radius:8px;
                cursor:pointer;
            ">◀</button>
        
            <div id="monthLabel" style="
                font-weight:bold;
                font-size:16px;
                letter-spacing:0.5px;
            "></div>
        
            <button onclick="changeMonth(1)" style="
                background:#1e40af;
                color:white;
                border:none;
                padding:6px 12px;
                border-radius:8px;
                cursor:pointer;
            ">▶</button>
        
        </div>
        <link href="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.11/index.global.min.css" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.11/index.global.min.js"></script>
        <div id="calendar"></div>
        """

        for d in data:

            status = d.get("status", "pending")
            color = "#f59e0b" if status == "pending" else "#22c55e" if status == "approved" else "#ef4444"
        
            html += f"""
            <div class="card" style="
                background:linear-gradient(135deg,#1e293b,#0f172a);
                padding:12px;
                border-radius:10px;
                margin-bottom:10px;
                color:white;
                box-shadow:0 6px 15px rgba(0,0,0,0.3)
            ">
        
                <input type="hidden" class="id" value='{d["id"]}'>
        
                <b>Stato:
                    <span style="color:{color}; font-weight:bold;">
                        {status.upper()}
                    </span>
                </b><br><br>
        
                Tipo:
                <select class="type">
                    <option value="ferie" {"selected" if d.get("type")=="ferie" else ""}>Ferie</option>
                    <option value="permesso" {"selected" if d.get("type")=="permesso" else ""}>Permesso</option>
                </select><br>
        
                Data:<br>
                {f"""
                Dal: <input type='date' class='date_from' value='{d.get("date_from","")}'><br>
                Al: <input type='date' class='date_to' value='{d.get("date_to","")}'><br>
                """ if d.get("type")=="ferie" else f"""
                <input type='date' class='date' value='{d.get("date_from","")}'><br>
                """}
        
                Dalle:
                <input type="time" class="start" value='{d.get("start_time","")}'><br>
        
                Alle:
                <input type="time" class="end" value='{d.get("end_time","")}'><br><br>
        
                <button onclick="update(this)" style="background:#3b82f6;color:white;">Modifica</button>
                <button onclick="remove(this)" style="background:#ef4444;color:white;">Elimina</button>
            </div>
            """

        html += """
<script>


function remove(btn){
    let card = btn.closest(".card");
    let id = card.querySelector(".id").value;

    fetch("/delete/" + id)
        .then(res => res.text())
        .then(() => {
            card.remove(); // sparisce subito senza reload
        });
}


function toggleRow(card){

    let type = card.querySelector(".type").value;
    let start = card.querySelector(".start");
    let end = card.querySelector(".end");

    if(type === "ferie"){
        start.disabled = true;
        end.disabled = true;
        start.value = "";
        end.value = "";
    } else {
        start.disabled = false;
        end.disabled = false;
    }
}

window.addEventListener("DOMContentLoaded", function() {

    document.querySelectorAll(".card").forEach(function(c){
        toggleRow(c);

        c.querySelector(".type").addEventListener("change", function(){
            toggleRow(c);
        });
    });

});

function update(btn){

    let card = btn.closest(".card");
    let type = card.querySelector(".type").value;

    let payload = {
        id: card.querySelector(".id").value,
        type: type,
        start_time: card.querySelector(".start")?.value || null,
        end_time: card.querySelector(".end")?.value || null,
        status: "pending"
    };

    if (type === "ferie") {

        let fromEl = card.querySelector(".date_from");
        let toEl = card.querySelector(".date_to");

        payload.date_from = fromEl ? fromEl.value : null;
        payload.date_to = toEl ? toEl.value : null;

    } else {

        let dateEl = card.querySelector(".date");

        payload.date_from = dateEl ? dateEl.value : null;
        payload.date_to = dateEl ? dateEl.value : null;
    }

    fetch("/update_absence", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(() => location.reload());
}

function remove(btn){
    let id = btn.parentElement.querySelector(".id").value;

    fetch("/delete/" + id)
    .then(() => location.reload());
}

const data = {{ data | tojson }};

let currentDate = new Date();

document.addEventListener("DOMContentLoaded", function () {

    if (!window.FullCalendar) {
        console.error("FullCalendar non caricato");
        return;
    }

    const calendarEl = document.getElementById("calendar");

    const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: "dayGridMonth",
        locale: "it",
        firstDay: 1,
        

        weekends: true,

        dayCellDidMount: function(info) {
            const day = info.date.getDay();
            if (day === 0 || day === 6) {
                info.el.style.backgroundColor = "#0b1220";
                info.el.style.opacity = "0.5";
            }
        },

        events: (typeof data !== "undefined" ? data : []).map(d => {

            if (d.type === "ferie") {
                return {
                    title: "Ferie",
                    start: d.date_from,
                    end: new Date(new Date(d.date_to).getTime() + 86400000).toISOString().split("T")[0],
                    color: d.status === "approved" ? "#22c55e"
                          : d.status === "rejected" ? "#ef4444"
                          : "#f59e0b"
                };
            }

            return {
                title: "Permesso",
                start: d.date_from,
                color: d.status === "approved" ? "#22c55e"
                      : d.status === "rejected" ? "#ef4444"
                      : "#f59e0b"
            };
        })
    });

    calendar.render();
});

</script>
"""
        

        return render_template_string(html, data=data)


# ---------------- ADD ----------------
@app.route("/add_absence", methods=["POST"])
def add_absence():

    if "user" not in session:
        return redirect("/")

    user = session["user"]

    absence_type = request.form["type"]

    # ---------------- FERIE ----------------
    if absence_type == "ferie":

        date_from = request.form["date_from"]
        date_to = request.form["date_to"]

        start_time = None
        end_time = None

    # ---------------- PERMESSO ----------------
    else:

        date_from = request.form["date"]
        date_to = request.form["date"]

        start_time = request.form["start_time"]
        end_time = request.form["end_time"]

    data = {
        "worker_name": user["username"],
        "sector": user["sector"],
        "date_from": date_from,
        "date_to": date_to,
        "type": absence_type,
        "start_time": start_time,
        "end_time": end_time,
        "status": "pending"
    }

    requests.post(
        f"{SUPABASE_URL}/rest/v1/absences",
        headers=HEADERS,
        json=data
    )

    return redirect("/dashboard")

    if "user" not in session:
        return redirect("/")

    user = session["user"]

    data = {
        "worker_name": user["username"],
        "date": request.form["date"],
        "type": request.form["type"],
        "start_time": request.form["start_time"] if request.form["type"] != "ferie" else None,
        "end_time": request.form["end_time"] if request.form["type"] != "ferie" else None,
        "status": "pending"
    }

    requests.post(
        f"{SUPABASE_URL}/rest/v1/absences",
        headers=HEADERS,
        json=data
    )

    return redirect("/dashboard")


# ---------------- UPDATE ----------------
@app.route("/update_absence", methods=["POST"])
def update_absence():

    data = request.json

    payload = {
        "type": data["type"],
        "start_time": data.get("start_time"),
        "end_time": data.get("end_time"),
        "status": "pending"
    }

    # ferie
    if data["type"] == "ferie":
        payload["date_from"] = data.get("date_from")
        payload["date_to"] = data.get("date_to")

    # permesso
    else:
        payload["date_from"] = data.get("date_from")
        payload["date_to"] = data.get("date_to")

    requests.patch(
        f"{SUPABASE_URL}/rest/v1/absences?id=eq.{data['id']}",
        headers=HEADERS,
        json=payload
    )

    return {"ok": True}


# ---------------- DELETE ----------------

@app.route("/delete/<int:id>")
def delete_absence(id):

    print("DELETE CHIAMATA CON ID:", id)

    requests.delete(
        f"{SUPABASE_URL}/rest/v1/absences?id=eq.{id}",
        headers=HEADERS
    )

    return ("ok", 200)

# ---------------- APPROVE ----------------
@app.route("/approve/<id>")
def approve(id):

    r = requests.patch(
        f"{SUPABASE_URL}/rest/v1/absences?id=eq.{id}",
        headers=HEADERS,
        json={"status": "approved"}
    )

    print("APPROVE STATUS:", r.status_code)
    print("APPROVE RESPONSE:", r.text)

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
