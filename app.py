import os
from dotenv import load_dotenv
load_dotenv(override=True)   # load .env FIRST before anything else reads os.environ

import re
import datetime
import firebase_admin
from firebase_admin import credentials, firestore, storage
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import numpy as np
from google import genai

# ── App init ──────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY']          = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024   # 5 MB max upload

# ── Gemini AI init ────────────────────────────────────────────────────────────────────
_gemini_key = os.environ.get('GEMINI_API_KEY', '')
if _gemini_key and _gemini_key != 'your_gemini_api_key_here':
    gemini_client = genai.Client(api_key=_gemini_key)
    print(f'[Gemini] Client initialized with key: {_gemini_key[:12]}...')
else:
    gemini_client = None
    print('[Gemini] No API key found — AI insights disabled.')


def gemini_generate(prompt: str, retries: int = 2) -> str | None:
    """Call Gemini with simple retry on 429 rate-limit errors."""
    import time
    if not gemini_client:
        return None
    models_to_try = ['gemini-2.0-flash', 'gemini-flash-latest']
    for model in models_to_try:
        for attempt in range(retries):
            try:
                resp = gemini_client.models.generate_content(
                    model=model, contents=prompt
                )
                print(f'[Gemini] OK on {model}')
                return resp.text.strip()
            except Exception as e:
                err = str(e)
                if '429' in err and attempt < retries - 1:
                    wait = 2 ** attempt
                    print(f'[Gemini] Rate-limited on {model} — retrying in {wait}s…')
                    time.sleep(wait)
                elif '429' in err:
                    print(f'[Gemini] {model} quota exhausted — trying next model…')
                    break
                else:
                    print(f'[Gemini] Error on {model}: {e}')
                    return None
    print('[Gemini] All models exhausted — returning None')
    return None


# ── Gemini insight cache (24 h) ───────────────────────────────────────────────
# Keyed by user + latest weight value so it only refreshes when new data is logged.
# This keeps API calls to ~1 per user per day on the Progress page.
import hashlib as _hashlib
_gemini_cache: dict = {}   # { cache_key: (result_str, expires_at) }
_CACHE_TTL = 86400         # 24 hours — regenerates only when user logs new weight


def gemini_cached(prompt: str, cache_key: str) -> str | None:
    """Return cached Gemini result if fresh, otherwise call API and cache it."""
    import time
    now = time.time()
    if cache_key in _gemini_cache:
        result, expires = _gemini_cache[cache_key]
        if now < expires:
            print(f'[Gemini] Cache hit for {cache_key[:20]}…')
            return result
    result = gemini_generate(prompt)
    if result is not None:
        _gemini_cache[cache_key] = (result, now + _CACHE_TTL)
    return result


# ── Firebase init ─────────────────────────────────────────────────────────────
cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred, {
    'storageBucket': 'proglang-3a28a.firebasestorage.app'
})
fs = firestore.client()

# ── Flask-Login ───────────────────────────────────────────────────────────────
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# ── User model ────────────────────────────────────────────────────────────────
class User(UserMixin):
    def __init__(self, data: dict):
        self.id             = data.get('username')
        self.username       = data.get('username')
        self.name           = data.get('name')
        self.password       = data.get('password')
        self.age            = data.get('age')
        self.gender         = data.get('gender')
        self.height         = data.get('height')
        self.goal           = data.get('goal')
        self.starting_weight = data.get('starting_weight')
        self.target_weight  = data.get('target_weight')
        self.photo_url      = data.get('photo_url', '')

    @staticmethod
    def get(username: str):
        doc = fs.collection('users').document(username).get()
        return User(doc.to_dict()) if doc.exists else None


@login_manager.user_loader
def load_user(uid):
    return User.get(uid)


