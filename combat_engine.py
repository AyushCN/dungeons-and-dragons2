import random


def roll_dice(num, sides):
    return sum(random.randint(1, sides) for _ in range(num))


def roll_d20(modifier=0):
    die = random.randint(1, 20)
    return {
        "die": die,
        "modifier": modifier,
        "total": die + modifier,
        "is_crit": die == 20,
        "is_fumble": die == 1
    }


class CombatEngine:

    def __init__(self, game_state):
        self.state = game_state

    # -------------------------
    # ACTOR RESOLUTION
    # -------------------------
    def get_enemy(self, enemy_id):
        return next(
            (e for e in self.state["enemies"] if e["id"] == enemy_id),
            None
        )

    def get_current_actor(self):
        return self.state["turn_order"][self.state["current_turn_index"]]

    # -------------------------
    # INITIATIVE
    # -------------------------
    def roll_initiative(self):
        self.state["player"]["initiative"] = random.randint(1, 20)

        for enemy in self.state["enemies"]:
            enemy["initiative"] = random.randint(1, 20)

        combatants = [
            {"type": "player", "initiative": self.state["player"]["initiative"]}
        ]

        for enemy in self.state["enemies"]:
            combatants.append({
                "type": "enemy",
                "id": enemy["id"],
                "initiative": enemy["initiative"]
            })

        combatants.sort(key=lambda x: x["initiative"], reverse=True)

        self.state["turn_order"] = combatants
        self.state["current_turn_index"] = 0

    # -------------------------
    # TURN CONTROL
    # -------------------------
    def next_turn(self):
        self.state["current_turn_index"] += 1
        if self.state["current_turn_index"] >= len(self.state["turn_order"]):
            self.state["current_turn_index"] = 0

    def remove_actor_from_turn_order(self, actor_type, actor_id=None):
        idx = self.state["current_turn_index"]
        turn_order = self.state["turn_order"]

        for i, entry in enumerate(turn_order):
            if entry["type"] != actor_type:
                continue

            if actor_type == "player" or entry.get("id") == actor_id:
                turn_order.pop(i)

                if i < idx:
                    self.state["current_turn_index"] -= 1
                elif i == idx:
                    pass

                break

        if self.state["current_turn_index"] >= len(turn_order):
            self.state["current_turn_index"] = 0

    # -------------------------
    # COMBAT RESOLUTION
    # -------------------------
    def resolve_attack(self, attacker, defender):
        roll = roll_d20(attacker["attack_bonus"])

        # Calculate effective AC (buffs apply here)
        effective_ac = defender["ac"]
        for effect in defender["status_effects"]:
            if effect["type"] == "defend":
                effective_ac += effect["ac_bonus"]

        # MISS
        if roll["total"] < effective_ac:
            return {
                "type": "attack",
                "attacker": attacker["name"],
                "defender": defender["name"],
                "roll": roll,
                "hit": False,
                "crit": False,
                "damage": 0
            }

        # HIT / CRIT
        num, sides = attacker["damage"]

        if roll["is_crit"]:
            damage = roll_dice(num * 2, sides)
        else:
            damage = roll_dice(num, sides)

        defender["hp"] -= damage

        event = {
            "type": "attack",
            "attacker": attacker["name"],
            "defender": defender["name"],
            "roll": roll,
            "hit": True,
            "crit": roll["is_crit"],
            "damage": damage,
            "defender_hp": defender["hp"]
        }

        # Apply poison ON HIT (example rule)
        if attacker.get("poison_on_hit"):
            defender["status_effects"].append({
                "type": "poison",
                "damage": 2,
                "duration": 3
            })
            event["applied_status"] = "poison"

        return event


    # -------------------------
    # PLAYER
    # -------------------------
    def resolve_player_attack(self, target_id):
        enemy = self.get_enemy(target_id)
        if not enemy:
            return {"error": "Invalid target"}

        return self.resolve_attack(self.state["player"], enemy)

    # -------------------------
    # ENEMY
    # -------------------------
    def choose_enemy_action(self, enemy):
        if enemy["hp"] < 0.3 * 20:
            return "defend"
        return "attack"

    def resolve_enemy_turn(self):
        actor = self.get_current_actor()

        if actor["type"] != "enemy":
            return {"error": "Not enemy turn"}

        enemy = self.get_enemy(actor["id"])

        # Enemy may already be dead
        if not enemy:
            self.remove_actor_from_turn_order("enemy", actor["id"])
            return {
                "type": "skip",
                "reason": "enemy already dead"
            }

        events = []

        # -------- START OF TURN STATUS EFFECTS --------
        status_events = self.apply_status_effects(enemy)
        events.extend(status_events)

        # Enemy died from poison before acting
        if enemy["hp"] <= 0:
            self.remove_actor_from_turn_order("enemy", enemy["id"])
            return {
                "type": "status_death",
                "actor": enemy["name"],
                "events": events
            }

        # -------- ACTION DECISION --------
        action = self.choose_enemy_action(enemy)

        if action == "attack":
            attack_event = self.resolve_attack(enemy, self.state["player"])
            events.append(attack_event)

            return {
                "type": "enemy_turn",
                "actor": enemy["name"],
                "events": events
            }

        if action == "defend":
            enemy["status_effects"].append({
                "type": "defend",
                "ac_bonus": 2,
                "duration": 1
            })

            events.append({
                "type": "status",
                "effect": "defend",
                "target": enemy["name"],
                "duration": 1
            })

            return {
                "type": "enemy_turn",
                "actor": enemy["name"],
                "events": events
            }

    def apply_status_effects(self, actor):
        events = []

        for effect in list(actor["status_effects"]):
            if effect["type"] == "poison":
                actor["hp"] -= effect["damage"]
                effect["duration"] -= 1

                events.append({
                    "type": "status",
                    "effect": "poison",
                    "target": actor["name"],
                    "damage": effect["damage"],
                    "remaining_duration": effect["duration"]
                })

                if effect["duration"] <= 0:
                    actor["status_effects"].remove(effect)

        return events
