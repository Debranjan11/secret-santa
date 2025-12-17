from flask import Flask, render_template, request, jsonify
import random
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    admin_key = request.json.get("admin_key")
    if admin_key != os.getenv("ADMIN_KEY"):
        return jsonify({"error": "Unauthorized"}), 403
    
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