# ── Helpers ───────────────────────────────────────────────────────────────────
def get_current_weight(username):
    """Return the most recent weight (float) logged by user, or None."""
    docs = (fs.collection('weight_logs')
              .where('user_id', '==', username)
              .get())
    if not docs:
        return None
    sorted_docs = sorted(docs, key=lambda d: d.to_dict().get('date', ''), reverse=True)
    return float(sorted_docs[0].to_dict().get('weight', 0))


def calc_bmi(weight_kg, height_cm):
    try:
        h = float(height_cm) / 100
        return round(float(weight_kg) / (h * h), 1)
    except Exception:
        return None


def progress_pct(starting, target, current):
    try:
        total = abs(float(starting) - float(target))
        done  = abs(float(starting) - float(current))
        return min(100, int((done / total) * 100)) if total > 0 else 100
    except Exception:
        return 0


def compute_calorie_goal(user) -> int:
    """
    Calculate a personalised daily calorie goal using Mifflin-St Jeor BMR
    (gender-neutral version) adjusted for a lightly-active lifestyle and
    the user's stated goal.

    Falls back to 2000 kcal if profile data is incomplete.
    """
    try:
        weight = float(user.starting_weight or 0)
        height = float(user.height or 0)
        age    = float(user.age or 0)
        if weight <= 0 or height <= 0 or age <= 0:
            return 2000

        # Mifflin-St Jeor formula
        gender = (user.gender or '').lower()
        if gender == 'male':
            bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
        elif gender == 'female':
            bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
        else:
            # Average if unspecified/other
            bmr = (10 * weight) + (6.25 * height) - (5 * age) - 78

        # Lightly active multiplier (default — no activity level stored yet)
        tdee = bmr * 1.375

        goal = (user.goal or '').lower()
        if any(k in goal for k in ('lose', 'loss', 'cut', 'deficit')):
            tdee -= 500          # ~0.5 kg/week deficit
        elif any(k in goal for k in ('gain', 'muscle', 'bulk', 'surplus')):
            tdee += 300          # lean bulk surplus
        # 'maintain' or anything else → no adjustment

        return max(1200, int(round(tdee, -1)))   # never go below 1200
    except Exception:
        return 2000


def validate_password(password: str) -> str | None:
    """Return an error message string if the password is invalid, else None."""
    if len(password) < 8:
        return 'Password must be at least 8 characters long.'
    if not re.search(r'[A-Z]', password):
        return 'Password must contain at least one uppercase letter.'
    if not re.search(r'[0-9]', password):
        return 'Password must contain at least one number.'
    return None


# ── MET lookup table (exercise type × intensity) ─────────────────────────────
# Values based on the Compendium of Physical Activities (Ainsworth et al.)
# Formula: kcal = MET × body_weight_kg × duration_hours
MET_TABLE = {
    'running':       {'Low': 6.0,  'Medium': 9.8,  'High': 12.8},
    'cycling':       {'Low': 4.0,  'Medium': 6.8,  'High': 10.0},
    'swimming':      {'Low': 5.8,  'Medium': 7.0,  'High': 9.8 },
    'weightlifting': {'Low': 3.0,  'Medium': 5.0,  'High': 6.0 },
    'yoga':          {'Low': 2.5,  'Medium': 3.0,  'High': 4.0 },
    'hiit':          {'Low': 6.0,  'Medium': 8.0,  'High': 10.0},
    'walking':       {'Low': 2.5,  'Medium': 3.5,  'High': 4.5 },
    'pilates':       {'Low': 2.8,  'Medium': 3.5,  'High': 4.5 },
    'dancing':       {'Low': 3.0,  'Medium': 5.0,  'High': 7.8 },
    'boxing':        {'Low': 5.0,  'Medium': 7.8,  'High': 10.5},
    'rowing':        {'Low': 4.8,  'Medium': 7.0,  'High': 10.0},
    'elliptical':    {'Low': 4.0,  'Medium': 6.0,  'High': 8.5 },
    'jump rope':     {'Low': 8.8,  'Medium': 11.0, 'High': 12.3},
    'basketball':    {'Low': 4.5,  'Medium': 6.5,  'High': 8.0 },
    'football':      {'Low': 5.0,  'Medium': 7.0,  'High': 9.0 },
    'tennis':        {'Low': 5.0,  'Medium': 7.0,  'High': 9.0 },
    # fallback for any unlisted exercise
    '_default':      {'Low': 3.5,  'Medium': 6.0,  'High': 9.0 },
}

