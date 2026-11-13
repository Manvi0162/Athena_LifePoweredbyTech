"""Log in as a Supabase user and print the access token, for testing the API
in /docs (click Authorize and paste it). The token expires after about an hour.

    python tools/get_token.py
"""
import os
from getpass import getpass

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_PUBLISHABLE_KEY"])
session = client.auth.sign_in_with_password({
    "email": input("Demo user email: ").strip(),
    "password": getpass("Demo user password: "),
}).session
print("\nAccess token (paste into Authorize in /docs):\n")
print(session.access_token)
