from flask import Flask, request, jsonify
import requests
from rag import load_rule_chunks, build_index, retrieve
import json

app = Flask(__name__)
import random

game_state = {
    "player_hp": 30,
    "enemy_hp": 20,
    "player_ac": 14,
    "enemy_ac": 12,
    "player_attack_bonus": 5,
    "enemy_attack_bonus": 4,
    "player_damage": (1, 8),  # 1d8
    "enemy_damage": (1, 6)    # 1d6
}
def roll_dice(num, sides):
    return sum(random.randint(1, sides) for _ in range(num))


chunks = load_rule_chunks()
index = build_index(chunks)

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"

@app.route("/action", methods=["POST"])
def action():
    user_input = request.json["input"]
    attack_roll = random.randint(1, 20) + game_state["player_attack_bonus"]

    if attack_roll >= game_state["enemy_ac"]:
        damage = roll_dice(*game_state["player_damage"])
        game_state["enemy_hp"] -= damage
        player_result = f"You hit for {damage} damage."
    else:
        player_result = "You miss"
    # Retrieve relevant rules
    relevant_rules = retrieve(user_input, chunks, index, top_k=2)
    rules_context = "\n\n".join(relevant_rules)

    prompt = f"""
You are a strict Dungeons & Dragons dungeon master.

You MUST follow these rules exactly:

{rules_context}

You are NOT allowed to:
- Ask the player to roll dice
- Calculate damage
- Modify HP
- Change game state

You ONLY:
- Describe what the enemy attempts to do
- Choose enemy_action logically

Respond ONLY in valid JSON format:

{{
  "enemy_action": "attack | defend | wait",
  "narration": "Short narrative description"
}}

Player Action: {user_input}
"""


    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        }
    )

    raw_output = response.json()["response"]

    try:
        ai_data = json.loads(raw_output)
    except:
        ai_data = {
            "enemy_action": "wait",
            "narration": "The enemy hesitates."
        }

    
    if ai_data["enemy_action"] == "attack":
        enemy_roll = random.randint(1, 20) + game_state["enemy_attack_bonus"]

        if enemy_roll >= game_state["player_ac"]:
            damage = roll_dice(*game_state["enemy_damage"])
            game_state["player_hp"] -= damage
            enemy_result = f"Enemy hits for {damage} damage."
        else:
            enemy_result = "Enemy misses."
    else:
        enemy_result = "Enemy takes defensive stance."

    # -------------------------
    # 5️⃣ Return full state
    # -------------------------

    return jsonify({
        "narration": ai_data["narration"],
        "player_result": player_result,
        "enemy_result": enemy_result,
        "player_hp": game_state["player_hp"],
        "enemy_hp": game_state["enemy_hp"]
    })

if __name__ == "__main__":
    app.run(debug=True)
