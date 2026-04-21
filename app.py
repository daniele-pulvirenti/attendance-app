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
                <b>{d['worker_name']}</b><br>
                📅 {d.get('date_from', d.get('date',''))}
                {" → " + d.get('date_to','') if d.get('type') == 'ferie' else ""}<br>
                🏷 {d.get('type','')}<br>
                ⏰ {d.get('start_time','')} - {d.get('end_time','')}<br>
                Stato: <span style="color:{color}">{d['status']}</span><br><br>

                <a href="/approve/{d['id']}" style="color:#22c55e">✔ Approva</a> |
                <a href="/reject/{d['id']}" style="color:#ef4444">✖ Rifiuta</a>
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
        <a href='/logout'>Logout</a><hr>

        <h3>➕ Inserisci assenza</h3>

        <form method="post" action="/add_absence" style="
            background:#111827;
            padding:15px;
            border-radius:10px;
            color:white;
        ">

          Tipo:
          <select name="type" id="type" onchange="toggleForm()">
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

          <button type="submit">Invia</button>
        </form>

        <script>
        function toggleForm(){

            let type = document.getElementById("type").value;
            let start = document.getElementById("start");
            let end = document.getElementById("end");

            if(type === "ferie"){
                document.getElementById("singleDate").style.display = "none";
                document.getElementById("rangeDate").style.display = "block";
                start.disabled = true;
                end.disabled = true;
            } else {
                document.getElementById("singleDate").style.display = "block";
                document.getElementById("rangeDate").style.display = "none";
                start.disabled = false;
                end.disabled = false;
            }
        }

        window.onload = toggleForm;
        </script>

        <hr>

        <h3>📌 Le tue assenze</h3>
        """

        for d in data:

            status = d.get("status", "pending")
            color = "#f59e0b" if status == "pending" else "#22c55e" if status == "approved" else "#ef4444"

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

                <input type="hidden" class="id" value="{d['id']}">

                <b>Stato:
                    <span style="color:{color}">
                        {status.upper()}
                    </span>
                </b><br><br>

                Tipo:
                <select class="type">
                    <option value="ferie" {"selected" if d.get("type")=="ferie" else ""}>Ferie</option>
                    <option value="permesso" {"selected" if d.get("type")=="permesso" else ""}>Permesso</option>
                </select><br>

                Data:
                <b>{date_display}</b><br><br>

                Dalle:
                <input type="time" class="start" value="{d.get('start_time','')}"><br>

                Alle:
                <input type="time" class="end" value="{d.get('end_time','')}"><br><br>

                <button onclick="update(this)">Modifica</button>
                <button onclick="remove(this)">Elimina</button>
            </div>
            """

        html += """
<script>

function remove(btn){
    let card = btn.closest(".card");
    let id = card.querySelector(".id").value;

    fetch("/delete/" + id)
        .then(() => card.remove());
}

function update(btn){

    let card = btn.parentElement;

    fetch("/update_absence", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({
            id: card.querySelector(".id").value,
            type: card.querySelector(".type").value,
            start_time: card.querySelector(".start").value,
            end_time: card.querySelector(".end").value
        })
    }).then(() => location.reload());
}

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

    if absence_type == "ferie":
        data = {
            "worker_name": user["username"],
            "date_from": request.form["date_from"],
            "date_to": request.form["date_to"],
            "type": "ferie",
            "start_time": None,
            "end_time": None,
            "status": "pending"
        }
    else:
        data = {
            "worker_name": user["username"],
            "date": request.form["date"],
            "type": "permesso",
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


# ---------------- UPDATE ----------------
@app.route("/update_absence", methods=["POST"])
def update_absence():

    data = request.json

    payload = {
        "type": data["type"],
        "start_time": data["start_time"],
        "end_time": data["end_time"]
    }

    requests.patch(
        f"{SUPABASE_URL}/rest/v1/absences?id=eq.{data['id']}",
        headers=HEADERS,
        json=payload
    )

    return {"ok": True}


# ---------------- DELETE ----------------
@app.route("/delete/<int:id>")
def delete_absence(id):

    requests.delete(
        f"{SUPABASE_URL}/rest/v1/absences?id=eq.{id}",
        headers=HEADERS
    )

    return ("ok", 200)


# ---------------- AUTH ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
