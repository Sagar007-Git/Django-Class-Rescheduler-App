import firebase_admin
from firebase_admin import credentials, messaging
import os

# 1. Initialize Firebase App (Only once)
# You must download your 'serviceAccountKey.json' from Firebase Console -> Project Settings -> Service Accounts
# and place it in the root folder (next to manage.py).

KEY_PATH = 'serviceAccountKey.json'

if not firebase_admin._apps:
    if os.path.exists(KEY_PATH):
        cred = credentials.Certificate(KEY_PATH)
        firebase_admin.initialize_app(cred)
    else:
        print(f"WARNING: '{KEY_PATH}' not found. Notifications will NOT be sent.")

def send_push_notification(tokens, title, body, data=None):
    """
    Sends a multicast message to multiple devices (Teachers).
    """
    if not firebase_admin._apps:
        print("Firebase not initialized. Skipping notification.")
        return

    if not tokens:
        return

    # Create the message
    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=data or {}, # Optional data payload (e.g., request_id: "1")
        tokens=tokens,
    )

    try:
        response = messaging.send_multicast(message)
        print(f"Successfully sent {response.success_count} messages.")
        if response.failure_count > 0:
            print(f"Failed to send {response.failure_count} messages.")
    except Exception as e:
        print(f"Error sending FCM message: {e}")