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
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
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

        try:
            user = res.json()
        except:
            return "Errore server"

        if not user:
            return "Utente non trovato"

        db_user = user[0]

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

        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/absences?select=*",
            headers=HEADERS
        )
        data = res.json()

        html = f"""
        <h2 style="color:#38bdf8">Dashboard Capo - {user['username']}</h2>
        <a href='/logout'>Logout</a><hr>
        """

        for d in data:

            color = "#f59e0b" if d["status"] == "pending" else "#22c55e" if d["status"] == "approved" else "#ef4444"

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
                📅 {d["date"]}<br>
                🏷 {d.get("type","")}<br>
                ⏰ {d.get("start_time","")} - {d.get("end_time","")}<br>
                Stato: <span style="color:{color}">{d["status"]}</span><br><br>
            
                <a href="/approve/{d["id"]}" style="color:#22c55e">✔ Approva</a> |
                <a href="/reject/{d["id"]}" style="color:#ef4444">✖ Rifiuta</a>
            </div>
"""
            html += """
            <script>
            setInterval(() => {
                location.reload();
            }, 5000);
            </script>
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
            document.getElementById("type").addEventListener("change", toggleAddForm);
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

            window.onload = function(){
            toggleAddForm();
            validateForm();
        }
                
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
        
        <div id="calendar"></div>
        """

        for d in data:

    status = d.get("status", "pending")
    color = "#f59e0b" if status == "pending" else "#22c55e" if status == "approved" else "#ef4444"

    # ---------------- DATA DISPLAY CORRETTA ----------------
    if d.get("type") == "ferie":
        date_display = f"{d.get('date_from','')} → {d.get('date_to','')}"
    else:
        date_display = d.get("date","")

    html += f"""
    <div class="card" style="
        background:linear-gradient(135deg,#1e293b,#0f172a);
        padding:12px;
        border-radius:10px;
        margin-bottom:10px;
        color:white;
        box-shadow:0 6px 15px rgba(0,0,0,0.3)
    ">

        <input type="hidden" class="id" value='{{d["id"]}}'>

        <b>Stato:
            <span style="color:{{color}}; font-weight:bold;">
                {{status.upper()}}
            </span>
        </b><br><br>

        Tipo:
        <select class="type">
            <option value="ferie" {{"selected" if d.get("type")=="ferie" else ""}}>Ferie</option>
            <option value="permesso" {{"selected" if d.get("type")=="permesso" else ""}}>Permesso</option>
        </select><br>

        Data:
        <b>{{date_display}}</b><br><br>

        Dalle:
        <input type="time" class="start" value='{{d.get("start_time","")}}'><br>

        Alle:
        <input type="time" class="end" value='{{d.get("end_time","")}}'><br><br>

        <button onclick="update(this)" style="background:#3b82f6;color:white;">Modifica</button>
        <button onclick="remove(this)" style="background:#ef4444;color:white;">Elimina</button>
    </div>
    """
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

    let card = btn.parentElement;

    fetch("/update_absence", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({
            id: card.querySelector(".id").value,
            type: card.querySelector(".type").value,
            date: card.querySelector(".date").value,
            start_time: card.querySelector(".start").value,
            end_time: card.querySelector(".end").value
        })
    }).then(()=>location.reload());
}

function remove(btn){
    let id = btn.parentElement.querySelector(".id").value;

    fetch("/delete/" + id)
    .then(() => location.reload());
}

const data = {{ data | tojson }};

let currentDate = new Date();

function renderCalendar(){

    const calendar = document.getElementById("calendar");
    const monthLabel = document.getElementById("monthLabel");

    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();

    const monthNames = [
        "Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno",
        "Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"
    ];

    monthLabel.innerHTML = `
        <span style="color:#38bdf8">${monthNames[month]}</span>
        <span style="opacity:0.7">${year}</span>
    `;

    const daysInMonth = new Date(year, month + 1, 0).getDate();

    let html = '<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:5px;">';

    for(let i=1;i<=daysInMonth;i++){

        let dateStr = `${year}-${String(month+1).padStart(2,'0')}-${String(i).padStart(2,'0')}`;

        let entry = data.find(d => d.date === dateStr);

        let bg = "#1e293b";

        if(entry){
            if(entry.status === "approved") bg = "#22c55e";
            else if(entry.status === "rejected") bg = "#ef4444";
            else bg = "#f59e0b";
        }

            html += "<div style='"
        + "background:" + bg + ";"
        + "color:white;"
        + "padding:8px;"
        + "border-radius:6px;"
        + "text-align:center;"
        + "font-size:12px;"
        + "'>"
        + i +
    "</div>";
    }

    html += '</div>';

    calendar.innerHTML = html;
}

function changeMonth(step){
    currentDate.setMonth(currentDate.getMonth() + step);
    renderCalendar();
}

renderCalendar();

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
        "date": data["date"],
        "start_time": data["start_time"],
        "end_time": data["end_time"]
    }

    if data["type"] == "ferie":
        payload["start_time"] = None
        payload["end_time"] = None

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
