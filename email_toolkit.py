import os
import environ
from pathlib import Path
import smtplib
import imapclient
import pyzmail
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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

SMTP_SERVER = env("SMTP_SERVER")
SMTP_PORT = int(env("SMTP_PORT"))

# --- Connect to IMAP (Fetching Emails) ---
imap = imapclient.IMAPClient(IMAP_SERVER, IMAP_PORT, ssl=True)
imap.login(EMAIL, PASSWORD)
imap.select_folder("INBOX")

# --- Menu ---
try:
    while True:
        print("Choose an option:")
        print("1. Read and reply to unread emails")
        print("2. Count emails from a specific sender and group by subject")
        print("3. Exit")

        choice = input("Enter your choice (1, 2, or 3): ").strip()
        
        if not choice:
            print("Invalid option. Please enter a valid option: 1, 2, or 3.")
            continue

        # --- Option 1: Read and reply ---
        if choice == "1":
            # Find All Unread Emails
            UIDs = imap.search(['UNSEEN'])

            # Process Each Unread Email
            for uid in UIDs:
                raw_message = imap.fetch([uid], ['BODY[]', 'FLAGS'])
                message = pyzmail.PyzMessage.factory(raw_message[uid][b'BODY[]'])

                # Extract Email Details
                subject = message.get_subject()
                from_name, from_email = message.get_addresses('from')[0]
                body = ""
                if message.text_part:
                    body = message.text_part.get_payload().decode(message.text_part.charset)
                elif message.html_part:
                    body = message.html_part.get_payload().decode(message.html_part.charset)
                else:
                    body = "(No text body found)"

                # Display Email to User
                print("\n" + "-"*50)
                print(f"From: {from_name} <{from_email}>")
                print(f"Subject: {subject}")
                print("Body Preview:\n", body[:500], "..." if len(body) > 500 else "")

                # Prompt User to Reply
                reply = input("Do you want to reply to this email? (yes/no): ").strip().lower()
                if reply == "yes":
                    reply_text = input("Enter your reply:\n")

                    # Send Reply via SMTP
                    msg = MIMEMultipart()
                    msg['From'] = EMAIL
                    msg['To'] = from_email
                    msg['Subject'] = f"Re: {subject}"
                    msg.attach(MIMEText(reply_text, 'plain'))

                    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                        server.starttls()
                        server.login(EMAIL, PASSWORD)
                        server.sendmail(EMAIL, from_email, msg.as_string())
                    print("Reply sent.")

                # Mark Email as Read or Seen
                imap.add_flags([uid], [b'\\Seen'])
            input("\n Task complete. Press Enter to return to menu...")
                
                
        # --- Option 2: Count and group by subject ---
        elif choice == "2":
            # --- Input: Sender Email to Search ---
            sender_email = input("Enter sender email to filter: ").strip()
            
            # --- Search Emails from Sender ---
            UIDs = imap.search(['FROM', sender_email])

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
                for subject, count in subject_counts.items():
                    print(f"{subject}: {count} message(s)")
            input("\n Task complete. Press Enter to return to menu...")

        elif choice == "3":
            print("Goodbye!")
            os.system('cls' if os.name == 'nt' else 'clear')
            break
        
        else:
            print("Invalid option selected.")

# --- Logout ---
finally:
    imap.logout()
