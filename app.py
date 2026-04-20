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
                <b>{{d['worker_name']}}</b><br>
                📅 {{d['date']}}<br>
                🏷 {{d.get('type','')}}<br>
                ⏰ {{d.get('start_time','')}} - {{d.get('end_time','')}}<br>
                Stato: <span style="color:{{color}}">{{d['status']}}</span><br><br>

                <a href="/approve/{{d['id']}}" style="color:#22c55e">✔ Approva</a> |
                <a href="/reject/{{d['id']}}" style="color:#ef4444">✖ Rifiuta</a>
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

          Data: <input type="date" name="date"><br><br>

          Dalle: <input type="time" name="start_time" id="start"><br><br>

          Alle: <input type="time" name="end_time" id="end"><br><br>

          <button type="submit" style="background:#3b82f6;color:white;padding:6px;border:none;border-radius:6px;">Salva</button>
        </form>

        <script>
        function toggleAddForm(){{
            let type = document.getElementById("type").value;
            let start = document.getElementById("start");
            let end = document.getElementById("end");

            if(type === "ferie"){{
                start.disabled = true;
                end.disabled = true;
                start.value = "";
                end.value = "";
            }} else {{
                start.disabled = false;
                end.disabled = false;
            }}
        }}
        </script>

        <hr>

        <h3>📌 Le tue assenze</h3>
        """

        for d in data:

            selected_ferie = "selected" if d.get("type") == "ferie" else ""
            selected_permesso = "selected" if d.get("type") == "permesso" else ""

            html += f"""
            <div class="card" style="
                background:linear-gradient(135deg,#1e293b,#0f172a);
                padding:12px;
                border-radius:10px;
                margin-bottom:10px;
                color:white;
                box-shadow:0 6px 15px rgba(0,0,0,0.3)
            ">
                <input type="hidden" class="id" value="{d["id"]}">
            
                Tipo:
                <select class="type">
                    <option value="ferie" {selected_ferie}>Ferie</option>
                    <option value="permesso" {selected_permesso}>Permesso</option>
                </select><br>
            
                Data:
                <input type="date" class="date" value="{d["date"]}"><br>
            
                Dalle:
                <input type="time" class="start" value="{d.get("start_time","")}"><br>
            
                Alle:
                <input type="time" class="end" value="{d.get("end_time","")}"><br><br>
            
                <button onclick="update(this)" style="background:#3b82f6;color:white;">Modifica</button>
                <button onclick="remove(this)" style="background:#ef4444;color:white;">Elimina</button>
            </div>
            """

        html += """
<script>

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

    fetch("/delete_absence/"+id)
    .then(()=>location.reload());
}

</script>
"""

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
@app.route("/delete_absence/<id>")
def delete_absence(id):

    requests.delete(
        f"{SUPABASE_URL}/rest/v1/absences?id=eq.{id}",
        headers=HEADERS
    )

    return {"ok": True}


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