def est_kcal(workout_type: str, intensity: str, duration_mins: float, weight_kg: float) -> int:
    """Return estimated kcal burned using the MET formula."""
    key     = workout_type.strip().lower()
    row     = MET_TABLE.get(key, MET_TABLE['_default'])
    met     = row.get(str(intensity).capitalize(), 6.0)
    return int(met * weight_kg * (duration_mins / 60))


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/create_profile', methods=['POST'])
def create_profile():
    name     = request.form['name']
    username = name.replace(' ', '_').lower()
    w        = request.form.get('weight')
    user_data = {
        'username':        username,
        'name':            name,
        'password':        generate_password_hash('password', method='pbkdf2:sha256'),
        'age':             request.form.get('age'),
        'gender':          request.form.get('gender'),
        'height':          None,
        'goal':            request.form.get('goal'),
        'starting_weight': w,
        'target_weight':   None,
        'photo_url':       '',
    }
    fs.collection('users').document(username).set(user_data)
    if w:
        fs.collection('weight_logs').add({
            'user_id': username,
            'date':    datetime.date.today().isoformat(),
            'weight':  float(w),
        })
    login_user(User(user_data))
    return redirect(url_for('overview'))


# ── Dashboard / Overview ──────────────────────────────────────────────────────
@app.route('/overview')
@login_required
def overview():
    today = datetime.date.today().isoformat()
    u     = current_user.username

    workout_docs = fs.collection('workouts').where('user_id', '==', u).get()
    meal_docs    = fs.collection('meals').where('user_id', '==', u).get()

    workout_list = [d.to_dict() for d in workout_docs]
    meal_list    = [d.to_dict() for d in meal_docs]
    today_meals  = [m for m in meal_list if m.get('date') == today]

    # MET-based calorie estimator (type + intensity lookup)
    user_weight = float(current_user.starting_weight or 70)

    def est_calories(w):
        return est_kcal(
            w.get('workout_type', ''),
            w.get('intensity', 'Medium'),
            float(w.get('duration', 0)),
            user_weight,
        )

    calories_burned  = int(sum(est_calories(w) for w in workout_list))
    workout_count    = len(workout_list)
    meal_count       = len(meal_list)
    today_cals       = sum(int(m.get('calories', 0)) for m in today_meals)

    intensities   = [w.get('intensity','') for w in workout_list if w.get('intensity')]
    avg_intensity = max(set(intensities), key=intensities.count).capitalize() if intensities else 'N/A'

    cur_w  = get_current_weight(u)
    pct    = progress_pct(current_user.starting_weight, current_user.target_weight, cur_w) if cur_w else 0

    # ── Weekly bar chart data (Mon–Sun of current ISO week) ───────────────────
    import datetime as dt
    today_date = dt.date.today()
    # Monday of current week
    week_start = today_date - dt.timedelta(days=today_date.weekday())
    week_days  = [week_start + dt.timedelta(days=i) for i in range(7)]
    day_labels = [d.strftime('%a') for d in week_days]

    weekly_cals = []
    for day in week_days:
        day_str   = day.isoformat()
        day_total = sum(
            est_calories(w) for w in workout_list
            if w.get('date') == day_str
        )
        weekly_cals.append(round(day_total, 1))

    # ── Fasting status + history ─────────────────────────────────────────────
    fasting_doc = None
    fasting_docs = (
        fs.collection('fasting_logs')
        .where('user_id', '==', u)
        .where('is_active', '==', True)
        .get()
    )
    if fasting_docs:
        fasting_doc = fasting_docs[0].to_dict()

    # Past completed fasts (most recent 10)
    all_fasts = [
        d.to_dict() for d in
        fs.collection('fasting_logs')
          .where('user_id', '==', u)
          .where('is_active', '==', False)
          .get()
        if d.to_dict().get('end_time')  # only truly completed ones
    ]
    past_fasts = sorted(all_fasts, key=lambda x: x.get('end_time', ''), reverse=True)[:10]

    return render_template('overview.html',
        user=current_user,
        calories_burned=calories_burned,
        workout_count=workout_count,
        meal_count=meal_count,
        today_calories=today_cals,
        avg_intensity=avg_intensity,
        progress_percentage=pct,
        progress_message='You are doing great! Keep going!',
        weekly_labels=day_labels,
        weekly_calories=weekly_cals,
        fasting=fasting_doc,
        past_fasts=past_fasts,
    )


