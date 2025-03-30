#!/usr/bin/env python3

from flask import Flask, request, jsonify
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

VERIFY_TOKEN = "echo-bot-access"
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        token_sent = request.args.get("hub.verify_token")
        if token_sent == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Invalid verification token", 403

    if request.method == 'POST':
        output = request.get_json()
        for entry in output.get("entry", []):
            messaging = entry.get("messaging", [])
            for message_event in messaging:
                sender_id = message_event["sender"]["id"]
                if message_event.get("message"):
                    user_message = message_event["message"].get("text")
                    if user_message:
                        reply = "EchoBot here: " + user_message
                        send_message(sender_id, reply)
        return "Message Processed", 200

def send_message(recipient_id, message_text):
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    url = f"https://graph.facebook.com/v17.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    print("Send API response:", response.status_code, response.text)
    return response.status_code

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=5000)