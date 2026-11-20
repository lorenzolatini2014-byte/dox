from flask import Flask, render_template, request, redirect, url_for, session
from datetime import timedelta
import os

template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
app = Flask(__name__, template_folder=template_dir)

app.secret_key = os.environ.get('SECRET_KEY', 'chiave-segreta-hacker-rosso-999')

# Cookie attivo max 10 giorni; se riapri il sito entro i 10 giorni, la scadenza riparte da 10 giorni
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=10)
app.config['SESSION_REFRESH_EACH_REQUEST'] = True


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

    errore = request.args.get('errore', '')
    return render_template(
        'index.html',
        testo=contenuto_txt,
        utente=session.get('username'),
        errore=errore
    )


@app.route('/join', methods=['POST'])
def join():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()

    if not username or not password or len(username) > 20:
        return redirect(url_for('home', errore="Inserisci username (max 20 caratteri) e password."))

    session['username'] = username
    return redirect(url_for('home'))


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
