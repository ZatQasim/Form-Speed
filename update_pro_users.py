import json
import os

def update_pro_users():
    pro_file = 'pro.json'
    
    # Try to find all users from possible sources
    # 1. Check if there's a users table in the database
    # 2. Check if there's a local users file
    
    all_emails = set()
    
    # Default users from the existing pro.json
    try:
        with open(pro_file, 'r') as f:
            data = json.load(f)
            for item in data.get('pro_users', []):
                if '@' in item:
                    all_emails.add(item)
    except Exception as e:
        print(f"Error reading pro.json: {e}")
        data = {"pro_users": [], "subscription": {"price_usd": 5, "trial_days": 7, "features": ["VPN", "Speed Sharing", "Mesh Network", "Advanced Analytics"]}, "stripe_price_id": "price_form_pro_monthly"}

    # Attempt to find other users (this is a safety measure to "never fail" and capture all)
    # In a real app, we'd query the DB. Here we look for common patterns.
    
    # Let's check for any .json files that might contain user data in device_client/cache
    cache_dir = 'device_client/cache'
    if os.path.exists(cache_dir):
        for filename in os.listdir(cache_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(cache_dir, filename), 'r') as f:
                        content = f.read()
                        # Simple heuristic to find emails
                        import re
                        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', content)
                        all_emails.update(emails)
                except:
                    pass

    # Update the pro_users list
    # The user asked for "all emails with their username Pro"
    # Given the format in pro.json: ["qasim", "email", ...]
    # We will ensure all found emails are in the list.
    
    current_pro_users = set(data.get('pro_users', []))
    current_pro_users.update(all_emails)
    
    data['pro_users'] = sorted(list(current_pro_users))
    
    with open(pro_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Successfully updated {pro_file}. Total pro users: {len(data['pro_users'])}")

if __name__ == "__main__":
    update_pro_users()
