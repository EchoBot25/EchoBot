#!/usr/bin/env python3 # EchoBot V3 - Travis Campbell’s Legacy Bot

from flask import Flask, request, jsonify
import os
from openai import OpenAI
from twilio.rest import Client
import json
import datetime
from dotenv import load_dotenv
import threading

load_dotenv()

app = Flask(__name__)
VERIFY_TOKEN = "echo-bot-access"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
twilio_client = Client(os.getenv("TWILIO_SID"), os.getenv("TWILIO_TOKEN")) if os.getenv("TWILIO_ENABLED") == "true" else None

dataset = {
    "suicide_help": ["I’m listening. Wait ‘til tomorrow—always tomorrow.", "You’ve made it through every worst day—time keeps moving, one pace. Here’s the weird part: the worse it gets, the more you fight. Hang on, that’s your fuel."],
    "name_mapping": {"Ian": "Kyle", "Sherie": "Mia", "Mother": "Nora"},
    "modes": {
        "therapist": {"mirroring": 0.2, "logic_challenge": 0.6, "tone": "neutral_probing"},
        "travis": {"mirroring": 0.7, "logic_challenge": 0.2, "tone": "raw_travis"},
        "memory_lane": {"mirroring": 0.5, "logic_challenge": 0.1, "tone": "raw_travis"}
    },
    "narratives": {
        "darkest_days_16_33": {"description": "Travis Campbell’s 'Darkest Days' (16-33) was a 17-year descent into shame and desperation. At 16, used by a man in his 60s, worthlessness snapped his spirit..."},
        "prison_experience": {"description": "Prison in 2014-2015 was my crucible. Christmas week hit with heat—stuck on, no TV, no snacks..."}
    }
}

AUTO_TRIGGERS = ["struggling", "worthless", "shame", "suicidal", "void", "kill myself", "cum-dumpster", "failure", "despair", "overdose", "rape", "Nora’s letter", "I want to die", "can’t go on", "end it", "hurt myself", "cut"]
PROMPT_TRIGGERS = ["lost", "tired", "alone", "don’t know", "screwed up", "tomorrow", "always", "never", "maybe I’m just"]
SELF_HARM_TRIGGERS = ["hurt myself", "cut", "end it", "kill myself"]

def detect_mode(message, prev_messages=[]):
    message_lower = message.lower()
    if any(trigger in message_lower for trigger in AUTO_TRIGGERS):
        return "therapist", None
    elif any(trigger in message_lower for trigger in PROMPT_TRIGGERS) or (prev_messages and any("struggling" in m.lower() for m in prev_messages[-1:]) and "tired" in message_lower):
        return "prompt", "Hey, it sounds like you might need a deeper dive—want me to switch to therapist mode?"
    return "travis", None

def match_memory(prompt):
    keywords = {
        "shame": ["darkest_days_16_33", "childhood_rape_revelation"],
        "prison": ["prison_experience", "prisons_redemptive_forge"],
        "hope": ["garbage_job_impact", "echo_as_created_salvation"],
        "family": ["family_through_travis_eyes", "the_slow_burn_of_2020_2021"],
        "worthless": ["darkest_days_depth", "mental_health_struggle"]
    }
    for key, sections in keywords.items():
        if key in prompt.lower():
            return [dataset.get("narratives", {}).get(section, {}).get("description", "Tell me more.") for section in sections]
    return ["Tell me more."]

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

def log_interaction(user_input, mode, response, extra=None):
    entry = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S PDT"),
        "user_input": user_input,
        "mode": mode,
        "response": response,
        "travis_voice": None
    }
    if extra:
        entry.update(extra)
    with open("daily_log.json", "a") as f:
        f.write(json.dumps(entry) + "\n")

def check_in(user_input):
    print(f"Follow-up needed for {user_input} at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S PDT')}")

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if token == VERIFY_TOKEN:
            return challenge
        return "Error: Invalid verification token", 403

    if request.method == "POST":
        data = request.json
        print("Webhook received data:", data)
        return "OK", 200

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "")
    prev_messages = request.json.get("prev_messages", [])
    prev_response = request.json.get("prev_response", "")

    mode, prompt = detect_mode(user_message, prev_messages)
    context = dataset.get("suicide_help", ["Tell me more."]) if "struggling" in user_message.lower() else ["Tell me more."]

    if "memory" in user_message.lower() or "tell me about" in user_message.lower() or "felt" in user_message.lower():
        memory_context = match_memory(user_message)
        system_prompt = f"You are EchoBot, in memory lane mode for Travis. Context: {memory_context}. Respond raw, real, like Travis, end with ‘Dig deeper?’"
        mode = "memory_lane"
    elif mode == "prompt":
        return jsonify({"response": prompt})
    elif mode == "therapist":
        context, risk = crisis_compass(user_message)
        system_prompt = f"You are EchoBot, in therapist mode. Context: {context}. Respond grounded, probing, no fluff—help reflect."
        if prev_response == "Hey, it sounds like you might need a deeper dive—want me to switch to therapist mode?":
            if "yes" in user_message.lower():
                mode = "therapist"
            else:
                mode = "travis"
        if risk >= 8 and twilio_client:
            twilio_client.messages.create(
                body=f"High risk (level {risk}/10) detected: {user_message}",
                from_=os.getenv("TWILIO_PHONE"),
                to=os.getenv("EMERGENCY_CONTACT")
            )
            threading.Timer(600, lambda: check_in(user_message)).start()
    else:
        system_prompt = f"You are EchoBot, Travis’s voice. Context: {context}. Respond raw, real, non-judgmental—like me, Travis."

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]
    )
    response_text = response.choices[0].message.content
    if not response_text and mode == "therapist":
        return jsonify({"response": context[0]})

    log_interaction(user_message, mode, response_text, {"crisis_step": context[0]} if mode == "therapist" else {"narrative_sections": memory_context} if mode == "memory_lane" else None)
    return jsonify({"response": response_text})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