# ── AI API: Calorie Estimator ─────────────────────────────────────────────────
@app.route('/api/estimate_calories', methods=['POST'])
@login_required
def api_estimate_calories():
    from flask import jsonify
    meal_name = request.json.get('meal_name', '').strip()
    if not meal_name:
        return jsonify({'calories': 0, 'error': 'No meal name provided'}), 400
    if not gemini_client:
        return jsonify({'calories': 400, 'note': 'AI unavailable — using default'}), 200
    prompt = (
        f'Estimate the calories in one typical serving of "{meal_name}". '
        'Return only a single integer number. No text, no explanation.'
    )
    text = gemini_generate(prompt)
    if text is None:
        return jsonify({'calories': 400, 'note': 'Estimation unavailable'}), 200
    cal = int(''.join(filter(str.isdigit, text[:6])) or '400')
    return jsonify({'calories': cal})


# ── AI API: Chatbot ───────────────────────────────────────────────────────────
@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    from flask import jsonify
    import json as _json
    message = request.json.get('message', '').strip()
    if not message:
        return jsonify({'reply': 'Please type a message.'}), 400
    today = datetime.date.today().isoformat()
    now   = datetime.datetime.now().strftime('%H:%M')
    u     = current_user.username

    # Save user message to history
    fs.collection('chat_logs').add({
        'user_id': u, 'role': 'user',
        'message': message,
        'timestamp': datetime.datetime.utcnow().isoformat(),
    })

    if not gemini_client:
        reply = 'AI is not configured. Please add your Gemini API key to the .env file.'
        fs.collection('chat_logs').add({
            'user_id': u, 'role': 'bot', 'message': reply,
            'timestamp': datetime.datetime.utcnow().isoformat(),
        })
        return jsonify({'reply': reply, 'action': None})

    prompt = f"""You are VitCheck's AI fitness assistant. Parse the user message and respond with valid JSON only.

User: {current_user.name}
Today: {today}  Time: {now}

Supported intents:
- log_meal: extract meal_name and estimate calories
- log_workout: extract workout_type (Running/Swimming/Cycling/Weightlifting/Yoga/Walking/HIIT/Other), duration (int, minutes), intensity (Low/Medium/High)
- log_weight: extract weight (float, kg)
- start_fast: user wants to begin a fast
- end_fast: user wants to end their fast
- general_question: anything else — answer helpfully

Respond ONLY with this JSON (no markdown, no backticks):
{{
  "intent": "<intent>",
  "data": {{ ... extracted fields ... }},
  "reply": "<friendly confirmation or answer in 1-2 sentences>"
}}

User message: {message}"""

    text = gemini_generate(prompt)
    if text is None:
        parsed = {'intent': 'general_question', 'data': {}, 'reply': 'AI is temporarily unavailable. Please try again in a moment.'}
    else:
        import re as _re
        json_match = _re.search(r'\{[\s\S]*\}', text)
        try:
            parsed = _json.loads(json_match.group()) if json_match else {}
            if not parsed.get('intent'):
                raise ValueError('missing intent')
        except Exception as e:
            print(f'[Chat] JSON parse error: {e} | raw: {text[:200]}')
            parsed = {'intent': 'general_question', 'data': {}, 'reply': 'Sorry, I had trouble understanding that. Please try again.'}

    intent = parsed.get('intent', 'general_question')
    data   = parsed.get('data', {})
    reply  = parsed.get('reply', 'Done!')
    print(f'[Chat] intent={intent} | user={u} | msg={message[:50]}')

    # ── Execute the action ────────────────────────────────────────────────────
    if intent == 'log_meal':
        fs.collection('meals').add({
            'user_id':   u,
            'meal_name': data.get('meal_name', message),
            'calories':  int(data.get('estimated_calories', data.get('calories', 400))),
            'date':      today,
            'time':      now,
        })
    elif intent == 'log_workout':
        fs.collection('workouts').add({
            'user_id':      u,
            'workout_type': data.get('workout_type', 'Other'),
            'duration':     int(data.get('duration', 30)),
            'intensity':    data.get('intensity', 'Medium'),
            'date':         today,
            'time':         now,
        })
    elif intent == 'log_weight':
        fs.collection('weight_logs').add({
            'user_id': u,
            'weight':  float(data.get('weight', 0)),
            'date':    today,
        })
    elif intent == 'start_fast':
        # Deactivate any existing active fast first
        for doc in fs.collection('fasting_logs').where('user_id','==',u).where('is_active','==',True).get():
            doc.reference.update({'is_active': False})
        fs.collection('fasting_logs').add({
            'user_id':    u,
            'start_time': datetime.datetime.utcnow().isoformat(),
            'end_time':   None,
            'calories_burned': None,
            'is_active':  True,
        })
    elif intent == 'end_fast':
        active = fs.collection('fasting_logs').where('user_id','==',u).where('is_active','==',True).get()
        for doc in active:
            d = doc.to_dict()
            start = datetime.datetime.fromisoformat(d['start_time'])
            end   = datetime.datetime.utcnow()
            hours = (end - start).total_seconds() / 3600
            # BMR-based calorie burn: ~0.9 kcal/kg/hr while fasting
            weight_kg = float(current_user.starting_weight or 70)
            kcal_burned = round(0.9 * weight_kg * hours, 1)
            doc.reference.update({
                'end_time':       end.isoformat(),
                'calories_burned': kcal_burned,
                'is_active':       False,
                'duration_hours':  round(hours, 2),
            })
            reply = f'{reply} You fasted for {round(hours, 1)} hours and burned approximately {kcal_burned} kcal.'

    # Save bot reply to history
    fs.collection('chat_logs').add({
        'user_id': u, 'role': 'bot', 'message': reply,
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'intent': intent,
    })
    return jsonify({'reply': reply, 'action': intent})


