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
    <h2>Dashboard Capo - {user['username']}</h2>

    <div style="margin-bottom:15px; display:flex; gap:8px; flex-wrap:wrap;">
        <button onclick="filterSector('all')">Tutti</button>
        <button onclick="filterSector('Dogane')">Dogane</button>
        <button onclick="filterSector('Syllabus')">Syllabus</button>
        <button onclick="filterSector('Unica')">Unica</button>
        <button onclick="filterSector('Accise')">Accise</button>
        <button onclick="filterSector('Fabbisogni')">Fabbisogni</button>
        <button onclick="filterSector('Bonus')">Bonus</button>
    </div>
    """

    for d in data:

        color = "#f59e0b" if d["status"] == "pending" else "#22c55e" if d["status"] == "approved" else "#ef4444"

        if d.get("type") == "ferie":
            date_display = f'{d.get("date_from","")} → {d.get("date_to","")}'
            time_display = "09:00 - 18:00"
        else:
            date_display = d.get("date_from","")
            time_display = f'{d.get("start_time","")} - {d.get("end_time","")}'

        html += f"""
        <div class="card" data-sector="{d.get('sector','')}" style="
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

    html += """
    <script>
    function filterSector(sector){
        document.querySelectorAll(".card").forEach(card => {
            if(sector === "all"){
                card.style.display = "block";
                return;
            }

            if(card.dataset.sector === sector){
                card.style.display = "block";
            } else {
                card.style.display = "none";
            }
        });
    }
    </script>
    """

    return html

    # ================= LAVORATORE =================
    else:

        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/absences?worker_name=eq.{user['username']}",
            headers=HEADERS
        )

        print("STATUS:", res.status_code)
        print("RESPONSE:", res.text)

        try:
            data = res.json()
        except Exception as e:
            print("🔥 JSON ERROR:", e)
            data = []


            html = f"""
        <h2 style="color:#38bdf8">Benvenuto {user['username']}</h2>
        <a href='/logout'>Logout</a>
        <hr>
        """

        for d in data:

            color = "#f59e0b" if d["status"] == "pending" else "#22c55e" if d["status"] == "approved" else "#ef4444"

            if d.get("type") == "ferie":
                date_display = f'{d.get("date_from","")} → {d.get("date_to","")}'
                time_display = "09:00 - 18:00"
            else:
                date_display = d.get("date_from","")
                time_display = f'{d.get("start_time","")} - {d.get("end_time","")}'

            html += f"""
            <div style="
                background:#0f172a;
                padding:12px;
                border-radius:10px;
                margin-bottom:10px;
                color:white;
            ">
                <b>{d["worker_name"]}</b>
                <span style="opacity:0.6">({d.get("sector","")})</span><br>
                📅 {date_display}<br>
                ⏰ {time_display}<br>
                Stato: <span style="color:{color}">{d["status"]}</span>
            </div>
            """

        html += """
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

          Dalle: <input type="time" name="start_time" id="start"><br><br>
          Alle: <input type="time" name="end_time" id="end"><br><br>

          <button type="submit">Invia</button>
        </form>

        <script>
        function toggleAddForm(){

            let type = document.getElementById("type").value;
            let start = document.getElementById("start");
            let end = document.getElementById("end");

            let singleDate = document.getElementById("singleDate");
            let rangeDate = document.getElementById("rangeDate");

            if(type === "ferie"){
                start.disabled = true;
                end.disabled = true;
                start.value = "";
                end.value = "";

                singleDate.style.display = "none";
                rangeDate.style.display = "block";
            } else {
                start.disabled = false;
                end.disabled = false;

                singleDate.style.display = "block";
                rangeDate.style.display = "none";
            }

            validateForm();
        }

        function blockWeekendDates(){
            document.querySelectorAll("input[type='date']").forEach(input => {
                input.addEventListener("input", function(){
                    const day = new Date(this.value).getDay();
                    if(day === 0 || day === 6){
                        alert("Weekend non selezionabile");
                        this.value = "";
                    }
                });
            });
        }

        function validateForm(){
            let type = document.getElementById("type").value;
            let start = document.getElementById("start").value;
            let end = document.getElementById("end").value;
        }

        window.addEventListener("DOMContentLoaded", function(){
            blockWeekendDates();
            toggleAddForm();
        });
        </script>
        """

        return render_template_string(html, data=data)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
