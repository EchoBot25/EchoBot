
from flask import Flask, request

app = Flask(__name__)

VERIFY_TOKEN = "echo-bot-access"

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("WEBHOOK VERIFIED")
            return challenge, 200
        else:
            return "Verification token mismatch", 403

    elif request.method == "POST":
        data = request.json
        print("Incoming data:", data)

        # Parse the message from Facebook
        try:
            for entry in data.get("entry", []):
                for msg_event in entry.get("messaging", []):
                    sender_id = msg_event["sender"]["id"]
                    message_text = msg_event["message"]["text"]
                    print(f"Received message from {sender_id}: {message_text}")

                    # Simulate a reply (actual call to FB Messenger Send API is omitted for now)
                    print(f"Would send: 'EchoBot here: I got your message!' to {sender_id}")
        except Exception as e:
            print("Error processing message:", str(e))

        return "EVENT_RECEIVED", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
