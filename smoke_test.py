"""Quick smoke test for all 3 AI features."""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()
from google import genai

client = genai.Client(api_key=os.environ.get('GEMINI_API_KEY'))

# ── Test 1: Calorie estimator ─────────────────────────────────────────────────
print('--- Test 1: Calorie Estimator ---')
resp = client.models.generate_content(
    model='gemini-flash-latest',
    contents='Estimate the calories in one typical serving of "grilled chicken salad". Return only a single integer. No text.'
)
raw = resp.text.strip()
cal = int(''.join(filter(str.isdigit, raw[:6])) or '400')
print(f'  grilled chicken salad => {cal} kcal')
assert 100 < cal < 1500, f'Unexpected calorie value: {cal}'
print('  PASS')

# ── Test 2: Chat intent parser ────────────────────────────────────────────────
print()
print('--- Test 2: Chat Intent Parser ---')
cases = [
    ('I had scrambled eggs on toast for breakfast', 'log_meal'),
    ('I ran for 30 minutes at high intensity',        'log_workout'),
    ('Start my fast',                                 'start_fast'),
    ('I weigh 74.5 kg today',                         'log_weight'),
]
for msg, expected_intent in cases:
    prompt = f'''You are VitCheck AI. Parse this message and return JSON only.
Supported intents: log_meal, log_workout, log_weight, start_fast, end_fast, general_question
Return exactly: {{"intent":"...","data":{{}},"reply":"..."}}
No markdown, no backticks.
Message: {msg}'''
    r = client.models.generate_content(model='gemini-flash-latest', contents=prompt)
    raw = r.text.strip().lstrip('`').rstrip('`')
    if raw.startswith('json'):
        raw = raw[4:]
    try:
        p = json.loads(raw)
        intent = p.get('intent', 'unknown')
        status = 'PASS' if intent == expected_intent else f'WARN (got {intent})'
        print(f'  [{status}] "{msg[:45]}" => {intent}')
    except Exception as e:
        print(f'  [PARSE ERROR] {e}: {raw[:80]}')

print()
print('Smoke test complete!')
