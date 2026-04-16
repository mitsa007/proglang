"""
seed_demo.py — Creates a realistic demo account in Firestore.

Account credentials:
  Username : alex_fit
  Password : FitDemo1

Run from the project root with the venv active:
  python seed_demo.py
"""

import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from werkzeug.security import generate_password_hash

# ── Firebase init ─────────────────────────────────────────────────────────────
cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred, {
    'storageBucket': 'proglang-3a28a.firebasestorage.app'
})
fs = firestore.client()

USERNAME = 'alex_fit'
TODAY    = datetime.date.today()

def d(days_ago: int) -> str:
    return (TODAY - datetime.timedelta(days=days_ago)).isoformat()

# ─────────────────────────────────────────────────────────────────────────────
# 1. User profile
# ─────────────────────────────────────────────────────────────────────────────
print('Creating user…')
fs.collection('users').document(USERNAME).set({
    'username':        USERNAME,
    'name':            'Alex Rivera',
    'password':        generate_password_hash('FitDemo1', method='pbkdf2:sha256'),
    'age':             '26',
    'height':          '168',
    'goal':            'lose',
    'starting_weight': '78',
    'target_weight':   '65',
    'photo_url':       '',
})

# ─────────────────────────────────────────────────────────────────────────────
# 2. Weight logs — steady downward trend with natural daily fluctuation
# ─────────────────────────────────────────────────────────────────────────────
print('Adding weight logs…')
weight_logs = [
    # (days_ago, weight_kg)
    (30, 78.0),
    (27, 77.7),
    (24, 77.5),
    (21, 77.2),
    (18, 76.9),
    (15, 76.6),
    (12, 76.4),
    (9,  76.1),
    (6,  75.8),
    (3,  75.5),
    (0,  75.2),   # today — latest
]
for days_ago, weight in weight_logs:
    fs.collection('weight_logs').add({
        'user_id': USERNAME,
        'date':    d(days_ago),
        'weight':  weight,
    })

# ─────────────────────────────────────────────────────────────────────────────
# 3. Workout logs — 5 sessions/week, progressive intensity & duration
# ─────────────────────────────────────────────────────────────────────────────
print('Adding workout logs…')
workouts = [
    # Week 1 (days 29-23)
    ('Running',       d(29), '06:30', 30, 'Medium'),
    ('Yoga',          d(27), '07:00', 30, 'Low'),
    ('Cycling',       d(26), '06:45', 40, 'Medium'),
    ('Weightlifting', d(25), '07:15', 45, 'Medium'),
    ('Running',       d(23), '06:30', 35, 'Medium'),

    # Week 2 (days 22-16)
    ('Swimming',      d(22), '07:00', 30, 'High'),
    ('Yoga',          d(20), '07:00', 30, 'Low'),
    ('Running',       d(19), '06:30', 40, 'Medium'),
    ('Weightlifting', d(18), '07:15', 50, 'Medium'),
    ('Cycling',       d(16), '06:45', 45, 'Medium'),

    # Week 3 (days 15-9)
    ('Running',       d(15), '06:20', 40, 'High'),
    ('Weightlifting', d(14), '07:00', 55, 'Medium'),
    ('Swimming',      d(12), '06:45', 35, 'High'),
    ('Yoga',          d(11), '07:00', 30, 'Low'),
    ('Running',       d(9),  '06:20', 45, 'High'),

    # Week 4 (days 8-2)
    ('Weightlifting', d(8),  '07:00', 60, 'High'),
    ('Cycling',       d(7),  '06:30', 50, 'Medium'),
    ('Running',       d(6),  '06:15', 45, 'High'),
    ('Swimming',      d(4),  '06:45', 40, 'High'),
    ('Weightlifting', d(3),  '07:00', 60, 'High'),

    # This week (days 1-0)
    ('Running',       d(2),  '06:15', 50, 'High'),
    ('Yoga',          d(1),  '07:00', 30, 'Low'),
    ('Cycling',       d(0),  '06:30', 45, 'Medium'),
]
for wtype, date, time, dur, intensity in workouts:
    fs.collection('workouts').add({
        'user_id':      USERNAME,
        'workout_type': wtype,
        'date':         date,
        'time':         time,
        'duration':     dur,
        'intensity':    intensity,
    })

# ─────────────────────────────────────────────────────────────────────────────
# 4. Meal logs — caloric deficit diet (~1,600–1,750 kcal/day)
# ─────────────────────────────────────────────────────────────────────────────
print('Adding meal logs…')

# (meal_name, kcal, time)
daily_meal_plans = [
    # Plan A
    [('Oatmeal with berries',          320, '07:30'),
     ('Grilled chicken salad',          480, '12:30'),
     ('Baked salmon & steamed broccoli',520, '19:00'),
     ('Greek yogurt',                   130, '15:30')],

    # Plan B
    [('Scrambled eggs on whole wheat',  380, '08:00'),
     ('Tuna wrap with lettuce',          420, '12:00'),
     ('Chicken stir-fry with rice',     550, '19:30'),
     ('Apple',                           90, '15:00')],

    # Plan C
    [('Banana smoothie',                280, '07:45'),
     ('Lentil soup & bread',            460, '13:00'),
     ('Turkey breast with sweet potato',540, '19:00'),
     ('Almonds (handful)',              160, '16:00')],

    # Plan D
    [('Avocado toast',                  360, '08:00'),
     ('Caesar salad with chicken',      490, '12:30'),
     ('Grilled tilapia & asparagus',    480, '19:00'),
     ('Cottage cheese',                 140, '15:00')],
]

for days_ago in range(30, 0, -1):   # 30 days ago → yesterday (today stays empty)
    plan = daily_meal_plans[(30 - days_ago) % len(daily_meal_plans)]
    date = d(days_ago)
    for meal_name, kcal, time in plan:
        fs.collection('meals').add({
            'user_id':   USERNAME,
            'date':      date,
            'time':      time,
            'meal_name': meal_name,
            'calories':  kcal,
        })

print('\nDone! Demo account created.')
print('   Username : alex_fit')
print('   Password : FitDemo1')
