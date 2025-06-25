import imapclient

EMAIL = "your@gmail.com"
PASSWORD = "password"
IMAP_SERVER = "imap.gmail.com"

try:
    imap = imapclient.IMAPClient(IMAP_SERVER, port=993, ssl=True)
    imap.login(EMAIL, PASSWORD)
    print("IMAP login successful!")
    imap.logout()
except Exception as e:
    print("IMAP login failed:", e)
