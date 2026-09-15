from app import get_gemini_api_key

key = get_gemini_api_key()
print("Retrieved key length:", len(key) if key else 0)
if key and len(key) >= 15:
    print("SUCCESS: Secret Manager key successfully loaded in GCP Compute Engine VM!")
else:
    print("FAILED: Could not retrieve key")
