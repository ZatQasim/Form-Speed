import requests
import os

FORM_ID_URL = os.getenv("FORM_ID_URL")

def verify_form_id_token(token):
    r = requests.post(
        f"{FORM_ID_URL}/verify",
        json={"token": token},
        timeout=3
    )
    if r.status_code != 200:
        return None
    return r.json()  # { user_id, email }