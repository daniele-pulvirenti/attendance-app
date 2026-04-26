import requests
import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
HEADERS = {
    "apikey": os.getenv("SUPABASE_KEY"),
    "Authorization": f"Bearer {os.getenv('SUPABASE_KEY')}",
    "Content-Type": "application/json"
}

def get(table, query=""):
    return requests.get(f"{SUPABASE_URL}/rest/v1/{table}{query}", headers=HEADERS)

def post(table, data):
    return requests.post(f"{SUPABASE_URL}/rest/v1/{table}", headers=HEADERS, json=data)

def patch(table, query, data):
    return requests.patch(f"{SUPABASE_URL}/rest/v1/{table}?{query}", headers=HEADERS, json=data)

def delete(table, query):
    return requests.delete(f"{SUPABASE_URL}/rest/v1/{table}?{query}", headers=HEADERS)
