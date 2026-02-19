# app.py

from flask import Flask, request, jsonify
from combat_engine import CombatEngine
import random

app = Flask(__name__)

# -----------------------------
# GAME STATE
# -----------------------------

game_state = {
    "round": 1,
    "player": {
        "name": "Player",
        "hp": 40,
        "max_hp": 40,
        "ac": 14,
        "attack_bonus": 5,
        "damage": (1, 8),
        "initiative": 0,
        "stats": {
            "str": 3,
            "acc": 2,
            "vit": 0,
            "arm": 0,
            "spd": 2
        },
        "buff": None,
        "debuff": None
    },
    "enemies": [
        {
            "id": 1,
            "name": "Goblin Warrior",
            "hp": 25,
            "max_hp": 25,
            "ac": 12,
            "attack_bonus": 4,
            "damage": (1, 6),
            "initiative": 0,
            "stats": {
                "str": 2,
                "acc": 1,
                "vit": 0,
                "arm": 0,
                "spd": 2
            },
            "buff": None,
            "debuff": None
        },
        {
            "id": 2,
            "name": "Goblin Shaman",
            "hp": 20,
            "max_hp": 20,
            "ac": 11,
            "attack_bonus": 3,
            "damage": (1, 4),
            "initiative": 0,
            "stats": {
                "str": 0,
                "acc": 2,
                "vit": 0,
                "arm": 0,
                "spd": 3
            },
            "buff": None,
            "debuff": None
        }
    ],
    "turn_order": [],
    "current_turn_index": 0,
    "combat_active": True,
    "log": []
}

# -----------------------------
# HELPER FUNCTIONS
# -----------------------------

def reset_combat():
    """Reset combat to initial state"""
    global game_state
    game_state = {
        "round": 1,
        "player": {
            "name": "Player",
            "hp": 40,
            "max_hp": 40,
            "ac": 14,
            "attack_bonus": 5,
            "damage": (1, 8),
            "initiative": 0,
            "stats": {
                "str": 3,
                "acc": 2,
                "vit": 0,
                "arm": 0,
                "spd": 2
            },
            "buff": None,
            "debuff": None
        },
        "enemies": [
            {
                "id": 1,
                "name": "Goblin Warrior",
                "hp": 25,
                "max_hp": 25,
                "ac": 12,
                "attack_bonus": 4,
                "damage": (1, 6),
                "initiative": 0,
                "stats": {
                    "str": 2,
                    "acc": 1,
                    "vit": 0,
                    "arm": 0,
                    "spd": 2
                },
                "buff": None,
                "debuff": None
            },
            {
                "id": 2,
                "name": "Goblin Shaman",
                "hp": 20,
                "max_hp": 20,
                "ac": 11,
                "attack_bonus": 3,
                "damage": (1, 4),
                "initiative": 0,
                "stats": {
                    "str": 0,
                    "acc": 2,
                    "vit": 0,
                    "arm": 0,
                    "spd": 3
                },
                "buff": None,
                "debuff": None
            }
        ],
        "turn_order": [],
        "current_turn_index": 0,
        "combat_active": True,
        "log": []
    }

def apply_enemy_ai(engine, enemy):
    """Simple AI for enemy turns"""
    # 30% chance to use special ability if available
    if random.random() < 0.3:
        abilities = {
            "Goblin Warrior": ["poison", "burn"],
            "Goblin Shaman": ["freeze", "stun"]
        }
        
        available = abilities.get(enemy["name"], [])
        if available:
            debuff_type = random.choice(available)
            
            # Try to apply debuff to player
            result = engine.apply_debuff(
                game_state["player"],
                debuff_type,
                duration=3,
                base=3 if debuff_type == "poison" else None,
                damage=4 if debuff_type in ["burn", "freeze"] else None
            )
            return result
    
    # Default to normal attack
    return []

# -----------------------------
# ROUTES
# -----------------------------

@app.route("/status", methods=["GET"])
def get_status():
    """Get current combat status"""
    if not game_state["turn_order"]:
        return jsonify({
            "status": "not_started",
            "message": "Combat not started. Use /start to begin."
        })
    
    engine = CombatEngine(game_state)
    return jsonify(engine.get_combat_status())

@app.route("/start", methods=["POST"])
def start_combat():
    """Start combat and roll initiative"""
    reset_combat()
    engine = CombatEngine(game_state)
    events = engine.roll_initiative()
    
    # Auto-start first round
    round_events = engine.start_round()
    events.extend(round_events)
    
    game_state["log"].extend(events)
    
    current_actor = engine.get_actor_by_ref(engine.get_current_actor())
    
    return jsonify({
        "message": "Combat started",
        "events": events,
        "current_turn": current_actor["name"],
        "status": engine.get_combat_status()
    })

