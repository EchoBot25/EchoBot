
import os
import requests
from flask import Flask, request

app = Flask(__name__)

VERIFY_TOKEN = "echo-bot-access"
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

@app.route("/", methods=["GET"])
def home():
    return "EchoBot is alive!"

@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge"), 200
    return "Verification token mismatch", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if data["object"] == "page":
        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:
                if messaging_event.get("message"):
                    sender_id = messaging_event["sender"]["id"]
                    message_text = messaging_event["message"].get("text", "")
                    reply_text = get_openai_response(message_text)
                    send_message(sender_id, reply_text)
    return "ok", 200

def get_openai_response(user_input):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    json_data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are EchoBot, a supportive AI trained to help people in emotional distress."},
            {"role": "user", "content": user_input}
        ]
    }
    try:
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=json_data)
        response_data = response.json()
        return response_data["choices"][0]["message"]["content"]
    except Exception as e:
        return "I'm having trouble responding right now. Please try again soon."

def send_message(recipient_id, message_text):
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": f"EchoBot here: {message_text}"}
    }
    params = {
        "access_token": PAGE_ACCESS_TOKEN
    }
    requests.post("https://graph.facebook.com/v18.0/me/messages", headers=headers, params=params, json=data)

if __name__ == "__main__":
    app.run(debug=True)
