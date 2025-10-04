from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from openai import OpenAI
from sqlalchemy import text
from datetime import datetime, timedelta
import os
import fitz
import re

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///flashcards.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.urandom(24)

db = SQLAlchemy(app)

OPENAI_KEY = "your_openai_api_key_here"
ai_client = OpenAI(api_key=OPENAI_KEY)

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    name = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    points = db.Column(db.Integer, default=0)
    streak = db.Column(db.Integer, default=0)
    last_day = db.Column(db.Date, default=datetime.utcnow)

def make_columns_if_missing():
    table = Player.__table__.name
    with db.engine.connect() as conn:
        result = conn.execute(text(f"PRAGMA table_info('{table}')"))
        cols = [r[1] for r in result]
        if 'points' not in cols:
            conn.execute(text(f"ALTER TABLE '{table}' ADD COLUMN points INTEGER DEFAULT 0"))
        if 'streak' not in cols:
            conn.execute(text(f"ALTER TABLE '{table}' ADD COLUMN streak INTEGER DEFAULT 0"))
        if 'last_day' not in cols:
            conn.execute(text(f"ALTER TABLE '{table}' ADD COLUMN last_day DATE"))
        conn.commit()

with app.app_context():
    db.create_all()
    make_columns_if_missing()

def make_flashcards(num, topic, grade):
    try:
        num = int(num)
    except:
        num = 5
    prompt = (
        f"Make {num} flashcards about '{topic}' for grade {grade}. "
        "Format exactly like this:\nQuestion: <question>\nAnswer: <answer>\n\n"
        "No extra text or numbering."
    )
    resp = ai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    try:
        return resp.choices[0].message.content.strip()
    except:
        return str(resp)

def make_hint(question, answer):
    prompt = f"Give a short hint for the question '{question}' with answer '{answer}' without giving it away."
    resp = ai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    try:
        return resp.choices[0].message.content.strip()
    except:
        return "Think carefully!"

def parse_flashcards(text, grade):
    cards = []
    if not text:
        return cards
    lines = [l.strip() for l in text.replace('\r\n','\n').split('\n') if l.strip() != '']
    q, a = None, None
    for l in lines:
        if re.match(r'^Question\s*:', l, re.I):
            if q and a:
                hint = make_hint(q, a)
                cards.append({"q": q, "a": a, "hint": hint, "grade": grade})
            q = l.split(':',1)[1].strip()
            a = None
        elif re.match(r'^Answer\s*:', l, re.I):
            a = l.split(':',1)[1].strip()
        else:
            if q and not a: q += " " + l
            elif a and not q: a += " " + l
    if q and a:
        hint = make_hint(q, a)
        cards.append({"q": q, "a": a, "hint": hint, "grade": grade})
    return cards

def is_correct(user_ans, correct_ans):
    if not user_ans.strip(): return False
    if user_ans.strip().lower() == correct_ans.strip().lower(): return True
    prompt = f"Is '{user_ans}' basically the same as '{correct_ans}'? Answer yes or no."
    resp = ai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    try:
        return resp.choices[0].message.content.strip().lower().startswith("yes")
    except:
        return False

def pdf_to_text(file):
    txt = ""
    file.stream.seek(0)
    with fitz.open(stream=file.read(), filetype="pdf") as doc:
        for page in doc: txt += page.get_text()
    return txt

@app.route('/', methods=['GET','POST'])
def home():
    if 'player_id' not in session: return redirect(url_for('login'))
    player = Player.query.get(session['player_id'])
    today = datetime.utcnow().date()
    last = player.last_day or today
    if last < today:
        if last == today - timedelta(days=1):
            player.streak += 1
        else:
            player.streak = 1
        player.last_day = today
        db.session.commit()
    cards = []
    grades = list(range(1,13))
    if request.method == 'POST':
        try:
            num = int(request.form['num_flashcards'])
            grade = int(request.form['grade_level'])
        except:
            num, grade = 5, 1
        topic = request.form.get('prompt','').strip()
        if num > 0 and topic:
            raw = make_flashcards(num, topic, grade)
            cards = parse_flashcards(raw, grade)
            session['grade'] = grade
            session['total_cards'] = len(cards)
            session['score_cards'] = 0
    return render_template('index.html', flashcards=cards, grades=grades)

@app.route('/upload_pdf', methods=['GET','POST'])
def upload_pdf():
    if 'player_id' not in session: return redirect(url_for('login'))
    cards = []
    grades = list(range(1,13))
    if request.method == 'POST':
        file = request.files.get('pdf')
        if file and file.filename.lower().endswith('.pdf'):
            text = pdf_to_text(file)
            raw = make_flashcards(5, text[:3000], 10)
            cards = parse_flashcards(raw, 10)
            session['grade'] = 10
            session['total_cards'] = len(cards)
            session['score_cards'] = 0
            return render_template('index.html', flashcards=cards, grades=grades)
    return render_template('upload_pdf.html')

@app.route('/check_answer', methods=['POST'])
def check_answer_api():
    if 'player_id' not in session: return jsonify({"correct": False})
    data = request.get_json(force=True)
    user_ans = data.get('user_answer','')
    correct_ans = data.get('correct_answer','')
    result = is_correct(user_ans, correct_ans)
    if result:
        player = Player.query.get(session['player_id'])
        grade = session.get('grade',1)
        try: player.points += int(grade)
        except: player.points += 1
        db.session.commit()
        session['score_cards'] = session.get('score_cards',0) + 1
    return jsonify({"correct": result})

@app.route('/ask_question', methods=['POST'])
def ask_question_api():
    if 'player_id' not in session: return jsonify({'answer':'Please log in!'})
    data = request.get_json(force=True)
    q = data.get('question','').strip()
    card = data.get('flashcard',{})
    card_q = card.get('q','')
    card_a = card.get('a','')
    prompt = f"Answer the student's question '{q}' based on flashcard '{card_q}' = '{card_a}'"
    resp = ai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role":"user","content":prompt}]
    )
    try: reply = resp.choices[0].message.content.strip()
    except: reply = "Couldn't make an answer now."
    return jsonify({'answer': reply})

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        name = request.form['username']
        pw = request.form['password']
        player = Player.query.filter_by(name=name).first()
        if player and check_password_hash(player.password, pw):
            session['player_id'] = player.id
            return redirect(url_for('home'))
        return render_template('login.html', error="Wrong username or password.")
    return render_template('login.html')

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method=='POST':
        email = request.form['email']
        name = request.form['username']
        pw = request.form['password']
        if Player.query.filter((Player.email==email)|(Player.name==name)).first():
            return render_template('signup.html', error="Email or name exists.")
        hashed = generate_password_hash(pw)
        new_player = Player(email=email,name=name,password=hashed,points=0,streak=1,last_day=datetime.utcnow().date())
        db.session.add(new_player)
        db.session.commit()
        session['player_id'] = new_player.id
        return redirect(url_for('home'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/leaderboard')
def leaderboard():
    players = Player.query.order_by(Player.points.desc()).all()
    return render_template('leaderboard.html', users=players, enumerate=enumerate)

@app.route('/brainbreak')
def brainbreak():
    if 'player_id' not in session: return redirect(url_for('login'))
    return render_template('brainbreak.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
