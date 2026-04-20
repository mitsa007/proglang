"""
add_progress.py -- Appends recent weight logs to the existing alex_fit demo account.
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

# ── Remove existing weight logs for this user and re-seed cleanly ─────────────
print('Clearing old weight logs...')
existing = fs.collection('weight_logs').where('user_id', '==', USERNAME).get()
for doc in existing:
    doc.reference.delete()
print(f'  Deleted {len(existing)} old entries.')

# ── Add 11 fresh weight logs ending at today ──────────────────────────────────
print('Adding fresh weight logs...')
weight_logs = [
    # (days_ago, weight_kg) — steady downward trend with realistic fluctuation
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

print(f'\nDone! {len(weight_logs)} weight entries added for {USERNAME}.')
print('Visit http://127.0.0.1:5000/progress to see the AI Trend Insight.')
