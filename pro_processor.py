import json
import re
from app import app, db, User, load_pro_config

EMAIL_REGEX = re.compile(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
)

def extract_emails_from_config(config: dict) -> set:
    """
    Recursively scan pro.json for ANY emails (gmail or otherwise).
    """
    found_emails = set()

    def scan(value):
        if isinstance(value, str):
            for email in EMAIL_REGEX.findall(value):
                found_emails.add(email.strip().lower())
        elif isinstance(value, list):
            for item in value:
                scan(item)
        elif isinstance(value, dict):
            for v in value.values():
                scan(v)

    scan(config)
    return found_emails


def grant_pro_benefits():
    """
    Analyze pro.json and ensure all matching users receive Pro status.
    """
    print("Starting Pro Status Analysis...")

    with app.app_context():
        try:
            config = load_pro_config()

            # Extract emails from anywhere in pro.json
            email_matches = extract_emails_from_config(config)

            # Also keep legacy username list if it exists
            username_matches = {
                str(u).strip().lower()
                for u in config.get("pro_users", [])
                if u
            }

            if not email_matches and not username_matches:
                print("No emails or usernames found in pro.json.")
                return

            print(f"Found {len(email_matches)} email(s) and {len(username_matches)} username(s).")

            granted_count = 0
            all_users = User.query.all()

            for user in all_users:
                user_email = user.email.strip().lower() if user.email else ""
                user_name = user.username.strip().lower() if user.username else ""

                if user_email in email_matches or user_name in username_matches:
                    if not user.is_pro or user.subscription_status != "active":
                        user.is_pro = True
                        user.subscription_status = "active"

                        if not user.stripe_subscription_id:
                            user.stripe_subscription_id = "pro_json_override"

                        db.session.add(user)
                        granted_count += 1
                        print(f"GRANTED: {user.username} ({user.email})")

            db.session.commit()
            print(f"Analysis complete. Total users updated: {granted_count}")

        except Exception as e:
            db.session.rollback()
            print(f"ERROR during analysis: {e}")


if __name__ == "__main__":
    grant_pro_benefits()