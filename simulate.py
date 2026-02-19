# simulate.py

import copy
from combat_engine import CombatEngine
from app import game_state as BASE_STATE


def clone_state():
    return copy.deepcopy(BASE_STATE)


def run_debug_combat(max_rounds=10):
    """
    Runs ONE combat and prints EVERYTHING so you can see statuses working.
    """
    state = clone_state()
    engine = CombatEngine(state)

    engine.roll_initiative()

    print("=== COMBAT START ===")

    while True:
        # ----- END CONDITIONS -----
        if state["player"]["hp"] <= 0:
            print("\nPLAYER DEFEATED")
            break

        if not state["enemies"]:
            print("\nENEMIES DEFEATED")
            break

        if state["round"] > max_rounds:
            print("\nCOMBAT TIMEOUT")
            break

        # ----- START OF ROUND -----
        if state["current_turn_index"] == 0:
            events = engine.start_round()
            print(f"\n--- ROUND {state['round']} START ---")
            for e in events:
                print(e)

        actor_ref = engine.get_current_actor()

        # ----- PLAYER TURN -----
        if actor_ref["type"] == "player":
            print("\nPlayer turn")

            target = state["enemies"][0]
            event = engine.resolve_attack(state["player"], target)
            print(event)

            # remove dead enemies
            state["enemies"] = [e for e in state["enemies"] if e["hp"] > 0]

        # ----- ENEMY TURN -----
        else:
            enemy = engine.get_enemy(actor_ref["id"])
            print(f"\n{enemy['name']} turn")

            event = engine.resolve_attack(enemy, state["player"])
            print(event)

        engine.next_turn()

    print("\n=== COMBAT END ===")


if __name__ == "__main__":
    run_debug_combat()
