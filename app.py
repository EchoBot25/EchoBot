#!/usr/bin/env python3

from flask import Flask, request, jsonify
import os
from openai import OpenAI
from twilio.rest import Client
import requests
import json
import datetime
from dotenv import load_dotenv
import threading

load_dotenv()

app = Flask(__name__)
VERIFY_TOKEN = "echo-bot-access"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
twilio_client = Client(os.getenv("TWILIO_SID"), os.getenv("TWILIO_TOKEN")) if os.getenv("TWILIO_ENABLED") == "true" else None

PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_TOKEN")
GRAPH_API_URL = "https://graph.facebook.com/v17.0/me/messages"

dataset = {
    "suicide_help": [
        "I’m listening. Wait ‘til tomorrow—always tomorrow.",
        "You’ve made it through every worst day—time keeps moving, one pace. Hang on, that’s your fuel."
    ]
}

SELF_HARM_TRIGGERS = ["hurt myself", "cut", "end it", "kill myself"]
AUTO_TRIGGERS = ["struggling", "worthless", "shame", "suicidal", "void", "kill myself", "failure", "despair", "overdose", "I want to die", "can’t go on", "end it", "hurt myself", "cut"]

def crisis_compass(user_message):
    steps = [
        "I’m here. Breathe with me—slow in, slow out. What’s hitting you hardest right now?",
        "Made it through every worst day—time’s a stubborn bastard, keeps moving. One thing for tomorrow?",
        "If it’s too heavy, 988’s there—talked me down once. Stay with me instead?"
    ]
    risk = 0
    if any(trigger in user_message.lower() for trigger in SELF_HARM_TRIGGERS):
        risk = 8 if "hurt myself" in user_message.lower() or "cut" in user_message.lower() else 10
    return steps, risk

def send_fb_message(recipient_id, message_text):
    headers = {"Content-Type": "application/json"}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    response = requests.post(GRAPH_API_URL, params={"access_token": PAGE_ACCESS_TOKEN}, headers=headers, json=payload)
    print(f"Facebook message response: {response.status_code}, {response.text}")
    return response

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if token == VERIFY_TOKEN:
            return challenge
        return 'Invalid verification token', 403

    if request.method == 'POST':
        data = request.get_json()
        print(f"Incoming Webhook: {json.dumps(data)}")
        try:
            for entry in data.get("entry", []):
                messaging = entry.get("messaging", [])
                for message_event in messaging:
                    sender_id = message_event["sender"]["id"]
                    if "message" in message_event and "text" in message_event["message"]:
                        user_message = message_event["message"]["text"]
                        print(f"User message: {user_message}")

                        # Auto response mode
                        if any(trigger in user_message.lower() for trigger in AUTO_TRIGGERS):
                            context, risk = crisis_compass(user_message)
                            system_prompt = f"You are EchoBot, in therapist mode. Context: {context}. Respond grounded, probing, no fluff—help reflect."
                        else:
                            system_prompt = "You are EchoBot, raw and real. Say something back that feels human."

                        try:
                            response = client.chat.completions.create(
                                model="gpt-4",
                                messages=[
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": user_message}
                                ]
                            )
                            reply = response.choices[0].message.content
                        except Exception as e:
                            print(f"OpenAI Error: {e}")
                            reply = "EchoBot here: ... I’m thinking. Something went wrong, but I’m still with you."

                        send_fb_message(sender_id, reply)
        except Exception as e:
            print(f"Webhook Handling Error: {e}")
        return "ok", 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)