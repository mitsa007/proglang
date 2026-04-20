"""Quick test to verify the Gemini API key is valid and working."""
import os
import sys
from dotenv import load_dotenv
from google import genai

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

key = os.environ.get('GEMINI_API_KEY', '')

if not key or key == 'your_gemini_api_key_here':
    print("[FAIL] No valid API key found in .env")
    print("   -> Open .env and replace 'your_gemini_api_key_here' with your real key")
else:
    print(f"[OK] API key loaded: {key[:8]}...{key[-4:]}")
    try:
        client = genai.Client(api_key=key)
        resp = client.models.generate_content(
            model='gemini-flash-latest',
            contents="Say 'VitCheck API is working!' in one sentence.",
        )
        print(f"[OK] Gemini response: {resp.text.strip()}")
        print("\n[SUCCESS] API is working correctly!")
    except Exception as e:
        print(f"\n[FAIL] API call failed: {e}")
        print("   -> Your key may be invalid or have no quota remaining.")
        print("   -> Check: https://aistudio.google.com/app/apikey")