# ── AI API: Chat History ──────────────────────────────────────────────────────
@app.route('/api/chat_history')
@login_required
def api_chat_history():
    from flask import jsonify
    docs = (
        fs.collection('chat_logs')
        .where('user_id', '==', current_user.username)
        .get()
    )
    history = sorted(
        [d.to_dict() for d in docs],
        key=lambda x: x.get('timestamp', '')
    )[-40:]  # last 40 messages
    return jsonify(history)


# ── API: Start / End Fast (manual buttons) ────────────────────────────────────
@app.route('/api/start_fast', methods=['POST'])
@login_required
def api_start_fast():
    from flask import jsonify
    u = current_user.username
    for doc in fs.collection('fasting_logs').where('user_id','==',u).where('is_active','==',True).get():
        doc.reference.update({'is_active': False})
    fs.collection('fasting_logs').add({
        'user_id':    u,
        'start_time': datetime.datetime.utcnow().isoformat(),
        'end_time':   None,
        'calories_burned': None,
        'is_active':  True,
    })
    return jsonify({'status': 'started'})


@app.route('/api/end_fast', methods=['POST'])
@login_required
def api_end_fast():
    from flask import jsonify
    u = current_user.username
    # Use most recent logged weight for accuracy; fall back to starting_weight
    weight_kg = get_current_weight(u) or float(current_user.starting_weight or 70)
    result = {'status': 'none_active'}
    for doc in fs.collection('fasting_logs').where('user_id','==',u).where('is_active','==',True).get():
        d = doc.to_dict()
        start = datetime.datetime.fromisoformat(d['start_time'])
        end   = datetime.datetime.utcnow()
        hours = (end - start).total_seconds() / 3600
        kcal  = round(0.9 * weight_kg * hours, 1)
        doc.reference.update({
            'end_time':        end.isoformat(),
            'calories_burned': kcal,
            'is_active':       False,
            'duration_hours':  round(hours, 2),
            'weight_used_kg':  weight_kg,
        })
        result = {'status': 'ended', 'hours': round(hours, 1), 'calories_burned': kcal}
    return jsonify(result)


