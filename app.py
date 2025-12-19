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
import random
import re


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
    #parse request
    data = request.get_json() 
    if not data:
        return {"error": "Invalid request."}, 400 

    #rate limiting
    ip = request.remote_addr or "unknown"

    if is_rate_limited(ip):
        return {
        "error": "Too many requests. Please wait a minute and try again."
    }, 429
    
    #admin Key check
    admin_key = data.get("admin_key", "")
    real_key = os.environ.get("ADMIN_KEY", "")

    if not secure_compare(admin_key, real_key):
        return {
        "error": "Unauthorized request."
    }, 403

    #extract participants
    participants = data.get("participants", [])
    error = validate_participants(participants)
    if error:
        return {"error": error}, 400
    
    if len(participants) < 2:
        return {"error": "At least two participants are required."}, 400

    #main logic
    try:
        assignments = generate_assignments(participants)

        for giver, receiver in assignments:
            send_email(
                giver["email"],
                giver["name"],
                receiver["name"]
            )

    except Exception:
        # Do NOT expose internal errors
        return {
            "error": "Something went wrong while sending emails. Please try again."
        }, 500

    #clear sensitive data
    participants.clear()

    #success message
    return jsonify({"message": "🎁 Secret Santa emails sent!"})

def generate_assignments(participants):
    if len(participants) < 2:
        raise ValueError("Not enough participants")

    givers = participants[:]
    receivers = participants[:]

    for _ in range(10):  # limited attempts to avoid infinite loop
        random.shuffle(receivers)
        if all(g["email"] != r["email"] for g, r in zip(givers, receivers)):
            return list(zip(givers, receivers))

    raise RuntimeError("Failed to generate valid Secret Santa assignments")


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

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def validate_participants(participants):
    if not isinstance(participants, list):
        return "Participants must be a list."

    if len(participants) < 2:
        return "At least two participants are required."

    seen_emails = set()

    for i, p in enumerate(participants):
        if not isinstance(p, dict):
            return f"Participant #{i+1} is invalid."

        name = p.get("name", "").strip()
        email = p.get("email", "").strip().lower()

        if not name:
            return f"Participant #{i+1} name is required."

        if not email or not EMAIL_REGEX.match(email):
            return f"Participant #{i+1} has an invalid email."

        if email in seen_emails:
            return "Duplicate emails are not allowed."

        seen_emails.add(email)

    return None  # valid

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

