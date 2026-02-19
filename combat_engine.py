# combat_engine.py - COMPLETE WITH ALL STATUS EFFECTS

import random

class CombatEngine:
    def __init__(self, state):
        self.state = state

    # -------------------------------------------------
    # ACTOR HELPERS
    # -------------------------------------------------

    def get_all_actors(self):
        return [self.state["player"]] + self.state["enemies"]

    def get_enemy(self, enemy_id):
        for e in self.state["enemies"]:
            if e["id"] == enemy_id:
                return e
        return None

    def get_actor_by_ref(self, ref):
        if not ref:
            return None
        if ref["type"] == "player":
            return self.state["player"]
        return self.get_enemy(ref["id"])

    # -------------------------------------------------
    # INITIATIVE
    # -------------------------------------------------

    def roll_initiative(self):
        combatants = []

        # Player
        p = self.state["player"]
        p["initiative"] = random.randint(1, 20) + p["stats"]["spd"]
        combatants.append({
            "type": "player",
            "initiative": p["initiative"]
        })

        # Enemies
        for e in self.state["enemies"]:
            e["initiative"] = random.randint(1, 20) + e["stats"]["spd"]
            combatants.append({
                "type": "enemy",
                "id": e["id"],
                "initiative": e["initiative"]
            })

        combatants.sort(key=lambda x: x["initiative"], reverse=True)
        self.state["turn_order"] = combatants
        self.state["current_turn_index"] = 0
        
        return [{
            "type": "initiative_rolled",
            "turn_order": [
                f"{self.get_actor_by_ref(ref)['name']} ({ref['initiative']})"
                for ref in combatants if self.get_actor_by_ref(ref)
            ]
        }]

    # -------------------------------------------------
    # STATUS APPLICATION - COMPLETE WITH ALL EFFECTS
    # -------------------------------------------------

    def apply_buff(self, target, buff_type, duration, **kwargs):
        """Apply a buff if slot is empty"""
        events = []
        
        # Check if buff slot is occupied
        if target["buff"] is not None:
            events.append({
                "type": "buff_failed",
                "target": target["name"],
                "buff": buff_type,
                "reason": "slot_occupied",
                "existing_buff": target["buff"]["type"]
            })
            return events
        
        # Create buff based on type
        buff = {"type": buff_type, "duration": duration}
        
        if buff_type == "regen":
            buff["heal"] = kwargs.get("heal", 5)
            events.append({
                "type": "buff_applied",
                "target": target["name"],
                "buff": "regen",
                "heal": buff["heal"],
                "duration": duration
            })
            
        elif buff_type == "block":
            buff["multiplier"] = kwargs.get("multiplier", 0.5)
            events.append({
                "type": "buff_applied",
                "target": target["name"],
                "buff": "block",
                "multiplier": buff["multiplier"],
                "duration": duration,
                "effect": f"Reduces incoming damage by {int((1-buff['multiplier'])*100)}%"
            })
            
        elif buff_type == "focus":
            events.append({
                "type": "buff_applied",
                "target": target["name"],
                "buff": "focus",
                "duration": duration,
                "effect": "Roll twice for attacks, take highest"
            })
            
        elif buff_type == "veil":
            buff["turn"] = 1
            events.append({
                "type": "buff_applied",
                "target": target["name"],
                "buff": "veil",
                "duration": duration,
                "protection_turn1": "100%",
                "protection_turn2": "65%",
                "protection_turn3": "40%"
            })
        
        target["buff"] = buff
        return events

    def apply_debuff(self, target, debuff_type, duration, **kwargs):
        """Apply a debuff with veil check and slot validation"""
        events = []
        
        # Check veil protection
        if target["buff"] and target["buff"]["type"] == "veil":
            veil_turn = target["buff"].get("turn", 1)
            block_chance = [1.0, 0.65, 0.40][veil_turn - 1]
            
            if random.random() < block_chance:
                # Debuff blocked
                target["buff"]["turn"] = veil_turn + 1
                events.append({
                    "type": "debuff_blocked",
                    "target": target["name"],
                    "debuff": debuff_type,
                    "by": "veil",
                    "veil_turn": veil_turn
                })
                return events
            else:
                # Veil breaks
                events.append({
                    "type": "veil_broken",
                    "target": target["name"],
                    "debuff": debuff_type
                })
                target["buff"] = None
        
        # Check if debuff slot is occupied
        if target["debuff"] is not None:
            events.append({
                "type": "debuff_failed",
                "target": target["name"],
                "debuff": debuff_type,
                "reason": "slot_occupied",
                "existing_debuff": target["debuff"]["type"]
            })
            return events
        
        # Create debuff based on type
        debuff = {"type": debuff_type, "duration": duration}
        
        if debuff_type == "poison":
            # Exponential damage over time
            debuff["base"] = kwargs.get("base", 3)
            debuff["multiplier"] = kwargs.get("multiplier", 1.5)
            debuff["turn"] = 1
            events.append({
                "type": "debuff_applied",
                "target": target["name"],
                "debuff": "poison",
                "base_damage": debuff["base"],
                "multiplier": debuff["multiplier"],
                "duration": duration,
                "effect": "Damage increases each round"
            })
            
        elif debuff_type == "burn":
            # Flat damage + reduces outgoing damage
            debuff["damage"] = kwargs.get("damage", 4)
            debuff["turn"] = 1
            events.append({
                "type": "debuff_applied",
                "target": target["name"],
                "debuff": "burn",
                "damage": debuff["damage"],
                "duration": duration,
                "effect": "Deals flat damage each round and reduces outgoing damage by 30%"
            })
            
        elif debuff_type == "freeze":
            # Flat damage + turn order manipulation
            debuff["damage"] = kwargs.get("damage", 3)
            debuff["turn_index"] = 1
            events.append({
                "type": "debuff_applied",
                "target": target["name"],
                "debuff": "freeze",
                "damage": debuff["damage"],
                "duration": duration,
                "effect": "Deals damage each round and may force acting last"
            })
            
        elif debuff_type == "stun":
            # Turn skipping with progressive recovery
            debuff["turn"] = 1
            debuff["can_act"] = False
            events.append({
                "type": "debuff_applied",
                "target": target["name"],
                "debuff": "stun",
                "duration": duration,
                "effect": "Chance to skip turns, increases each turn"
            })
        
        target["debuff"] = debuff
        return events

    # -------------------------------------------------
    # ROUND CONTROL
    # -------------------------------------------------

    def start_round(self):
        events = []

        events.append({
            "type": "round_start",
            "round": self.state["round"]
        })

        # Resolve statuses for all actors
        for actor in self.get_all_actors():
            if actor["hp"] > 0:
                events.extend(self.resolve_statuses(actor))

        # Apply freeze turn order manipulation
        events.extend(self.apply_freeze_order())

        return events

    def end_round(self):
        """Cleanup expired statuses and increment round"""
        events = []
        
        for actor in self.get_all_actors():
            if actor["hp"] > 0:
                cleanup_events = self.cleanup_status(actor)
                if cleanup_events:
                    events.extend(cleanup_events)

        self.state["round"] += 1
        
        events.append({
            "type": "round_end",
            "new_round": self.state["round"]
        })
        
        return events

    # -------------------------------------------------
    # STATUS RESOLUTION - COMPLETE WITH ALL EFFECTS
    # -------------------------------------------------

    def resolve_statuses(self, actor):
        events = []
        
        print(f"DEBUG: Resolving statuses for {actor['name']}")
        print(f"DEBUG: Buff: {actor['buff']}")
        print(f"DEBUG: Debuff: {actor['debuff']}")

        # ---------- REGEN (BUFF) ----------
        if actor["buff"] and actor["buff"]["type"] == "regen":
            heal = actor["buff"]["heal"]
            old_hp = actor["hp"]
            max_hp = actor["max_hp"]
            
            if old_hp < max_hp:
                new_hp = min(max_hp, old_hp + heal)
                actor["hp"] = new_hp
                heal_amount = new_hp - old_hp
            else:
                heal_amount = 0
            
            actor["buff"]["duration"] -= 1
            
            events.append({
                "type": "status_tick",
                "status": "regen",
                "target": actor["name"],
                "value": heal_amount,
                "hp_before": old_hp,
                "hp_after": actor["hp"]
            })
            print(f"DEBUG: Applied regen, healed {heal_amount}")

        # ---------- DEBUFFS ----------
        if actor["debuff"]:
            dmg = 0
            debuff = actor["debuff"]
            print(f"DEBUG: Processing debuff: {debuff['type']}")

            # ----- POISON (Exponential) -----
            if debuff["type"] == "poison":
                dmg = int(debuff["base"] * (debuff["multiplier"] ** debuff["turn"]))
                print(f"DEBUG: Poison turn {debuff['turn']}, damage {dmg}")
                debuff["turn"] += 1
                debuff["duration"] -= 1
                
            # ----- BURN (Flat damage) -----
            elif debuff["type"] == "burn":
                dmg = debuff["damage"]
                print(f"DEBUG: Burn damage: {dmg}")
                debuff["duration"] -= 1
                
            # ----- FREEZE (Flat damage) -----
            elif debuff["type"] == "freeze":
                dmg = debuff["damage"]
                print(f"DEBUG: Freeze damage: {dmg}")
                debuff["duration"] -= 1
                # Turn index handled in apply_freeze_order
                
            # ----- STUN (Turn skipping) -----
            elif debuff["type"] == "stun":
                turn = debuff.get("turn", 1)
                
                # Stun recovery chances
                if turn == 1:
                    debuff["can_act"] = False
                    print(f"DEBUG: Stun turn 1 - cannot act")
                elif turn == 2:
                    debuff["can_act"] = random.random() < 0.30
                    print(f"DEBUG: Stun turn 2 - can act: {debuff['can_act']}")
                elif turn == 3:
                    debuff["can_act"] = random.random() < 0.40
                    print(f"DEBUG: Stun turn 3 - can act: {debuff['can_act']}")
                else:
                    chance = min(0.50 + (turn - 4) * 0.10, 0.90)
                    debuff["can_act"] = random.random() < chance
                    print(f"DEBUG: Stun turn {turn} - chance {chance:.0%}, can act: {debuff['can_act']}")
                
                debuff["turn"] = turn + 1
                
                events.append({
                    "type": "stun_check",
                    "target": actor["name"],
                    "turn": turn,
                    "can_act": debuff["can_act"]
                })

            # Apply damage if any
            if dmg > 0:
                old_hp = actor["hp"]
                actor["hp"] -= dmg
                
                events.append({
                    "type": "status_tick",
                    "status": debuff["type"],
                    "target": actor["name"],
                    "value": dmg,
                    "hp_before": old_hp,
                    "hp_after": actor["hp"]
                })
                print(f"DEBUG: Applied {dmg} damage, HP {old_hp} → {actor['hp']}")

        return events

    # -------------------------------------------------
    # CLEANUP STATUS
    # -------------------------------------------------

    def cleanup_status(self, actor):
        """Remove expired statuses"""
        events = []
        
        # Cleanup buffs
        if actor["buff"] and actor["buff"]["duration"] <= 0:
            events.append({
                "type": "buff_expired",
                "target": actor["name"],
                "buff": actor["buff"]["type"]
            })
            actor["buff"] = None
            print(f"DEBUG: Buff expired for {actor['name']}")

        # Cleanup debuffs (except stun which has special removal)
        if actor["debuff"] and actor["debuff"]["duration"] <= 0:
            if actor["debuff"]["type"] != "stun":
                events.append({
                    "type": "debuff_expired",
                    "target": actor["name"],
                    "debuff": actor["debuff"]["type"]
                })
                actor["debuff"] = None
                print(f"DEBUG: Debuff expired for {actor['name']}")
        
        # Special handling for stun (removed on successful recovery)
        if actor["debuff"] and actor["debuff"]["type"] == "stun":
            if actor["debuff"].get("can_act", False):
                events.append({
                    "type": "stun_recovered",
                    "target": actor["name"]
                })
                actor["debuff"] = None
                print(f"DEBUG: Stun recovered for {actor['name']}")
        
        return events

    # -------------------------------------------------
    # FREEZE TURN ORDER EFFECT
    # -------------------------------------------------

    def apply_freeze_order(self):
        """Temporarily move frozen actors to end of turn order for this round"""
        events = []
        new_order = []
        frozen = []

        for ref in self.state["turn_order"]:
            actor = self.get_actor_by_ref(ref)
            
            if actor and actor["hp"] > 0 and actor["debuff"] and actor["debuff"]["type"] == "freeze":
                turn = actor["debuff"].get("turn_index", 1)
                
                # Freeze turn effects:
                if turn == 1:
                    go_last = True
                elif turn == 2:
                    go_last = random.random() < 0.80
                elif turn == 3:
                    go_last = random.random() < 0.70
                else:
                    go_last = False

                actor["debuff"]["turn_index"] = turn + 1

                if go_last:
                    frozen.append(ref)
                    events.append({
                        "type": "freeze_effect",
                        "target": actor["name"],
                        "turn": turn,
                        "action": "moved_to_end"
                    })
                else:
                    new_order.append(ref)
                    events.append({
                        "type": "freeze_effect",
                        "target": actor["name"],
                        "turn": turn,
                        "action": "normal_turn"
                    })
            else:
                new_order.append(ref)

        self.state["turn_order"] = new_order + frozen
        return events

    # -------------------------------------------------
    # TURN ORDER CLEANUP
    # -------------------------------------------------

    def cleanup_turn_order(self):
        """Remove dead actors from turn order"""
        new_turn_order = []
        
        for ref in self.state["turn_order"]:
            actor = self.get_actor_by_ref(ref)
            if actor and actor["hp"] > 0:
                new_turn_order.append(ref)
            else:
                print(f"DEBUG: Removing dead actor from turn order")
        
        self.state["turn_order"] = new_turn_order
        
        # Make sure current_turn_index is valid
        if self.state["current_turn_index"] >= len(self.state["turn_order"]):
            self.state["current_turn_index"] = 0

    # -------------------------------------------------
    # TURN FLOW
    # -------------------------------------------------

    def get_current_actor(self):
        if self.state["current_turn_index"] < len(self.state["turn_order"]):
            return self.state["turn_order"][self.state["current_turn_index"]]
        return None

    def next_turn(self):
        """Advance to next turn, handling stun and round transitions"""
        events = []
        
        # Check if combat has ended
        combat_end = self.check_combat_end()
        if combat_end["ended"]:
            return [combat_end]

        # Get current actor
        current_ref = self.get_current_actor()
        if not current_ref:
            return events

        current_actor = self.get_actor_by_ref(current_ref)
        
        # Check for stun
        if current_actor and current_actor["hp"] > 0:
            if current_actor.get("debuff") and current_actor["debuff"]["type"] == "stun":
                if not current_actor["debuff"].get("can_act", True):
                    # Skip this turn
                    events.append({
                        "type": "turn_skipped",
                        "actor": current_actor["name"],
                        "reason": "stunned"
                    })
                    
                    self.state["current_turn_index"] += 1
                    
                    # Check if round ended
                    if self.state["current_turn_index"] >= len(self.state["turn_order"]):
                        self.state["current_turn_index"] = 0
                        events.extend(self.end_round())
                    
                    # Recursively process next turn
                    events.extend(self.next_turn())
                    return events

        # Normal turn advancement
        self.state["current_turn_index"] += 1

        if self.state["current_turn_index"] >= len(self.state["turn_order"]):
            self.state["current_turn_index"] = 0
            events.extend(self.end_round())

        return events

    # -------------------------------------------------
    # COMBAT END CHECK
    # -------------------------------------------------

    def check_combat_end(self):
        """Check if combat has ended"""
        if self.state["player"]["hp"] <= 0:
            return {
                "type": "combat_end",
                "ended": True,
                "reason": "player_defeated",
                "round": self.state["round"]
            }
        
        alive_enemies = [e for e in self.state["enemies"] if e["hp"] > 0]
        if not alive_enemies:
            return {
                "type": "combat_end",
                "ended": True,
                "reason": "victory",
                "round": self.state["round"]
            }
        
        self.state["enemies"] = alive_enemies
        
        # Clean up turn order
        self.cleanup_turn_order()
        
        return {"ended": False}

    # -------------------------------------------------
    # ATTACK RESOLUTION
    # -------------------------------------------------

    def resolve_attack(self, attacker, defender):
        events = []
        
        if defender["hp"] <= 0:
            events.append({
                "type": "attack_aborted",
                "reason": "defender_already_dead",
                "defender": defender["name"]
            })
            return events

        # Roll with Focus
        if attacker["buff"] and attacker["buff"]["type"] == "focus":
            d1 = random.randint(1, 20)
            d2 = random.randint(1, 20)
            roll = max(d1, d2)
            crit = d1 == 20 or d2 == 20
            events.append({
                "type": "focus_roll",
                "attacker": attacker["name"],
                "rolls": [d1, d2],
                "used": roll
            })
        else:
            roll = random.randint(1, 20)
            crit = roll == 20

        total = roll + attacker["attack_bonus"] + attacker["stats"]["acc"]

        # Hit check
        if total < defender["ac"] + defender["stats"]["arm"]:
            events.append({
                "type": "miss",
                "attacker": attacker["name"],
                "defender": defender["name"],
                "roll": roll,
                "total": total,
                "target_ac": defender["ac"] + defender["stats"]["arm"]
            })
            return events

        # Damage calculation
        num, sides = attacker["damage"]
        dice = num * (2 if crit else 1)
        base = sum(random.randint(1, sides) for _ in range(dice))
        damage = base + attacker["stats"]["str"]

        original_damage = damage

        # Burn/Freeze reduction (30% less damage)
        if attacker["debuff"] and attacker["debuff"]["type"] in ("burn", "freeze"):
            damage = int(damage * 0.70)
            events.append({
                "type": "damage_reduced",
                "reason": attacker["debuff"]["type"],
                "original": original_damage,
                "reduced": damage
            })

        # Block reduction
        if defender["buff"] and defender["buff"]["type"] == "block":
            damage = int(damage * defender["buff"]["multiplier"])
            events.append({
                "type": "damage_blocked",
                "defender": defender["name"],
                "block_multiplier": defender["buff"]["multiplier"],
                "damage_after_block": damage
            })

        old_hp = defender["hp"]
        defender["hp"] -= damage

        events.append({
            "type": "attack",
            "attacker": attacker["name"],
            "defender": defender["name"],
            "hit": True,
            "crit": crit,
            "roll": roll,
            "total": total,
            "damage": damage,
            "defender_hp_before": old_hp,
            "defender_hp_after": defender["hp"]
        })

        if defender["hp"] <= 0:
            events.append({
                "type": "death",
                "character": defender["name"]
            })

        return events

    # -------------------------------------------------
    # SIMULATION HELPERS
    # -------------------------------------------------

    def get_combat_status(self):
        """Get current combat status summary"""
        # Safely build turn order display
        turn_order_display = []
        for ref in self.state["turn_order"]:
            actor = self.get_actor_by_ref(ref)
            if actor:
                turn_order_display.append(f"{actor['name']} ({ref['initiative']})")
        
        # Safely get current turn
        current_ref = self.get_current_actor()
        current_actor = self.get_actor_by_ref(current_ref) if current_ref else None
        current_turn_name = current_actor["name"] if current_actor else None
        
        return {
            "round": self.state["round"],
            "player": {
                "name": self.state["player"]["name"],
                "hp": self.state["player"]["hp"],
                "max_hp": self.state["player"]["max_hp"],
                "buff": self.state["player"]["buff"]["type"] if self.state["player"]["buff"] else None,
                "debuff": self.state["player"]["debuff"]["type"] if self.state["player"]["debuff"] else None
            },
            "enemies": [
                {
                    "name": e["name"],
                    "hp": e["hp"],
                    "max_hp": e["max_hp"],
                    "buff": e["buff"]["type"] if e["buff"] else None,
                    "debuff": e["debuff"]["type"] if e["debuff"] else None
                }
                for e in self.state["enemies"] if e["hp"] > 0
            ],
            "turn_order": turn_order_display,
            "current_turn": current_turn_name,
            "combat_active": self.state["player"]["hp"] > 0 and len([e for e in self.state["enemies"] if e["hp"] > 0]) > 0
        }