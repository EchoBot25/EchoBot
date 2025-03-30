
#!/usr/bin/env python3

from flask import Flask, request, jsonify
import os
from openai import OpenAI
from twilio.rest import Client
import json
import datetime
from dotenv import load_dotenv
import threading

load_dotenv()
app = Flask(__name__)

VERIFY_TOKEN = "echo-bot-access"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
twilio_client = Client(os.getenv("TWILIO_SID"), os.getenv("TWILIO_TOKEN")) if os.getenv("TWILIO_ENABLED") == "true" else None

dataset = {
    "suicide_help": ["I’m listening. Wait ‘til tomorrow—always tomorrow.", "You’ve made it through every worst day—time keeps moving, one pace. The worse it gets, the more you fight. Hang on, that’s your fuel."],
    "name_mapping": {"Ian": "Kyle", "Sherie": "Mia", "Mother": "Nora"},
    "modes": {
        "therapist": {"mirroring": 0.2, "logic_challenge": 0.6, "tone": "neutral_probing"},
        "travis": {"mirroring": 0.7, "logic_challenge": 0.2, "tone": "raw_travis"},
        "memory_lane": {"mirroring": 0.5, "logic_challenge": 0.1, "tone": "raw_travis"}
    },
    "narratives": {
        "darkest_days_16_33": {"description": "Travis Campbell’s 'Darkest Days' (16-33) was a 17-year descent into shame and desperation..."},
        "prison_experience": {"description": "Prison in 2014-2015 was my crucible. Christmas week hit with heat—stuck on, no TV, no snacks..."}
    }
}

AUTO_TRIGGERS = ["struggling", "worthless", "shame", "suicidal", "void", "kill myself", "failure", "despair", "overdose", "rape", "I want to die", "can’t go on", "end it", "hurt myself", "cut"]
PROMPT_TRIGGERS = ["lost", "tired", "alone", "don’t know", "screwed up", "tomorrow", "always", "never"]
SELF_HARM_TRIGGERS = ["hurt myself", "cut", "end it", "kill myself"]

def detect_mode(message, prev_messages=[]):
    message_lower = message.lower()
    if any(trigger in message_lower for trigger in AUTO_TRIGGERS):
        return "therapist", None
    elif any(trigger in message_lower for trigger in PROMPT_TRIGGERS):
        return "prompt", "Sounds like something deeper is going on. Want me to switch to therapist mode?"
    return "travis", None

def match_memory(prompt):
    keywords = {
        "shame": ["darkest_days_16_33"],
        "prison": ["prison_experience"]
    }
    for key, sections in keywords.items():
        if key in prompt.lower():
            return [dataset["narratives"].get(section, {}).get("description", "") for section in sections]
    return ["Tell me more."]

def crisis_compass(user_message):
    steps = [
        "I’m here. Breathe with me—slow in, slow out. What’s hitting you hardest right now?",
        "Time keeps moving. What’s one thing to hold onto until tomorrow?",
        "Too much? 988 helped me once. Want to stay here with me a minute?"
    ]
    risk = 0
    if any(trigger in user_message.lower() for trigger in SELF_HARM_TRIGGERS):
        risk = 10
    return steps, risk

@app.route("/webhook", methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if token == VERIFY_TOKEN:
            return challenge, 200
        return "Verification token mismatch", 403

    if request.method == 'POST':
        try:
            data = request.json
            for entry in data.get("entry", []):
                for messaging_event in entry.get("messaging", []):
                    sender_id = messaging_event["sender"]["id"]
                    if "message" in messaging_event:
                        user_message = messaging_event["message"].get("text", "")
                        response_text = handle_message(user_message)
                        send_message(sender_id, response_text)
            return "ok", 200
        except Exception as e:
            print("Error in webhook POST:", str(e))
            return "error", 500

def handle_message(user_message):
    try:
        mode, prompt = detect_mode(user_message)
        if mode == "prompt":
            return prompt
        elif mode == "therapist":
            context, risk = crisis_compass(user_message)
            system_prompt = f"You are EchoBot, therapist mode. Context: {context}. Respond grounded, probing."
            if risk >= 8 and twilio_client:
                try:
                    twilio_client.messages.create(
                        body=f"High risk ({risk}/10): {user_message}",
                        from_=os.getenv("TWILIO_PHONE"),
                        to=os.getenv("EMERGENCY_CONTACT")
                    )
                except Exception as err:
                    print("Twilio error:", err)
        elif "memory" in user_message.lower():
            context = match_memory(user_message)
            system_prompt = f"You are EchoBot in memory lane mode. Context: {context}. Respond raw like Travis. End with 'Dig deeper?'"
        else:
            context = ["Tell me more."]
            system_prompt = f"You are EchoBot, raw Travis voice. Context: {context}"

        completion = client.chat.completions.create(
            model="grok-beta",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print("AI fallback triggered:", str(e))
        return "I'm here. Something glitched, but I won’t leave you hanging."

def send_message(recipient_id, message_text):
    import requests
    params = {
        "access_token": os.getenv("PAGE_ACCESS_TOKEN")
    }
    headers = {
        "Content-Type": "application/json"
    }
    body = {
        "recipient": {"id": recipient_id},
        "message": {"text": f"EchoBot here: {message_text}"}
    }
    r = requests.post("https://graph.facebook.com/v17.0/me/messages", params=params, headers=headers, json=body)
    print("Sent message:", r.status_code, r.text)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
