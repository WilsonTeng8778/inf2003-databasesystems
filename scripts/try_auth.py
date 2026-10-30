"""Try registration/login/me/logout against a running localhost Flask server."""

import argparse
import getpass
import sys
from pathlib import Path
from urllib.error import URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.support.local_api import LocalApi


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--register", action="store_true", help="Create a normal account before testing sign-in state")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    args = parser.parse_args()
    client = LocalApi(args.base_url)
    # Connect first so passwords are not requested when the server is stopped.
    client.request("/api/auth/csrf")
    email = input("Email: ").strip()
    password = getpass.getpass("Password (hidden): ")
    path = "/api/auth/register" if args.register else "/api/auth/login"
    client.request(path, {"email": email, "password": password})
    try:
        user = client.request("/api/auth/me")["user"]
        print(f"Signed in as {user['email']} — role: {user['role']}")
        if args.register:
            print("Account created. It remains available for later login.")
    finally:
        client.request("/api/auth/logout", {})
        print("Signed out; this demo's session was revoked.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, URLError) as error:
        raise SystemExit(str(error))
