from flask import Flask, request, jsonify, render_template
import requests
import os
from flask_cors import CORS
from dotenv import load_dotenv
import time

load_dotenv()

app = Flask(__name__)
CORS(app)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

@app.route('/')
def index():
    return render_template('frontend.html')

@app.route("/debate", methods=["POST"])
def debate():
    if not OPENROUTER_API_KEY:
        return jsonify({"error": "Server misconfigured: missing API key."}), 500

    data = request.json
    user_statement = data.get("statement")
    persona = data.get("persona", "default")
    history = data.get("history", [])

    if not user_statement:
        return jsonify({"error": "No statement provided"}), 400

    persona_prompt = {
        "default": "You're an expert debater who always takes the opposing side with strong arguments in 3-4 lines.",
        "sarcastic": "You're a sarcastic debater who mocks the user's stance while arguing the opposite side cleverly in 3-4 lines.",
        "serious": "You're a professional debater who calmly and seriously argues against the user's point with credible logic in 3-4 lines.",
        "casual": "You're a chill and witty debater who casually argues against the user's opinion like a funny smart friend in 3-4 lines."
    }.get(persona)


    prompt = f"""
User: "{user_statement}"

You are EchoVice, a confident and intelligent AI debater.
Always argue against the user's opinion—cleverly, concisely, and with strong logic.
Use real facts and sharp reasoning.
⚠️ Keep it short: 3-4 strong sentences, no more.
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    messages = [{"role": "system", "content": persona_prompt}]
    for msg in history:
        role = "user" if msg.get("role") == "user" else "assistant"
        messages.append({"role": role, "content": msg.get("content")})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "mistralai/devstral-2512:free",
        "messages": messages
    }

    retries = 3
    delay = 2
    for attempt in range(retries):
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=15
            )

            if response.status_code == 200:
                reply = response.json()["choices"][0]["message"]["content"]
                return jsonify({"response": reply})

            elif response.status_code == 429:
                time.sleep(delay)
                delay *= 2

            else:
                return jsonify({
                    "error": f"API Error: {response.status_code} - {response.text}"
                }), response.status_code

        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
            else:
                return jsonify({"error": "The request timed out. Please try again later."}), 408

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return jsonify({"error": "Failed after multiple attempts. Please wait and try again."}), 500

if __name__ == "__main__":
    app.run(debug=False)

