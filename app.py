
from flask import Flask, request
import openai
import os

app = Flask(__name__)

VERIFY_TOKEN = "echo-bot-access"

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        token_sent = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if token_sent == VERIFY_TOKEN:
            return str(challenge)
        return "Invalid verification token", 403
    elif request.method == "POST":
        output = request.get_json()
        if output and "entry" in output:
            for entry in output["entry"]:
                messaging = entry.get("messaging", [])
                for message_event in messaging:
                    sender_id = message_event["sender"]["id"]
                    if "message" in message_event and "text" in message_event["message"]:
                        user_message = message_event["message"]["text"]
                        response_text = f"EchoBot here: {user_message}"
                        print(f"Responding to {sender_id}: {response_text}")
        return "Message Processed", 200

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
