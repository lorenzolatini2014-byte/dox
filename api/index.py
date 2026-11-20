from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta, datetime
import requests
import json
import os
import time

template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
app = Flask(__name__, template_folder=template_dir)

app.secret_key = os.environ.get('SECRET_KEY', 'chiave-segreta-hacker-rosso-999')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=10)
app.config['SESSION_REFRESH_EACH_REQUEST'] = True

KV_URL = os.environ.get('KV_REST_API_URL')
KV_TOKEN = os.environ.get('KV_REST_API_TOKEN')

# Memoria temporanea solo in locale se non hai ancora collegato il DB
local_users = {}
local_chat = []


def db_cmd(*args):
    if not KV_URL or not KV_TOKEN:
        return None
    headers = {"Authorization": f"Bearer {KV_TOKEN}"}
    res = requests.post(KV_URL, headers=headers, json=list(args), timeout=10)
    if res.status_code == 200:
        return res.json().get('result')
    return None


@app.before_request
def make_session_permanent():
    session.permanent = True


@app.route('/', methods=['GET'])
def home():
    txt_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'text.txt'))
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            contenuto_txt = f.read()
    except FileNotFoundError:
        contenuto_txt = "ERRORE: File text.txt non trovato."

    ora = time.time()
    un_anno_fa = ora - (365 * 24 * 60 * 60)
    messaggi_validi = []

    if KV_URL and KV_TOKEN:
        db_cmd("ZREMRANGEBYSCORE", "hacker_chat", "-inf", un_anno_fa)
        raw_msgs = db_cmd("ZRANGE", "hacker_chat", 0, -1) or []
        for item in raw_msgs:
            try:
                messaggi_validi.append(json.loads(item))
            except Exception:
                pass
    else:
        local_chat[:] = [m for m in local_chat if m['timestamp'] > un_anno_fa]
        messaggi_validi = list(local_chat)

    errore = request.args.get('errore', '')
    return render_template(
        'index.html',
        testo=contenuto_txt,
        messaggi=messaggi_validi,
        utente=session.get('username'),
        errore=errore,
        db_attivo=bool(KV_URL and KV_TOKEN)
    )


@app.route('/join', methods=['POST'])
def join():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()

    if not username or not password or len(username) > 20:
        return redirect(url_for('home', errore="Inserisci username (max 20 caratteri) e password."))

    if KV_URL and KV_TOKEN:
        hashed_pw = db_cmd("HGET", "hacker_users", username)
        if hashed_pw:
            if check_password_hash(hashed_pw, password):
                session['username'] = username
                return redirect(url_for('home'))
            return redirect(url_for('home', errore="Password errata per questo username."))
        db_cmd("HSET", "hacker_users", username, generate_password_hash(password))
        session['username'] = username
        return redirect(url_for('home'))
    else:
        if username in local_users:
            if check_password_hash(local_users[username], password):
                session['username'] = username
                return redirect(url_for('home'))
            return redirect(url_for('home', errore="Password errata."))
        local_users[username] = generate_password_hash(password)
        session['username'] = username
        return redirect(url_for('home'))


@app.route('/chat', methods=['POST'])
def chat():
    if 'username' not in session:
        return redirect(url_for('home', errore="Devi unirti alla community per inviare messaggi."))

    testo_msg = request.form.get('messaggio', '').strip()
    if testo_msg and len(testo_msg) <= 500:
        ora = time.time()
        payload = {
            "user": session['username'],
            "text": testo_msg,
            "date": datetime.utcnow().strftime('%d/%m/%Y %H:%M UTC'),
            "timestamp": ora
        }
        if KV_URL and KV_TOKEN:
            db_cmd("ZADD", "hacker_chat", ora, json.dumps(payload))
        else:
            local_chat.append(payload)

    return redirect(url_for('home'))


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)