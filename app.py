
import os
import requests
from flask import Flask, request

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "echo-bot-access")
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        return "Verification failed", 403

    if request.method == "POST":
        data = request.get_json()
        if data["object"] == "page":
            for entry in data["entry"]:
                for messaging_event in entry.get("messaging", []):
                    sender_id = messaging_event["sender"]["id"]
                    if "message" in messaging_event:
                        message_text = messaging_event["message"].get("text")
                        if message_text:
                            send_message(sender_id, f"EchoBot here: {message_text}")
        return "EVENT_RECEIVED", 200
    return "Not Found", 404

def send_message(recipient_id, message_text):
    headers = {"Content-Type": "application/json"}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    response = requests.post(url, headers=headers, json=payload)
    print("Sent message:", response.text)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
