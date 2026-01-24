import json
import os
from app import app, db, User, load_pro_config

def grant_pro_benefits():
    """
    Independent program to analyze pro.json and ensure all users have Pro benefits.
    Can be run as a standalone script or scheduled task.
    """
    print("Starting Pro Status Analysis...")
    
    with app.app_context():
        try:
            config = load_pro_config()
            pro_users = [str(u).strip().lower() for u in config.get('pro_users', []) if u]
            
            if not pro_users:
                print("No users found in pro.json.")
                return

            print(f"Found {len(pro_users)} identifier(s) in pro.json.")
            
            # Grant Pro status to all matching users in the database
            all_users = User.query.all()
            granted_count = 0
            
            for user in all_users:
                user_email = user.email.strip().lower() if user.email else ""
                user_name = user.username.strip().lower() if user.username else ""
                
                if user_email in pro_users or user_name in pro_users:
                    if not user.is_pro or user.subscription_status != 'active':
                        user.is_pro = True
                        user.subscription_status = 'active'
                        if not user.stripe_subscription_id:
                            user.stripe_subscription_id = "pro_json_override"
                        
                        db.session.add(user)
                        granted_count += 1
                        print(f"GRANTED: {user.username} ({user.email})")
            
            db.session.commit()
            print(f"Analysis complete. Total users updated: {granted_count}")
            
        except Exception as e:
            print(f"ERROR during analysis: {str(e)}")

if __name__ == "__main__":
    grant_pro_benefits()
