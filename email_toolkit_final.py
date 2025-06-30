import os
import environ
from pathlib import Path
import smtplib
import imapclient
import pyzmail
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from collections import defaultdict
import json
import html
import re


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

env = environ.Env()
if ENV_FILE.exists():
    environ.Env.read_env(ENV_FILE)
else:
    raise Exception(f".env file not found! at {ENV_FILE}")

EMAIL = env("EMAIL")
PASSWORD = env("PASSWORD")
IMAP_SERVER = env("IMAP_SERVER")
IMAP_PORT = int(env("IMAP_PORT"))
SMTP_SERVER = env("SMTP_SERVER")
SMTP_PORT = int(env("SMTP_PORT"))


imap = imapclient.IMAPClient(IMAP_SERVER, IMAP_PORT, ssl=True)
imap.login(EMAIL, PASSWORD)
imap.select_folder("INBOX")


def clean_email_body(message):
    body = ""
    if message.text_part:
        try:
            body = message.text_part.get_payload().decode(message.text_part.charset or "utf-8")
        except:
            body = message.text_part.get_payload().decode("utf-8", errors="replace")
    elif message.html_part:
        try:
            body = message.html_part.get_payload().decode(message.html_part.charset or "utf-8")
        except:
            body = message.html_part.get_payload().decode("utf-8", errors="replace")

    clean_body = body.replace('\r\n', '\n').replace('\xa0', ' ')
    clean_body = html.unescape(clean_body)
    clean_body = re.sub(r'<[^>]+>', '', clean_body)
    clean_body = re.sub(r'\u2060', '', clean_body)
    clean_body = re.sub(r'[ \t]+$', '', clean_body, flags=re.MULTILINE)
    clean_body = re.sub(r'\n{3,}', '\n\n', clean_body)
    clean_body = re.sub(r'-\s*\n\s*', '- ', clean_body)
    clean_body = re.sub(r'^\s*[-•]+\s*$', '', clean_body, flags=re.MULTILINE)
    clean_body = re.sub(r'\n\s*-\s*', '\n- ', clean_body)

    return clean_body.strip()


def get_email_data(uid):
    raw_message = imap.fetch([uid], ['BODY[]', 'INTERNALDATE'])
    message = pyzmail.PyzMessage.factory(raw_message[uid][b'BODY[]'])
    date_obj = raw_message[uid][b'INTERNALDATE']
    date_str = date_obj.strftime("%Y-%m-%d %H:%M:%S")

    subject_raw = message.get_subject()
    subject_clean = re.sub(r'^(Re:|Fwd:)\s*', '', subject_raw, flags=re.IGNORECASE).strip()
    from_name, from_email = message.get_addresses('from')[0]
    body = clean_email_body(message)

    return {
        "uid": uid,
        "date": date_str,
        "from_name": from_name,
        "sender": from_email,
        "subject": subject_raw,
        "subject_clean": subject_clean,
        "body": body
    }


def get_thread_by_subject(subject_clean):
    UIDs = imap.search(['ALL'])
    thread = []

    for uid in UIDs:
        email_data = get_email_data(uid)
        if email_data['subject_clean'] == subject_clean:
            thread.append(email_data)

    thread.sort(key=lambda x: x['date'])
    return thread


try:
    while True:
        print("Choose an option:")
        print("1. Read and reply to unread emails")
        print("2. Show all conversation threads grouped by subject")
        print("3. Count emails from a specific sender and group by subject")
        print("4. Exit")

        choice = input("Enter your choice (1, 2, 3, or 4): ").strip()
        
        if not choice:
            print("Invalid option. Please enter a valid option: 1, 2, 3, or 4.")
            continue

        if choice == "1":
            UIDs = imap.search(['UNSEEN'])
            if not UIDs:
                print("No unread emails found.")
                continue
            
            for uid in UIDs:
                email_data = get_email_data(uid)
                
                print("\n" + "-" * 50)
                print(f"From: {email_data['from_name']} <{email_data['sender']}>")
                print(f"Subject: {email_data['subject']}")
                print("Fetching full thread...")

                thread = get_thread_by_subject(email_data['subject_clean'])

                print(json.dumps({email_data['subject_clean']: thread}, indent=4, ensure_ascii=False))

                reply = input("Do you want to reply to this email? (yes/no): ").strip().lower()
                if reply == "yes":
                    reply_text = input("Enter your reply:\n")

                    msg = MIMEMultipart()
                    msg['From'] = EMAIL
                    msg['To'] = email_data['sender']
                    msg['Subject'] = f"Re: {email_data['subject']}"
                    msg.attach(MIMEText(reply_text, 'plain'))

                    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                        server.starttls()
                        server.login(EMAIL, PASSWORD)
                        server.sendmail(EMAIL, email_data['sender'], msg.as_string())
                    print("Reply sent.")

                imap.add_flags([uid], [b'\\Seen'])
                
            input("\n Task complete. Press Enter to return to menu...")


        elif choice == "2":
            print("Fetching all emails to build conversation threads...")

            UIDs = imap.search(['ALL'])
            if not UIDs:
                print("No emails found.")
            else:
                threads = defaultdict(list)

                for uid in UIDs:
                    email_data = get_email_data(uid)
                    threads[email_data['subject_clean']].append(email_data)
                    
                for thread  in threads.values():
                    thread .sort(key=lambda x: x['date'])

                print("\nConversation Threads:\n" + "="*80)
                print(json.dumps(threads, indent=4, ensure_ascii=False))

            input("\nTask complete. Press Enter to return to menu...")
            
            
        elif choice == "3":
            sender_email = input("Enter sender email to filter: ").strip()
            UIDs = imap.search(['FROM', sender_email])

            if not UIDs:
                print(f"No emails found from {sender_email}")
            else:
                subject_counts = defaultdict(int)

                for uid in UIDs:
                    raw_message = imap.fetch([uid], ['BODY[]'])
                    message = pyzmail.PyzMessage.factory(raw_message[uid][b'BODY[]'])
                    subject = message.get_subject().strip()
                    subject_counts[subject] += 1

                print(f"\nTotal Emails from: {sender_email} = {len(UIDs)}")
                print("\nGrouped by Subject:")
                print("-" * 50)
                for subject, count in subject_counts.items():
                    print(f"{subject}: {count} message(s)")
                    
            input("\n Task complete. Press Enter to return to menu...")
            
            
        elif choice == "4":
            print("Goodbye!")
            os.system('cls' if os.name == 'nt' else 'clear')
            break
        
        else:
            print("Invalid option. Please enter 1, 2, 3, or 4.")
            
finally:
    imap.logout()
