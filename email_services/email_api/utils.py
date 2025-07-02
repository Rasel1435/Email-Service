import html
import re
import requests
from email.mime.text import MIMEText
import base64
from django.conf import settings


def refresh_access_token(user):
    user_auth = user.social_auth.filter(provider='google-oauth2').first()
    if not user_auth:
        return None

    refresh_token = user_auth.extra_data.get('refresh_token')
    if not refresh_token:
        return None

    data = {
        'client_id': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY,
        'client_secret': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token',
    }

    resp = requests.post('https://oauth2.googleapis.com/token', data=data)
    if resp.status_code == 200:
        new_token = resp.json().get('access_token')
        user_auth.extra_data['access_token'] = new_token
        user_auth.save()
        return new_token
    else:
        print("Refresh token error:", resp.text)
        return None


def get_gmail_token(user):
    user_auth = user.social_auth.filter(provider='google-oauth2').first()
    if not user_auth:
        return None

    access_token = user_auth.extra_data.get('access_token')
    new_token = refresh_access_token(user)
    return new_token or access_token



def clean_email_body(body):
    """
    Clean raw email body text to remove html tags, excess whitespace, etc.
    """
    clean_body = body.replace('\r\n', '\n').replace('\xa0', ' ')
    clean_body = html.unescape(clean_body)
    clean_body = re.sub(r'<[^>]+>', '', clean_body)
    clean_body = re.sub(r'\u2060', '', clean_body)
    clean_body = re.sub(r'[ \t]+$', '', clean_body, flags=re.MULTILINE)
    clean_body = re.sub(r'\n{3,}', '\n\n', clean_body)
    clean_body = re.sub(r'-\s*\n\s*', '- ', clean_body)
    clean_body = re.sub(r'^\s*[-\u2022]+\s*$', '', clean_body, flags=re.MULTILINE)
    clean_body = re.sub(r'\n\s*-\s*', '\n- ', clean_body)

    return clean_body.strip()


def fetch_all_inbox_emails(user):
    """
    Fetch all unread emails from the user's Gmail inbox.
    Returns a dict grouped by threadId, each with subject and message list.
    """
    access_token = get_gmail_token(user)
    if not access_token:
        return {"error": "User not authenticated with Gmail."}

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json',
    }

    params = {
        'q': 'in:inbox',
        'maxResults': 100
    }

    search_url = 'https://gmail.googleapis.com/gmail/v1/users/me/messages'
    resp = requests.get(search_url, headers=headers, params=params)
    if resp.status_code != 200:
        print("Gmail API Error:", resp.status_code, resp.text)
        return {"error": "Failed to fetch unread emails."}

    messages = resp.json().get('messages', [])
    threads = {}

    for msg in messages:
        msg_id = msg['id']
        msg_url = f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}'
        msg_resp = requests.get(msg_url, headers=headers)
        if msg_resp.status_code != 200:
            continue
        msg_data = msg_resp.json()

        headers_list = msg_data.get('payload', {}).get('headers', [])
        subject = next((h['value'] for h in headers_list if h['name'] == 'Subject'), 'No Subject')
        from_email = next((h['value'] for h in headers_list if h['name'] == 'From'), '')
        date = next((h['value'] for h in headers_list if h['name'] == 'Date'), '')
        thread_id = msg_data.get('threadId')

        body = ''
        parts = msg_data.get('payload', {}).get('parts', [])
        if not parts:
            body = msg_data.get('payload', {}).get('body', {}).get('data', '')
        else:
            for part in parts:
                if part['mimeType'] == 'text/plain':
                    body = part['body'].get('data', '')
                    break

        if body:
            try:
                body = base64.urlsafe_b64decode(body).decode('utf-8')
            except Exception:
                body = ''

        thread_data = {
            'id': msg_id,
            'thread_id': thread_id,
            'from_email': from_email,
            'subject': subject,
            'date': date,
            'body': clean_email_body(body),
        }
        if thread_id not in threads:
            threads[thread_id] = {
                'subject': subject,
                'messages': []
            }
        threads[thread_id]['messages'].append(thread_data)

    for thread in threads.values():
        thread['messages'].sort(key=lambda x: x['date'])

    return threads


def fetch_email_threads(user, sender_email):
    """
    Fetch emails from a specific sender email.
    Returns emails grouped by threadId with subject and message list.
    """
    access_token = get_gmail_token(user)
    if not access_token:
        return {"error": "User not authenticated with Gmail."}

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json',
    }

    params = {
        'q': f'from:{sender_email}',
        'maxResults': 100
    }

    search_url = 'https://gmail.googleapis.com/gmail/v1/users/me/messages'
    resp = requests.get(search_url, headers=headers, params=params)
    if resp.status_code != 200:
        print("Gmail API Error:", resp.status_code, resp.text)
        return {"error": "Failed to fetch email list."}

    messages = resp.json().get('messages', [])
    threads = {}

    for msg in messages:
        msg_id = msg['id']
        msg_url = f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}'
        msg_resp = requests.get(msg_url, headers=headers)
        if msg_resp.status_code != 200:
            continue
        msg_data = msg_resp.json()

        headers_list = msg_data.get('payload', {}).get('headers', [])
        subject = next((h['value'] for h in headers_list if h['name'] == 'Subject'), 'No Subject')
        from_email = next((h['value'] for h in headers_list if h['name'] == 'From'), '')
        date = next((h['value'] for h in headers_list if h['name'] == 'Date'), '')
        thread_id = msg_data.get('threadId')

        body = ''
        parts = msg_data.get('payload', {}).get('parts', [])
        if not parts:
            body = msg_data.get('payload', {}).get('body', {}).get('data', '')
        else:
            for part in parts:
                if part['mimeType'] == 'text/plain':
                    body = part['body'].get('data', '')
                    break

        if body:
            try:
                body = base64.urlsafe_b64decode(body).decode('utf-8')
            except Exception:
                body = ''

        thread_data = {
            'id': msg_id,
            'thread_id': thread_id,
            'from_email': from_email,
            'subject': subject,
            'date': date,
            'body': clean_email_body(body),
        }
        if thread_id not in threads:
            threads[thread_id] = {
                'subject': subject,
                'messages': []
            }
        threads[thread_id]['messages'].append(thread_data)

    for thread in threads.values():
        thread['messages'].sort(key=lambda x: x['date'])

    return threads


def send_email(user, to, subject, body, thread_id=None):
    """
    Send an email via Gmail API.
    If thread_id is provided, sends as reply to that thread.
    """
    access_token = get_gmail_token(user)
    if not access_token:
        return {"error": "User not authenticated with Gmail."}

    message = MIMEText(body)
    message['to'] = to
    message['subject'] = subject or 'No Subject'

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    
    email_data = {'raw': raw}
    if thread_id:
        email_data['threadId'] = thread_id

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json',
    }

    send_url = 'https://gmail.googleapis.com/gmail/v1/users/me/messages/send'
    send_resp = requests.post(send_url, headers=headers, json=email_data)

    if send_resp.status_code == 200:
        return {"message": "Email sent successfully."}
    else:
        print("Send Email Error:", send_resp.status_code, send_resp.text)
        return {"error": "Failed to send email."}
