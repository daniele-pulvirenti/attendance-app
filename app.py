from flask import Flask, request, jsonify, render_template_string
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# -----------------------
# HOME (semplice UI)
# -----------------------
HTML = """
<h2>Gestione Presenze</h2>

<h3>Lavoratore</h3>
<form action="/add" method="post">
  Nome: <input name="worker_name"><br>
  Data: <input type="date" name="date"><br>
  <button type="submit">Segnala assenza</button>
</form>

<hr>

<h3>Capo - Dashboard</h3>
<a href="/dashboard">Vedi assenze</a>
"""

@app.route("/")
def home():
    return render_template_string(HTML)

# -----------------------
# AGGIUNGI ASSENZA
# -----------------------
@app.route("/add", methods=["POST"])
def add_absence():
    data = {
        "worker_name": request.form["worker_name"],
        "date": request.form["date"]
    }

    res = requests.post(
        f"{SUPABASE_URL}/rest/v1/absences",
        headers=HEADERS,
        json=data
    )

    return "Assenza registrata! <a href='/'>torna</a>"

# -----------------------
# DASHBOARD CAPO
# -----------------------
@app.route("/dashboard")
def dashboard():
    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/absences?select=*",
        headers=HEADERS
    )

    data = res.json()

    html = "<h2>Dashboard Capo</h2>"
    html += "<ul>"

    for d in data:
        html += f"<li>{d['worker_name']} - {d['date']}</li>"

    html += "</ul><a href='/'>home</a>"
    return html


import os

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
