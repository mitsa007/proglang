import os
import re
import datetime
import firebase_admin
from firebase_admin import credentials, firestore, storage
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import numpy as np

# ── App init ──────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY']          = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024   # 5 MB max upload

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
    )


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
        calorie_goal=1400,
        today=today,
        now=now,
        past_meals_by_date=past_meals_by_date,
    )


@app.route('/add_meal', methods=['POST'])
@login_required
def add_meal():
    fs.collection('meals').add({
        'user_id':   current_user.username,
        'meal_name': request.form.get('meal_name', '').strip(),
        'date':      request.form.get('date', datetime.date.today().isoformat()),
        'time':      request.form.get('time', '00:00'),
        'calories':  int(request.form.get('calories', 0)),
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
    return render_template('progress.html',
        logs=logs,
        prediction=prediction,
        chart_labels=chart_labels,
        chart_weights=chart_weights,
        today=today,
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
            'age': None, 'height': None, 'goal': None,
            'starting_weight': None, 'target_weight': None, 'photo_url': '',
        })
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))
