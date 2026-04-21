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

    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/absences?worker_name=eq.{user['username']}",
        headers=HEADERS
    )
    data = res.json()

    html = """
    <h2>Dashboard</h2>
    <a href="/logout">Logout</a><hr>

    <h3>Inserisci assenza</h3>

    <form method="post" action="/add_absence">
        Tipo:
        <select id="type" name="type" onchange="toggleForm()">
            <option value="ferie">Ferie</option>
            <option value="permesso">Permesso</option>
        </select><br><br>

        Data: <input type="date" name="date"><br><br>

        Dalle: <input type="time" id="start" name="start_time"><br><br>
        Alle: <input type="time" id="end" name="end_time"><br><br>

        <button type="submit">Invia</button>
    </form>

    <hr>
    <h3>Le tue richieste</h3>

    <div id="list">
    """

    for d in data:

        html += f"""
        <div class="card" style="padding:10px;border:1px solid #ccc;margin:5px;">
            <input type="hidden" class="id" value="{d['id']}">

            <b>{d.get('type')}</b> - {d.get('date','')}<br>
            {d.get('start_time','')} - {d.get('end_time','')}<br>
            Stato: {d.get('status')}<br>

            <button onclick="removeItem(this)">Elimina</button>
        </div>
        """

    html += """
    </div>

    <script>

    function toggleForm(){
        let type = document.getElementById("type").value;
        let start = document.getElementById("start");
        let end = document.getElementById("end");

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

    function removeItem(btn){
        let id = btn.parentElement.querySelector(".id").value;

        fetch("/delete/" + id)
            .then(() => location.reload());
    }

    window.onload = toggleForm;

    </script>
    """

    return render_template_string(html)


# ---------------- ADD ----------------
@app.route("/add_absence", methods=["POST"])
def add_absence():

    user = session["user"]

    data = {
        "worker_name": user["username"],
        "date": request.form["date"],
        "type": request.form["type"],
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


# ---------------- DELETE ----------------
@app.route("/delete/<int:id>")
def delete(id):

    requests.delete(
        f"{SUPABASE_URL}/rest/v1/absences?id=eq.{id}",
        headers=HEADERS
    )

    return ("ok", 200)


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