@app.route('/api/fasting_status')
@login_required
def api_fasting_status():
    from flask import jsonify
    docs = fs.collection('fasting_logs').where('user_id','==',current_user.username).where('is_active','==',True).get()
    if docs:
        d = docs[0].to_dict()
        return jsonify({'is_fasting': True, 'start_time': d['start_time']})
    return jsonify({'is_fasting': False})


# ── Workout ───────────────────────────────────────────────────────────────────
@app.route('/workout')
@login_required
def workout():
    docs = fs.collection('workouts').where('user_id', '==', current_user.username).get()
    workouts = sorted(
        [{'id': d.id, **d.to_dict()} for d in docs],
        key=lambda x: (x.get('date',''), x.get('time','')),
        reverse=True
    )
    today = datetime.date.today().isoformat()
    now   = datetime.datetime.now().strftime('%H:%M')
    user_weight = float(current_user.starting_weight or 70)

    # Annotate each workout with estimated kcal burned
    for w in workouts:
        w['est_kcal'] = est_kcal(
            w.get('workout_type', ''),
            w.get('intensity', 'Medium'),
            float(w.get('duration', 0)),
            user_weight,
        )

    return render_template('workout_tracker.html', workouts=workouts, today=today, now=now)


@app.route('/add_workout', methods=['POST'])
@login_required
def add_workout():
    fs.collection('workouts').add({
        'user_id':      current_user.username,
        'workout_type': request.form.get('workout_type', '').strip(),
        'date':         request.form.get('date', datetime.date.today().isoformat()),
        'time':         request.form.get('time', '00:00'),
        'duration':     int(request.form.get('duration', 30)),
        'intensity':    request.form.get('intensity', 'Medium'),
    })
    return redirect(url_for('workout'))


@app.route('/delete_workout/<doc_id>', methods=['POST'])
@login_required
def delete_workout(doc_id):
    fs.collection('workouts').document(doc_id).delete()
    return redirect(url_for('workout'))


# ── Meals ─────────────────────────────────────────────────────────────────────
@app.route('/meals')
@login_required
def meals():
    docs = fs.collection('meals').where('user_id', '==', current_user.username).get()
    meals_list = sorted(
        [{'id': d.id, **d.to_dict()} for d in docs],
        key=lambda x: (x.get('date',''), x.get('time','')),
        reverse=True
    )
    today       = datetime.date.today().isoformat()
    now         = datetime.datetime.now().strftime('%H:%M')
    today_meals = [m for m in meals_list if m.get('date') == today]
    today_cals  = sum(int(m.get('calories', 0)) for m in today_meals)

    # Build past meals grouped by date (newest date first, today excluded)
    past_meals_by_date = {}
    for m in meals_list:
        d = m.get('date', '')
        if d and d != today:
            past_meals_by_date.setdefault(d, []).append(m)
    # Sort dates newest-first
    past_meals_by_date = dict(
        sorted(past_meals_by_date.items(), key=lambda x: x[0], reverse=True)
    )

    return render_template('meal_tracker.html',
        meals=meals_list,
        today_meals=today_meals,
        today_calories=today_cals,
        calorie_goal=compute_calorie_goal(current_user),
        today=today,
        now=now,
        past_meals_by_date=past_meals_by_date,
    )


