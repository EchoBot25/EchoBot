
import os
from flask import Flask, request
import json

app = Flask(__name__)

VERIFY_TOKEN = "echo-bot-access"

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        else:
            return "Verification failed", 403

    elif request.method == "POST":
        data = request.get_json()
        print("Received webhook event:", json.dumps(data, indent=2))

        if data["object"] == "page":
            for entry in data["entry"]:
                for event in entry.get("messaging", []):
                    sender_id = event["sender"]["id"]
                    message_text = event.get("message", {}).get("text")

                    if message_text:
                        print(f"Received message from {sender_id}: {message_text}")
                        # Simulate reply (replace this with OpenAI call later)
                        send_message(sender_id, f"EchoBot received: {message_text}")
        return "EVENT_RECEIVED", 200

def send_message(recipient_id, text):
    import requests
    PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
    if not PAGE_ACCESS_TOKEN:
        print("PAGE_ACCESS_TOKEN not set in environment variables.")
        return

    url = "https://graph.facebook.com/v17.0/me/messages"
    headers = {"Content-Type": "application/json"}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text},
        "messaging_type": "RESPONSE"
    }
    params = {"access_token": PAGE_ACCESS_TOKEN}

    response = requests.post(url, headers=headers, params=params, json=payload)
    print("Sent message response:", response.status_code, response.text)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
