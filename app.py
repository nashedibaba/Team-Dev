"""
app.py — AI Group Project Manager
Uses: Groq (LLM) + Hindsight Cloud (Memory)
Run: pip install flask groq requests
     python app.py
"""

from flask import Flask, request, jsonify, send_from_directory
import requests
from groq import Groq

app = Flask(__name__)

# ─── API KEYS ─────────────────────────────────────────────────────────────────
HINDSIGHT_API_KEY   = "hsk_f0f5db2a3bfe6969e850731d76696a10_06fa2795d116581d"
HINDSIGHT_MEMORY_ID = "group project manager"
GROQ_API_KEY        = "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"
HINDSIGHT_BASE_URL  = "https://api.hindsight.vectorize.io/v1"

groq_client = Groq(api_key=GROQ_API_KEY)

# ─── HINDSIGHT HELPERS ────────────────────────────────────────────────────────
HEADERS = {
    "Authorization": f"Bearer {HINDSIGHT_API_KEY}",
    "Content-Type": "application/json"
}

def retain_memory(text, project_id):
    """Save a message into Hindsight memory."""
    try:
        requests.post(
            f"{HINDSIGHT_BASE_URL}/memories/{HINDSIGHT_MEMORY_ID}/retain",
            headers=HEADERS,
            json={"text": text, "metadata": {"project_id": project_id}},
            timeout=5
        )
    except Exception as e:
        print(f"[Hindsight retain error] {e}")

def recall_memory(query, project_id):
    """Retrieve relevant past memories for this project."""
    try:
        response = requests.post(
            f"{HINDSIGHT_BASE_URL}/memories/{HINDSIGHT_MEMORY_ID}/recall",
            headers=HEADERS,
            json={"query": query, "metadata": {"project_id": project_id}, "limit": 5},
            timeout=5
        )
        result = response.json()
        if "memories" in result:
            return "\n".join(m.get("text", "") for m in result["memories"])
    except Exception as e:
        print(f"[Hindsight recall error] {e}")
    return ""

# ─── ROUTES ───────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data         = request.json
    user_message = data.get("message", "").strip()
    project_id   = data.get("project_id", "team1")
    member_name  = data.get("member_name", "Team Member")

    if not user_message:
        return jsonify({"reply": "Please send a message."}), 400

    # 1. Save incoming message to memory
    retain_memory(f"{member_name} said: {user_message}", project_id)

    # 2. Recall relevant past context
    memory_text = recall_memory(user_message, project_id)

    # 3. Build system prompt with memories injected
    system_prompt = f"""You are an AI Group Project Manager that remembers everything about the team.
You help students track tasks, decisions, deadlines and team progress.

Here are your memories about this project:
{memory_text if memory_text else "No previous memories yet — this is a fresh project!"}

Based on these memories, help the team member with their question.
Be specific about who was assigned what task and what decisions were made."""

    # 4. Call Groq
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": f"[{member_name}]: {user_message}"}
            ]
        )
        reply = response.choices[0].message.content
    except Exception as e:
        print(f"[Groq error] {e}")
        return jsonify({"reply": f"AI error: {str(e)}"}), 500

    # 5. Save AI reply to memory
    retain_memory(f"AI replied to {member_name}: {reply}", project_id)

    return jsonify({"reply": reply})

# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("  ProjectAI is running!")
    print("  Open: http://localhost:5000")
    print("=" * 50)
    app.run(debug=True)