@app.route('/add_meal', methods=['POST'])
@login_required
def add_meal():
    calories_raw = request.form.get('calories', '0').strip()
    try:
        calories = int(float(calories_raw)) if calories_raw else 400
    except ValueError:
        calories = 400
    fs.collection('meals').add({
        'user_id':   current_user.username,
        'meal_name': request.form.get('meal_name', '').strip(),
        'date':      request.form.get('date', datetime.date.today().isoformat()),
        'time':      request.form.get('time', '00:00'),
        'calories':  calories,
    })
    return redirect(url_for('meals'))


@app.route('/delete_meal/<doc_id>', methods=['POST'])
@login_required
def delete_meal(doc_id):
    fs.collection('meals').document(doc_id).delete()
    return redirect(url_for('meals'))


# ── Progress ──────────────────────────────────────────────────────────────────
@app.route('/progress')
@login_required
def progress():
    docs = fs.collection('weight_logs').where('user_id', '==', current_user.username).get()
    logs = sorted(
        [{'id': d.id, **d.to_dict()} for d in docs],
        key=lambda x: x.get('date',''),
        reverse=True
    )

    prediction    = None
    chart_labels  = []
    chart_weights = []

    if len(logs) >= 2:
        asc     = sorted(logs, key=lambda x: x.get('date',''))
        weights = [float(l['weight']) for l in asc]
        chart_labels  = [l['date'] for l in asc]
        chart_weights = weights
        x      = np.arange(len(weights))
        coeffs = np.polyfit(x, weights, 1)
        nxt    = round(float(np.polyval(coeffs, len(weights))), 1)
        prediction = {
            'next_weight': nxt,
            'trend':       'decreasing' if coeffs[0] < 0 else 'increasing',
            'slope':       round(float(coeffs[0]), 3),
        }

    today = datetime.date.today().isoformat()

    # ── Gemini AI Insight ─────────────────────────────────────────────────────
    ai_insight = None
    if gemini_client and prediction and len(logs) >= 2:
        prompt = f"""You are an expert fitness coach inside VitCheck.
Your goal is to provide a "Trend Insight" for the user {current_user.name}.

User Stats:
- Current weight: {logs[0]['weight']} kg
- Target weight: {current_user.target_weight} kg
- Trend: {prediction['trend']} at {abs(prediction['slope']):.3f} kg per entry
- Next predicted weight: {prediction['next_weight']} kg

Please provide exactly 2 short sentences:
1. A trend observation: Analyze their current momentum toward their goal.
2. An actionable recommendation: One specific thing they should do today.

Be professional, encouraging, and do not use any markdown or bullets."""
        latest_weight = logs[0].get('weight', 0)   # changes only when new entry logged
        cache_key = f"insight:{current_user.username}:{latest_weight}:{prediction['trend']}"
        ai_insight = gemini_cached(prompt, cache_key)

    return render_template('progress.html',
        logs=logs,
        prediction=prediction,
        chart_labels=chart_labels,
        chart_weights=chart_weights,
        today=today,
        ai_insight=ai_insight,
    )


@app.route('/log_weight', methods=['POST'])
@login_required
def log_weight():
    fs.collection('weight_logs').add({
        'user_id': current_user.username,
        'date':    request.form.get('date', datetime.date.today().isoformat()),
        'weight':  float(request.form.get('weight', 0)),
    })
    return redirect(url_for('progress'))


