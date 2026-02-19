from flask import Flask, request, jsonify
from combat_engine import CombatEngine

app = Flask(__name__)

game_state = {
    "player": {
    "name": "Player",
    "hp": 30,
    "ac": 14,
    "attack_bonus": 5,
    "damage": (1, 8),
    "initiative": 0,
    "status_effects": [],
    "poison_on_hit": True
},

    "enemies": [
        {
            "id": 1,
            "name": "Goblin A",
            "hp": 20,
            "ac": 12,
            "attack_bonus": 4,
            "damage": (1, 6),
            "initiative": 0,
            "status_effects": []
        },
        {
            "id": 2,
            "name": "Goblin B",
            "hp": 18,
            "ac": 12,
            "attack_bonus": 4,
            "damage": (1, 6),
            "initiative": 0,
            "status_effects": []
        }
    ],
    "turn_order": [],
    "current_turn_index": 0
}


@app.route("/action", methods=["POST"])
def action():
    data = request.json or {}
    target_id = data.get("target_id")

    engine = CombatEngine(game_state)

    if not game_state["turn_order"]:
        engine.roll_initiative()

    actor = engine.get_current_actor()

    # ================= PLAYER =================
    if actor["type"] == "player":

        if target_id is None:
            return jsonify({
                "turn": "player",
                "player_hp": game_state["player"]["hp"],
                "enemies": game_state["enemies"]
            })

        event = engine.resolve_player_attack(target_id)

        for enemy in list(game_state["enemies"]):
            if enemy["hp"] <= 0:
                engine.remove_actor_from_turn_order("enemy", enemy["id"])

        game_state["enemies"] = [e for e in game_state["enemies"] if e["hp"] > 0]

        engine.next_turn()

        return jsonify({
            "actor": "player",
            "event": event,
            "player_hp": game_state["player"]["hp"],
            "enemies": game_state["enemies"]
        })

    # ================= ENEMY =================
    else:
        event = engine.resolve_enemy_turn()

        if game_state["player"]["hp"] <= 0:
            engine.remove_actor_from_turn_order("player")
            return jsonify({
                "actor": event.get("attacker", "enemy"),
                "event": event,
                "message": "You have been defeated.",
                "player_hp": 0,
                "enemies": game_state["enemies"]
            })

        engine.next_turn()

        return jsonify({
            "actor": event.get("attacker", "enemy"),
            "event": event,
            "player_hp": game_state["player"]["hp"],
            "enemies": game_state["enemies"]
        })


if __name__ == "__main__":
    app.run(debug=True)
