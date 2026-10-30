"""Interactive saved-vehicle menu using your existing application account."""

import argparse
import getpass
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.support.local_api import ApiError, LocalApi


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    args = parser.parse_args()
    client = LocalApi(args.base_url)
    client.request("/api/auth/csrf")
    signed = client.request("/api/auth/login", {"email": input("Application email: ").strip(),
                                               "password": getpass.getpass("Application password (hidden): ")})
    print(f"Signed in as {signed['user']['email']}.")
    try:
        while True:
            print("\n1 List my saved vehicles\n2 Save a vehicle\n3 Rename a saved vehicle\n4 Remove a saved vehicle\n0 Sign out and exit")
            action = input("Choose: ").strip()
            if action == "0":
                break
            try:
                if action == "1":
                    result = client.request("/api/saved-vehicles?pageSize=100")
                    for item in result["items"]:
                        vehicle = item["vehicle"]
                        print(f"{item['savedVehicleId']}: {vehicle['year']} {vehicle['make']} {vehicle['model']} — {item['nickname'] or '(no nickname)'}")
                    print(f"Showing {len(result['items'])} of {result['pagination']['total']} saved vehicles.")
                elif action == "2":
                    year = int(input("Model year: "))
                    make, model = input("Make: ").strip(), input("Model: ").strip()
                    found = client.request("/api/vehicles/search?" + urlencode({"year": year, "make": make, "model": model}))
                    if not found["items"]:
                        print("No matching vehicle in the imported catalogue.")
                        continue
                    item = client.request("/api/saved-vehicles", {"modelYearId": found["items"][0]["modelYearId"],
                                                                 "nickname": input("Nickname (optional): ")})["savedVehicle"]
                    print(f"Saved vehicle {item['savedVehicleId']}.")
                elif action == "3":
                    saved_id = int(input("Saved vehicle ID: "))
                    client.request(f"/api/saved-vehicles/{saved_id}", {"nickname": input("New nickname (blank clears it): ")}, method="PATCH")
                    print("Nickname updated.")
                elif action == "4":
                    saved_id = int(input("Saved vehicle ID: "))
                    client.request(f"/api/saved-vehicles/{saved_id}", method="DELETE")
                    print("Saved vehicle removed.")
                else:
                    print("Choose one of the displayed options.")
            except ApiError as error:
                print(f"HTTP {error.status}: {error}")
                if error.status == 401:
                    break
            except ValueError:
                print("Use a numeric model year or saved vehicle ID.")
    finally:
        try:
            client.request("/api/auth/logout", {})
        except ApiError as error:
            if error.status != 401:
                raise
        print("Signed out. Saved vehicles remain unless you removed them.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, URLError) as error:
        raise SystemExit(str(error))
    except (KeyboardInterrupt, EOFError):
        raise SystemExit("\nStopped.")
