#Just a helper to see what models are available with the current key

import os
import google.generativeai as genai
from dotenv import load_dotenv

# 1. Load the key
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ CRITICAL: No API Key found in .env")
else:
    print(f"🔑 Key found: {api_key[:5]}...{api_key[-5:]}")
    
    # 2. Configure Google
    genai.configure(api_key=api_key)
    
    print("\n🔍 ASKING GOOGLE: 'What models can I use?'")
    print("-" * 40)
    
    try:
        # 3. Get the list
        found_any = False
        for m in genai.list_models():
            # Filter for models that can chat
            if 'generateContent' in m.supported_generation_methods:
                print(f"✅ AVAILABLE: {m.name}")
                found_any = True
        
        if not found_any:
            print("⚠️  NO CHAT MODELS FOUND. This key might be restricted.")
            
    except Exception as e:
        print(f"❌ CONNECTION ERROR: {e}")
        print("Tip: If you are in Europe, your key might require 'Pay-As-You-Go' enabled in Google Cloud.")