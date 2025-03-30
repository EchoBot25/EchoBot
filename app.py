
#!/usr/bin/env python3

from flask import Flask, request, jsonify
import os
from openai import OpenAI
from twilio.rest import Client
from dotenv import load_dotenv
import json
import datetime
import threading

load_dotenv()

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
twilio_client = Client(os.getenv("TWILIO_SID"), os.getenv("TWILIO_TOKEN")) if os.getenv("TWILIO_ENABLED") == "true" else None
VERIFY_TOKEN = "echo-bot-access"

# In-memory data for response simulation
dataset = {
    "suicide_help": ["I’m listening. Wait ‘til tomorrow—always tomorrow.", "You’ve made it through every worst day—time keeps moving, one pace. Here’s the weird part: the worse it gets, the more you fight. Hang on, that’s your fuel."]
}

SELF_HARM_TRIGGERS = ["hurt myself", "cut", "end it", "kill myself"]

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if token == VERIFY_TOKEN:
            return challenge
        return 'Error: Invalid verification token', 403

    if request.method == 'POST':
        data = request.json
        print("Webhook received data:", data)

        if data.get("object") == "page":
            for entry in data.get("entry", []):
                for messaging_event in entry.get("messaging", []):
                    sender_id = messaging_event["sender"]["id"]
                    if "message" in messaging_event:
                        message_text = messaging_event["message"].get("text", "")
                        response_text = handle_message(message_text)
                        send_message(sender_id, response_text)
        return "EVENT_RECEIVED", 200

    return "Invalid request", 400

def handle_message(message):
    if any(trigger in message.lower() for trigger in SELF_HARM_TRIGGERS):
        return dataset["suicide_help"][0]
    return "I'm here. What would you like to talk about?"

def send_message(recipient_id, message_text):
    import requests
    PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    response = requests.post(url, headers=headers, json=payload)
    print("Sent message:", response.text)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
