import json
import os
import re
import sqlite3

def update_pro_users():
    pro_file = 'pro.json'
    all_emails = set()
    
    # 1. Existing Pro Users
    try:
        with open(pro_file, 'r') as f:
            data = json.load(f)
            for item in data.get('pro_users', []):
                if '@' in item: all_emails.add(item)
    except:
        data = {"pro_users": [], "subscription": {"price_usd": 5, "trial_days": 7, "features": ["VPN", "Speed Sharing", "Mesh Network", "Advanced Analytics"]}, "stripe_price_id": "price_form_pro_monthly"}

    # 2. Database Extraction
    try:
        if os.path.exists('instance/project.db'):
            conn = sqlite3.connect('instance/project.db')
            cursor = conn.cursor()
            cursor.execute("SELECT email FROM user")
            for row in cursor.fetchall():
                if row[0]: all_emails.add(row[0])
            conn.close()
    except: pass

    # 3. Hardcoded / Known Users
    all_emails.add("qasimthemuslimdiscord@gmail.com")
    
    # 4. Final Merge
    data['pro_users'] = sorted(list(all_emails))
    
    with open(pro_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Updated pro.json with {len(data['pro_users'])} emails.")

if __name__ == '__main__':
    update_pro_users()