@app.route('/delete_weight/<doc_id>', methods=['POST'])
@login_required
def delete_weight(doc_id):
    fs.collection('weight_logs').document(doc_id).delete()
    return redirect(url_for('progress'))


# ── Profile ───────────────────────────────────────────────────────────────────
@app.route('/profile')
@login_required
def profile():
    cur_w = get_current_weight(current_user.username)
    bmi   = calc_bmi(cur_w, current_user.height) if cur_w and current_user.height else None
    return render_template('profile.html', user=current_user, current_weight=cur_w, bmi=bmi)


@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    update_data = {
        'name':            request.form.get('name'),
        'age':             request.form.get('age'),
        'gender':          request.form.get('gender'),
        'height':          request.form.get('height'),
        'starting_weight': request.form.get('starting_weight'),
        'target_weight':   request.form.get('target_weight'),
        'goal':            request.form.get('goal'),
    }
    photo = request.files.get('photo')
    photo_data = request.form.get('photo_data', '')

    if photo_data and photo_data.startswith('data:image'):
        # Cropped base64 from Cropper.js
        try:
            import base64 as b64mod
            header, data = photo_data.split(',', 1)
            img_bytes = b64mod.b64decode(data)
            bucket = storage.bucket()
            blob   = bucket.blob(f'profile_photos/{current_user.username}.jpg')
            blob.upload_from_string(img_bytes, content_type='image/jpeg')
            blob.make_public()
            update_data['photo_url'] = blob.public_url
        except Exception as e:
            flash(f'Photo upload failed: {e}')
    elif photo and photo.filename:
        # Raw file fallback
        try:
            bucket = storage.bucket()
            blob   = bucket.blob(f'profile_photos/{current_user.username}')
            blob.upload_from_file(photo, content_type=photo.content_type)
            blob.make_public()
            update_data['photo_url'] = blob.public_url
        except Exception as e:
            flash(f'Photo upload failed: {e}')
    fs.collection('users').document(current_user.username).update(update_data)
    flash('Profile updated successfully!')
    return redirect(url_for('profile'))


@app.route('/reset_data', methods=['POST'])
@login_required
def reset_data():
    u = current_user.username
    for col in ('workouts', 'meals', 'weight_logs'):
        for doc in fs.collection(col).where('user_id', '==', u).get():
            doc.reference.delete()
    flash('All your data has been reset.')
    return redirect(url_for('profile'))


@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    current_pw  = request.form.get('current_password', '')
    new_pw      = request.form.get('new_password', '')
    confirm_pw  = request.form.get('confirm_password', '')

    # Verify current password
    if not check_password_hash(current_user.password, current_pw):
        flash('Current password is incorrect.')
        return redirect(url_for('profile'))

    # Check new password matches confirmation
    if new_pw != confirm_pw:
        flash('New passwords do not match.')
        return redirect(url_for('profile'))

    # Enforce strength rules
    pw_error = validate_password(new_pw)
    if pw_error:
        flash(pw_error)
        return redirect(url_for('profile'))

    # Save new hashed password
    hashed = generate_password_hash(new_pw, method='pbkdf2:sha256')
    fs.collection('users').document(current_user.username).update({'password': hashed})
    flash('Password changed successfully!')
    return redirect(url_for('profile'))



# ── Auth ──────────────────────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.get(request.form['username'])
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('overview'))
        flash('Invalid username or password')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if fs.collection('users').document(username).get().exists:
            flash('Username already taken — please choose another.')
            return render_template('register.html')
        pw_error = validate_password(password)
        if pw_error:
            flash(pw_error)
            return render_template('register.html')
        hashed = generate_password_hash(password, method='pbkdf2:sha256')
        fs.collection('users').document(username).set({
            'username': username, 'name': request.form['name'],
            'password': hashed,
            'age': None, 'gender': None, 'height': None, 'goal': None,
            'starting_weight': None, 'target_weight': None, 'photo_url': '',
        })
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))
