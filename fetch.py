import os
import csv
import requests
from dotenv import load_dotenv

load_dotenv()

# ENV variables
BASE_URL = os.getenv("BASE_URL")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
TOKEN_URL = os.getenv("TOKEN_URL")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
ORG_ID = os.getenv("ORG_ID") 
PAGE_SIZE = int(os.getenv("PAGE_SIZE", "50"))  

CSV_FILE = os.getenv("CSV_FILE", "invoices.csv")


# -------------- helpers -------------- #
def save_tokens(access_token: str, refresh_token: str | None):
    from dotenv import set_key

    set_key(".env", "ACCESS_TOKEN", access_token)
    if refresh_token:
        set_key(".env", "REFRESH_TOKEN", refresh_token)


def refresh_access_token() -> str:
    global ACCESS_TOKEN, REFRESH_TOKEN
    if not REFRESH_TOKEN:
        raise RuntimeError("No refresh token available")

    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    resp = requests.post(TOKEN_URL, data=data, timeout=30)
    resp.raise_for_status()
    d = resp.json()
    ACCESS_TOKEN = d["access_token"]
    REFRESH_TOKEN = d.get("refresh_token", REFRESH_TOKEN)
    save_tokens(ACCESS_TOKEN, REFRESH_TOKEN)
    print("[fetch] access token refreshed")
    return ACCESS_TOKEN


def api_get(path_or_url: str, params: dict | None = None) -> requests.Response:
    global ACCESS_TOKEN
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        url = path_or_url
    else:
        url = f"{BASE_URL}{path_or_url}"

    resp = requests.get(url, headers=headers, params=params, timeout=30)

    if resp.status_code == 401:
        refresh_access_token()
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        resp = requests.get(url, headers=headers, params=params, timeout=30)

    return resp


# -------------- API specific -------------- #
def get_contact_name(contact_id: str) -> str:
    if not contact_id:
        return "—"
    resp = api_get(f"/contacts/{contact_id}/")
    if not resp.ok:
        return f"id:{contact_id}"
    data = resp.json()
    return data.get("name") or data.get("display_name") or f"id:{contact_id}"


def get_invoice_detail(invoice_id: str) -> dict:
    resp = api_get(f"/invoices/{invoice_id}/")
    if not resp.ok:
        return {}
    return resp.json()


def list_invoices():
    total_invoices = 0
    csv_rows = []

    # Print header
    header_str = f"{'Invoice ID':<26} | {'Date':<10} | {'Customer':<15} | {'Status':<6} | {'Total':>10} | {'Description':<20} | {'Qty':>5} | {'Line Total':>10}"
    print("-" * len(header_str))
    print(header_str)
    print("-" * len(header_str))

    # Start fetching pages
    page = 1
    next_url = None  

    while True:
        if next_url:
            resp = api_get(next_url)
        else:
            params = {"page": page}
            if PAGE_SIZE:
                params["page_size"] = PAGE_SIZE
            if ORG_ID:
                params["organization"] = ORG_ID
            resp = api_get("/invoices/", params=params)

        if resp.status_code == 404:
            break

        if not resp.ok:
            print(f"[page {page}] error {resp.status_code}: {resp.text}")
            break

        data = resp.json()

        if isinstance(data, dict):
            invoices = data.get("results") or data.get("invoices") or []
            next_url = data.get("next")  
        else:
            invoices = data
            next_url = None

        if not invoices:
            break

        total_invoices += len(invoices)

        for inv in invoices:
            inv_id = inv.get("id")
            date = inv.get("invoice_date") or inv.get("date")
            contact_id = inv.get("contact") or inv.get("contact_id")
            customer = get_contact_name(contact_id) if contact_id else "—"
            total = inv.get("total") or inv.get("grand_total") or inv.get("amount") or 0
            status = inv.get("status") or "-"

            detail = get_invoice_detail(inv_id)
            line_items = detail.get("line_items", [])

            if not line_items:
                # Print on terminal
                print(
                    f"{inv_id:<26} | {date:<10} | {customer:<15} | {status:<6} | {total:>10.2f} | {'-':<20} | {'-':>5} | {'-':>10}"
                )
                # CSV saving 
                csv_rows.append(
                    [
                        inv_id,
                        date,
                        customer,
                        status,
                        f"{total:.2f}",
                        "-",
                        "",
                        "",
                    ]
                )
                continue

            for item in line_items:
                desc = item.get("description") or item.get("name") or "-"
                qty = item.get("quantity") or item.get("qty") or 1
                line_amount = (
                    item.get("line_amount")
                    or item.get("amount")
                    or item.get("total")
                    or 0
                )

                # Print on terminal
                print(
                    f"{inv_id:<26} | {date:<10} | {customer:<15} | {status:<6} | {total:>10.2f} | {desc:<20.20} | {qty:>5} | {line_amount:>10.2f}"
                )

                # CSV saving
                csv_rows.append(
                    [
                        inv_id,
                        date,
                        customer,
                        status,
                        f"{total:.2f}",
                        desc,
                        qty,
                        f"{line_amount:.2f}",
                    ]
                )

        print("-" * len(header_str))

        if not next_url:
            page += 1


    #  End of fetching - terminal summary
    print(f"Total invoices fetched: {total_invoices}".center(len(header_str)))
    print("-" * len(header_str))

    # End of fetching - save to CSV
    if csv_rows:
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "invoice_id",
                    "date",
                    "customer",
                    "status",
                    "total",
                    "description",
                    "qty",
                    "line_total",
                ]
            )
            writer.writerows(csv_rows)
        print(f"[CSV] saved to {CSV_FILE}")
    else:
        print("[CSV] no rows to write.")


if __name__ == "__main__":
    list_invoices()
