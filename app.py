
import os
import requests
from flask import Flask, request

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "echo-bot-access")

def send_message(recipient_id, message_text):
    print(f"Sending message to {recipient_id}: {message_text}")
    params = {"access_token": PAGE_ACCESS_TOKEN}
    headers = {"Content-Type": "application/json"}
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    response = requests.post(
        "https://graph.facebook.com/v12.0/me/messages",
        params=params,
        headers=headers,
        json=data
    )
    print("Facebook API response:", response.status_code, response.text)

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge"), 200
        return "Verification token mismatch", 403

    if request.method == "POST":
        data = request.get_json()
        print("Received webhook event:", data)

        if data["object"] == "page":
            for entry in data["entry"]:
                for messaging_event in entry.get("messaging", []):
                    print("Message event:", messaging_event)
                    if messaging_event.get("message"):
                        sender_id = messaging_event["sender"]["id"]
                        message_text = messaging_event["message"].get("text", "")
                        send_message(sender_id, f"EchoBot here: {message_text}")

        return "OK", 200

if __name__ == "__main__":
    app.run(debug=True)
