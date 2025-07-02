import os
import environ
from pathlib import Path
import imapclient
import pyzmail
from collections import defaultdict

# --- Environment Setup ---
BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

env = environ.Env()
if ENV_FILE.exists():
    environ.Env.read_env(ENV_FILE)
else:
    raise Exception(f".env file not found! at {ENV_FILE}")

# Load Credentials
EMAIL = env("EMAIL")
PASSWORD = env("PASSWORD")
IMAP_SERVER = env("IMAP_SERVER")
IMAP_PORT = int(env("IMAP_PORT"))

# --- Connect to IMAP (Fetching Emails) ---
imap = imapclient.IMAPClient(IMAP_SERVER, IMAP_PORT, ssl=True)
imap.login(EMAIL, PASSWORD)
imap.select_folder("INBOX")

# --- Input: Sender Email to Search ---
sender_email = input("Enter sender email to filter: ").strip()

# --- Search Emails from Sender ---
search_criteria = ['FROM', sender_email]
UIDs = imap.search(search_criteria)

if not UIDs:
    print(f"No emails found from {sender_email}")
else:
    subject_counts = defaultdict(int)
    
    # Process Each Unread Email
    for uid in UIDs:
        raw_message = imap.fetch([uid], ['BODY[]'])
        message = pyzmail.PyzMessage.factory(raw_message[uid][b'BODY[]'])
        # Extract Email Details
        subject = message.get_subject().strip()
        subject_counts[subject] += 1

    # Display Total Emails and Subjects
    print(f"\nTotal Emails from: {sender_email} = {len(UIDs)}")
    print("\nGrouped by Subject:")
    print("-" * 50)
    
    # Display Grouped Emails
    for subject, count in subject_counts.items():
        print(f"{subject}: {count} message(s)")

# --- Disconnect from IMAP ---
imap.logout()