"""
add_progress.py -- Re-seeds weight logs AND workouts for the alex_fit demo account.
Run with: .venv\\Scripts\\python.exe add_progress.py
"""
import sys
import datetime
import firebase_admin
from firebase_admin import credentials, firestore

sys.stdout.reconfigure(encoding='utf-8')

cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred)
fs = firestore.client()

USERNAME = 'alex_fit'
TODAY    = datetime.date.today()

def d(days_ago: int) -> str:
    return (TODAY - datetime.timedelta(days=days_ago)).isoformat()

# ══════════════════════════════════════════════════════════════════════════════
# 1. Weight Logs — 30-day downward trend with realistic fluctuations
# ══════════════════════════════════════════════════════════════════════════════
print('Clearing old weight logs...')
existing = fs.collection('weight_logs').where('user_id', '==', USERNAME).get()
for doc in existing:
    doc.reference.delete()
print(f'  Deleted {len(existing)} old entries.')

print('Adding fresh weight logs...')
weight_logs = [
    # (days_ago, weight_kg)
    (30, 78.0),
    (27, 77.6),
    (24, 77.3),
    (21, 77.0),
    (18, 76.7),
    (15, 76.4),
    (12, 76.1),
    (9,  75.8),
    (6,  75.5),
    (3,  75.1),
    (0,  74.8),  # today
]
for days_ago, weight in weight_logs:
    fs.collection('weight_logs').add({
        'user_id': USERNAME,
        'date':    d(days_ago),
        'weight':  weight,
    })
    print(f'  {d(days_ago)} → {weight} kg')

print(f'\n✓ {len(weight_logs)} weight entries added.')

# ══════════════════════════════════════════════════════════════════════════════
# 2. Workouts — Current week (Mon-Sun) with varied exercises
# ══════════════════════════════════════════════════════════════════════════════
print('\nClearing old workouts...')
existing_w = fs.collection('workouts').where('user_id', '==', USERNAME).get()
for doc in existing_w:
    doc.reference.delete()
print(f'  Deleted {len(existing_w)} old entries.')

# Build current ISO week (Mon = 0)
week_start = TODAY - datetime.timedelta(days=TODAY.weekday())  # Monday
week_days  = [week_start + datetime.timedelta(days=i) for i in range(7)]

# Workout schedule for the week — realistic mixed program
workout_schedule = [
    # (day_index, workout_type, time, duration_mins, intensity)
    (0, 'Running',       '06:30', 40, 'Medium'),   # Monday
    (0, 'Weightlifting', '17:30', 45, 'High'),      # Monday PM
    (1, 'Cycling',       '06:45', 50, 'Medium'),    # Tuesday
    (2, 'Swimming',      '07:00', 35, 'High'),      # Wednesday
    (2, 'Yoga',          '18:00', 30, 'Low'),        # Wednesday PM
    (3, 'Running',       '06:15', 45, 'High'),      # Thursday
    (4, 'Weightlifting', '07:00', 60, 'High'),      # Friday
    (4, 'Walking',       '12:30', 30, 'Low'),        # Friday lunch
    (5, 'HIIT',          '08:00', 25, 'High'),      # Saturday
    (5, 'Cycling',       '16:00', 40, 'Medium'),    # Saturday PM
    (6, 'Yoga',          '09:00', 45, 'Medium'),    # Sunday
]

print('Adding fresh workouts for current week...')
added_workouts = 0
for day_idx, wtype, time, dur, intensity in workout_schedule:
    workout_date = week_days[day_idx]
    # Only add workouts up to today (don't seed future workouts)
    if workout_date > TODAY:
        continue
    fs.collection('workouts').add({
        'user_id':      USERNAME,
        'workout_type': wtype,
        'date':         workout_date.isoformat(),
        'time':         time,
        'duration':     dur,
        'intensity':    intensity,
    })
    day_name = workout_date.strftime('%a')
    print(f'  {day_name} {workout_date.isoformat()} — {wtype} ({dur}min, {intensity})')
    added_workouts += 1

print(f'\n✓ {added_workouts} workouts added for current week.')

# ══════════════════════════════════════════════════════════════════════════════
# 3. Meals — Add today's meals so the overview stats are populated
# ══════════════════════════════════════════════════════════════════════════════
print('\nClearing old meals...')
existing_m = fs.collection('meals').where('user_id', '==', USERNAME).get()
for doc in existing_m:
    doc.reference.delete()
print(f'  Deleted {len(existing_m)} old entries.')

print('Adding meals for the past 7 days...')
daily_plans = [
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

meal_count = 0
for days_ago in range(14, -1, -1):  # 14 days ago → today
    plan = daily_plans[days_ago % len(daily_plans)]
    date = d(days_ago)
    for meal_name, kcal, time in plan:
        fs.collection('meals').add({
            'user_id':   USERNAME,
            'date':      date,
            'time':      time,
            'meal_name': meal_name,
            'calories':  kcal,
        })
        meal_count += 1
    print(f'  {date} — {len(plan)} meals')

print(f'\n✓ {meal_count} meals added (past 14 days).')

print('\n══════════════════════════════════════════')
print(f'Done! All demo data refreshed for {USERNAME}.')
print('Visit http://127.0.0.1:5000/overview  — Activity chart')
print('Visit http://127.0.0.1:5000/progress  — Weight chart')
print('══════════════════════════════════════════')
