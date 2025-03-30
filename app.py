
#!/usr/bin/env python3

from flask import Flask, request, jsonify
import os
import requests
from openai import OpenAI
from dotenv import load_dotenv
import datetime
import json

load_dotenv()

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

VERIFY_TOKEN = "echo-bot-access"
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")

dataset = {
    "suicide_help": ["I’m listening. Wait ‘til tomorrow—always tomorrow.", 
                     "You’ve made it through every worst day—time keeps moving, one pace. Hang on, that’s your fuel."]
}

SELF_HARM_TRIGGERS = ["hurt myself", "cut", "end it", "kill myself"]

def crisis_compass(user_message):
    steps = [
        "I’m here. Breathe with me—slow in, slow out. What’s hitting you hardest right now?",
        "Made it through every worst day—time’s a stubborn bastard, keeps moving. One thing for tomorrow?",
        "If it’s too heavy, 988’s there—talked me down once. Stay with me instead?"
    ]
    risk = 0
    if any(trigger in user_message.lower() for trigger in SELF_HARM_TRIGGERS):
        risk = 10
    return steps, risk

def send_facebook_message(recipient_id, message_text):
    headers = {"Content-Type": "application/json"}
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    response = requests.post(
        f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}",
        headers=headers,
        json=data
    )
    return response.status_code, response.text

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if token == VERIFY_TOKEN:
            return challenge, 200
        return "Verification token mismatch", 403

    if request.method == "POST":
        payload = request.get_json()
        for entry in payload.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                sender_id = messaging_event["sender"]["id"]
                if "message" in messaging_event and "text" in messaging_event["message"]:
                    user_message = messaging_event["message"]["text"]
                    context, risk = crisis_compass(user_message)
                    system_prompt = f"You are EchoBot, a brutally honest but caring therapist. Context: {context}. Respond concisely but authentically."
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_message}
                        ]
                    )
                    reply = response.choices[0].message.content.strip()
                    send_facebook_message(sender_id, reply)
        return "OK", 200

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "")
    context, _ = crisis_compass(user_message)
    system_prompt = f"You are EchoBot, a brutally honest but caring therapist. Context: {context}. Respond concisely but authentically."
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    )
    reply = response.choices[0].message.content.strip()
    return jsonify({"response": reply})

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
