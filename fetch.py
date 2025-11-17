import os
import csv
import requests
from functools import lru_cache
from dotenv import load_dotenv
from dotenv import set_key

load_dotenv()

# ENV VARIABLES
BASE_URL = os.getenv("BASE_URL")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
TOKEN_URL = os.getenv("TOKEN_URL")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
PAGE_SIZE = int(os.getenv("PAGE_SIZE", "50"))
CSV_FILE = os.getenv("CSV_FILE", "invoices.csv")

def save_tokens(access_token: str, refresh_token: str | None):
    """
    Save updated tokens into .env for future runs.
    """
    set_key(".env", "ACCESS_TOKEN", access_token)
    if refresh_token:
        set_key(".env", "REFRESH_TOKEN", refresh_token)

def refresh_access_token() -> str:
    """
    Refresh access token using the refresh token when it expires.
    """
    global ACCESS_TOKEN, REFRESH_TOKEN
    if not REFRESH_TOKEN:
        raise RuntimeError("No refresh token available")

    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    resp = requests.post(TOKEN_URL, data=data, timeout=15)
    resp.raise_for_status()
    d = resp.json()
    ACCESS_TOKEN = d["access_token"]
    REFRESH_TOKEN = d.get("refresh_token", REFRESH_TOKEN)
    save_tokens(ACCESS_TOKEN, REFRESH_TOKEN)
    return ACCESS_TOKEN

def api_get(path_or_url: str, params: dict | None = None) -> requests.Response:
    """
    Make an authenticated GET request, refreshing token if needed.
    """
    global ACCESS_TOKEN
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        url = path_or_url
    else:
        url = f"{BASE_URL}{path_or_url}"

    resp = requests.get(url, headers=headers, params=params, timeout=15)

    if resp.status_code == 401:
        refresh_access_token()
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        resp = requests.get(url, headers=headers, params=params, timeout=15)

    return resp

@lru_cache(maxsize=None)
def get_contact_name(contact_id: str) -> str:
    """
    Return contact name for a given id, using an in-memory cache
    to avoid repeated API calls for the same contact.
    """
    if not contact_id:
        return "—"
    resp = api_get(f"/contacts/{contact_id}/")
    if not resp.ok:
        return f"id:{contact_id}"
    data = resp.json()
    return data.get("name") or data.get("display_name") or f"id:{contact_id}"

# def get_invoice_detail(invoice_id: str) -> dict:
#     """
#     Fetch full invoice details.
#     """
#     resp = api_get(f"/invoices/{invoice_id}/")
#     if not resp.ok:
#         return {}
#     return resp.json()

def list_invoices():
    header_str = (
        f"{'Invoice No':<15} | {'Date':<10} | {'Customer':<15} | "
        f"{'Status':<8} | {'Description':<20} | {'Price':>10} | {'Qty':>5} | {'Line Total':>10}"
    )
    print("-" * len(header_str))
    print(header_str)
    print("-" * len(header_str))

    csv_rows = []
    total_from_api = 0
    total_kept = 0

    page = 1
    next_url = None
    prev_next = None
    seen_ids = set()
    MAX_PAGES = 500

    while page <= MAX_PAGES:
        # ---------- Fetch one page ----------
        if next_url:
            resp = api_get(next_url)
        else:
            params = {"page": page}
            if PAGE_SIZE:
                params["page_size"] = PAGE_SIZE
            resp = api_get("/invoices/", params=params)

        if resp.status_code == 404:
            break
        if not resp.ok:
            print(f"[error] page {page}: {resp.status_code} {resp.text}")
            break

        data = resp.json()
        invoices = data.get("results") or data.get("invoices") or data or []
        next_url = data.get("next") if isinstance(data, dict) else None

        # stop if no new ids (API repeating same page)
        new_ids = [inv.get("id") for inv in invoices if inv.get("id") not in seen_ids]
        if not new_ids:
            break
        for _id in new_ids:
            if _id:
                seen_ids.add(_id)

        total_from_api += len(invoices)
        visible_in_page = 0

        # ---------- Process invoices in this page ----------
        for inv in invoices:
            inv_id = inv.get("id")
            if not inv_id:
                continue

            status_raw = inv.get("status") or ""
            status_lower = status_raw.lower()

            # skip deleted / archived
            if status_lower in ("deleted", "delete", "archived"):
                continue

            inv_no = (
                inv.get("invoice_number")
                or inv.get("number")
                or ""
            )
            date = inv.get("invoice_date") or inv.get("date") or ""

            contact_id = inv.get("contact") or inv.get("contact_id")
            customer = get_contact_name(contact_id) if contact_id else "—"

            status = status_raw or "-"
            line_items = inv.get("line_items")
            
            visible_in_page += 1
            total_kept += 1

            if not line_items:
                print(
                    f"{inv_no:<15} | {date:<10} | {customer:<15} | "
                    f"{status:<8} | {'-':<20} | {'-':>10} | {'-':>5} | {'-':>10}"
                )
                csv_rows.append([inv_no, date, customer, status, "-", "", "", ""])
                continue

            # Print line items
            for item in line_items:
                desc = item.get("description") or item.get("name") or "-"
                qty = item.get("quantity") or 1
                line_amount = item.get("line_amount") or 0
                unit_price = line_amount / qty if qty else line_amount

                print(
                    f"{inv_no:<15} | {date:<10} | {customer:<15} | "
                    f"{status:<8} | {desc:<20.20} | "
                    f"{unit_price:>10.2f} | {qty:>5} | {line_amount:>10.2f}"
                )
                csv_rows.append(
                    [
                        inv_no,
                        date,
                        customer,
                        status,
                        desc,
                        f"{unit_price:.2f}",
                        qty,
                        f"{line_amount:.2f}",
                    ]
                )

        if visible_in_page:
            print("-" * len(header_str))

        # ---------- Next page ----------
        if next_url:
            if next_url == prev_next:
                break
            prev_next = next_url
        else:
            page += 1

    # ---------- Summary ----------
    print(f"Total invoices returned by API (all): {total_from_api}".center(len(header_str)))
    print(f"Total non-deleted invoices shown: {total_kept}".center(len(header_str)))
    print("-" * len(header_str))

    # ---------- CSV ----------
    if csv_rows:
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "invoice_number",
                    "date",
                    "customer",
                    "status",
                    "description",
                    "unit_price",
                    "qty",
                    "line_total",
                ]
            )
            writer.writerows(csv_rows)
        print(f"[CSV] saved to {CSV_FILE}")

if __name__ == "__main__":
    if not ACCESS_TOKEN:
        print("[error] ACCESS_TOKEN not set. Run config.py first.")
    else:
        list_invoices()
