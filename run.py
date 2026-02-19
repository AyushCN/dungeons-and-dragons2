# test_all_statuses.py

import requests
import time

BASE_URL = "http://localhost:5000"

def print_header(text):
    print(f"\n{'='*60}")
    print(f"📌 {text}")
    print('='*60)

def test_status(status_name, is_buff, target_type="player", target_id=1, **kwargs):
    """Test a single status effect"""
    
    print_header(f"TESTING: {status_name.upper()} ({'BUFF' if is_buff else 'DEBUFF'})")
    
    # Reset and start
    requests.post(f"{BASE_URL}/reset")
    start_resp = requests.post(f"{BASE_URL}/start").json()
    print(f"Turn order: {start_resp['status']['turn_order']}")
    
    # Apply the status
    json_data = {
        "target_type": target_type,
        "status_type": status_name,
        "is_buff": is_buff,
        "duration": 3
    }
    # Add any additional parameters
    json_data.update(kwargs)
    
    response = requests.post(f"{BASE_URL}/apply_status", json=json_data).json()
    print(f"✓ Applied {status_name}")
    
    # Run 4 turns to see the effect
    for turn in range(1, 5):
        time.sleep(1)
        
        # Get status to see whose turn
        status = requests.get(f"{BASE_URL}/status").json()
        current = status.get('current_turn', 'Unknown')
        
        # Take action
        if current == "Player":
            resp = requests.post(f"{BASE_URL}/action", 
                                json={"action": "attack", "target_id": 1}).json()
        else:
            resp = requests.post(f"{BASE_URL}/action", 
                                json={"action": "attack"}).json()
        
        print(f"\n  Turn {turn} ({current}):")
        
        # Show relevant events
        for event in resp.get('events', []):
            if event.get('type') == 'status_tick':
                print(f"    • {event['status']}: {event['value']} to {event['target']}")
            elif event.get('type') == 'stun_check':
                print(f"    • STUN: {event['target']} can act: {event['can_act']}")
            elif event.get('type') == 'freeze_effect':
                print(f"    • FREEZE: {event['target']} {event['action']}")
            elif event.get('type') == 'damage_reduced':
                print(f"    • DAMAGE REDUCED: {event['original']} → {event['reduced']}")
            elif event.get('type') == 'damage_blocked':
                print(f"    • BLOCKED: {event['damage_after_block']} damage taken")
            elif event.get('type') == 'debuff_blocked':
                print(f"    • VEIL BLOCKED: {event['debuff']}")
            elif event.get('type') == 'attack':
                print(f"    • ATTACK: {event['damage']} damage")
            elif event.get('type') == 'miss':
                print(f"    • MISS")
        
        # Show final HP
        final = resp.get('status', status)
        player_hp = final['player']['hp']
        print(f"    📊 Player HP: {player_hp}/40")

def test_all():
    """Test all status effects"""
    
    print_header("TESTING ALL STATUS EFFECTS")
    
    # Test Buffs
    test_status("regen", True, "player", 1, heal=5)
    test_status("block", True, "player", 1, multiplier=0.5)
    test_status("focus", True, "player", 1)
    test_status("veil", True, "player", 1)
    
    # Test Debuffs on Enemies
    test_status("poison", False, "enemy", 1, base=3, multiplier=1.5)
    test_status("burn", False, "enemy", 1, damage=4)
    test_status("freeze", False, "enemy", 1, damage=3)
    test_status("stun", False, "enemy", 1)
    
    # Test Debuffs on Player
    test_status("poison", False, "player", 1, base=3, multiplier=1.5)
    test_status("burn", False, "player", 1, damage=4)
    test_status("freeze", False, "player", 1, damage=3)
    test_status("stun", False, "player", 1)

if __name__ == "__main__":
    test_all()