@app.route("/action", methods=["POST"])
def take_action():
    """Take an action in combat"""
    if not game_state["combat_active"]:
        return jsonify({"error": "Combat has ended"}), 400
    
    data = request.json or {}
    action_type = data.get("action", "attack")
    
    engine = CombatEngine(game_state)
    
    # Check if combat has ended
    end_check = engine.check_combat_end()
    if end_check["ended"]:
        game_state["combat_active"] = False
        return jsonify(end_check)
    
    # Get current actor
    current_ref = engine.get_current_actor()
    if not current_ref:
        return jsonify({"error": "No current turn"}), 400
    
    current_actor = engine.get_actor_by_ref(current_ref)
    
    # ----- FIX: Capture and INCLUDE round start events -----
    round_events = []
    if game_state["current_turn_index"] == 0:
        round_events = engine.start_round()
        print(f"DEBUG: Round {game_state['round']} start events: {len(round_events)}")  # Debug
    
    events = []  # Will hold ALL events for this response
    
    # Add round events to the response
    if round_events:
        events.extend(round_events)
    
    # Handle different action types
    if current_ref["type"] == "player":
        if action_type == "attack":
            target_id = data.get("target_id")
            if not target_id:
                return jsonify({"error": "No target specified"}), 400
            
            target = engine.get_enemy(target_id)
            if not target:
                return jsonify({"error": "Invalid target"}), 400
            
            action_events = engine.resolve_attack(game_state["player"], target)
            events.extend(action_events)
            
        elif action_type == "use_buff":
            buff_type = data.get("buff_type")
            if buff_type in ["regen", "block", "focus", "veil"]:
                action_events = engine.apply_buff(
                    game_state["player"],
                    buff_type,
                    duration=3,
                    heal=6 if buff_type == "regen" else None,
                    multiplier=0.6 if buff_type == "block" else None
                )
                events.extend(action_events)
            else:
                return jsonify({"error": "Invalid buff type"}), 400
                
        elif action_type == "use_debuff":
            debuff_type = data.get("debuff_type")
            target_id = data.get("target_id")
            
            if not target_id:
                return jsonify({"error": "No target specified"}), 400
            
            target = engine.get_enemy(target_id)
            if not target:
                return jsonify({"error": "Invalid target"}), 400
            
            if debuff_type in ["poison", "burn", "freeze", "stun"]:
                action_events = engine.apply_debuff(
                    target,
                    debuff_type,
                    duration=3,
                    base=4 if debuff_type == "poison" else None,
                    damage=5 if debuff_type in ["burn", "freeze"] else None
                )
                events.extend(action_events)
            else:
                return jsonify({"error": "Invalid debuff type"}), 400
    
    else:  # Enemy turn
        enemy = engine.get_enemy(current_ref["id"])
        if enemy and enemy["hp"] > 0:
            # Use AI for enemy actions
            ai_events = apply_enemy_ai(engine, enemy)
            if ai_events:
                events.extend(ai_events)
            else:
                action_events = engine.resolve_attack(enemy, game_state["player"])
                events.extend(action_events)
    
    # Add events to log
    game_state["log"].extend(events)
    
    # Advance to next turn
    turn_events = engine.next_turn()
    game_state["log"].extend(turn_events)
    
    # Check combat end again
    end_check = engine.check_combat_end()
    if end_check["ended"]:
        game_state["combat_active"] = False
        events.append(end_check)
    
    # Prepare response - NOW INCLUDES round_events!
    response = {
        "round": game_state["round"],
        "actor": current_actor["name"],
        "events": events,  # ← Now contains round_start events + action events
        "status": engine.get_combat_status()
    }
    
    # Add turn events if any
    if turn_events:
        response["turn_events"] = turn_events
    
    return jsonify(response)
@app.route("/apply_status", methods=["POST"])
def apply_status():
    """Directly apply a status effect (for testing)"""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    target_type = data.get("target_type", "player")  # 'player' or enemy_id
    target_id = data.get("target_id")
    status_type = data.get("status_type")
    is_buff = data.get("is_buff", True)
    duration = data.get("duration", 3)
    
    engine = CombatEngine(game_state)
    
    # Get target
    if target_type == "player":
        target = game_state["player"]
    else:
        target = engine.get_enemy(target_id)
        if not target:
            return jsonify({"error": "Enemy not found"}), 404
    
    # Apply status
    if is_buff:
        events = engine.apply_buff(target, status_type, duration)
    else:
        events = engine.apply_debuff(target, status_type, duration)
    
    game_state["log"].extend(events)
    
    return jsonify({
        "message": f"Applied {status_type} to {target['name']}",
        "events": events,
        "status": engine.get_combat_status()
    })

@app.route("/log", methods=["GET"])
def get_log():
    """Get combat log"""
    return jsonify({
        "log": game_state["log"][-50:]  # Last 50 events
    })

@app.route("/reset", methods=["POST"])
def reset():
    """Reset combat"""
    reset_combat()
    return jsonify({
        "message": "Combat reset",
        "status": "ready to start"
    })

@app.route("/simulate", methods=["POST"])
def simulate():
    """Run a full simulation"""
    data = request.json or {}
    max_turns = data.get("max_turns", 50)
    
    reset_combat()
    engine = CombatEngine(game_state)
    
    # Start combat
    events = engine.roll_initiative()
    events.extend(engine.start_round())
    
    turn_count = 0
    simulation_log = []
    
    while game_state["combat_active"] and turn_count < max_turns:
        turn_count += 1
        current_ref = engine.get_current_actor()
        current = engine.get_actor_by_ref(current_ref)
        
        turn_events = []
        
        if current_ref["type"] == "player":
            # Player attacks first living enemy
            living_enemies = [e for e in game_state["enemies"] if e["hp"] > 0]
            if living_enemies:
                target = living_enemies[0]
                turn_events = engine.resolve_attack(current, target)
        else:
            # Enemy attacks player
            turn_events = engine.resolve_attack(current, game_state["player"])
        
        events.extend(turn_events)
        simulation_log.extend(turn_events)
        
        # Advance turn
        turn_events = engine.next_turn()
        events.extend(turn_events)
        simulation_log.extend(turn_events)
        
        # Check combat end
        end_check = engine.check_combat_end()
        if end_check["ended"]:
            game_state["combat_active"] = False
            events.append(end_check)
            simulation_log.append(end_check)
    
    return jsonify({
        "turns_simulated": turn_count,
        "final_state": engine.get_combat_status(),
        "log": simulation_log
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)