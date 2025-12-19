from flask import Flask, render_template, request, jsonify
import random
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import time
from collections import defaultdict
from flask import request
import hmac
import os

RATE_LIMIT = 5           # max requests
RATE_WINDOW = 60         # per 60 seconds

request_log = defaultdict(list)

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

def secure_compare(a, b):
    return hmac.compare_digest(a.encode(), b.encode())


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()  
    
    ip = request.remote_addr or "unknown"

    if is_rate_limited(ip):
        return {
        "error": "Too many requests. Please wait a minute and try again."
    }, 429
    
    admin_key = data.get("admin_key", "")
    real_key = os.environ.get("ADMIN_KEY", "")

    if not secure_compare(admin_key, real_key):
        return {
        "error": "Unauthorized request."
    }, 403

    
    participants = request.json.get("participants")

    if not participants or len(participants) < 2:
        return jsonify({"error": "At least 2 participants required"}), 400

    names = [p["name"] for p in participants]
    shuffled = names[:]

    while True:
        random.shuffle(shuffled)
        if all(names[i] != shuffled[i] for i in range(len(names))):
            break

    for i, p in enumerate(participants):
        send_email(p["email"], p["name"], shuffled[i])

    return jsonify({"message": "🎁 Secret Santa emails sent!"})

def send_email(to_email, name, assigned):
    message = Mail(
        from_email=os.getenv("FROM_EMAIL"),
        to_emails=to_email,
        subject="🎄 Your Secret Santa Assignment",
        plain_text_content=f"""
Hi {name},

🎁 You are the Secret Santa for: {assigned}

Keep it a secret 🤫
Happy gifting!
"""
    )

    sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
    sg.send(message)

def is_rate_limited(ip):
    now = time.time()
    window = request_log[ip]

    # keep only recent requests
    request_log[ip] = [t for t in window if now - t < RATE_WINDOW]

    if len(request_log[ip]) >= RATE_LIMIT:
        return True

    request_log[ip].append(now)
    return False


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

