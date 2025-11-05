# Wafeq Automation Developer – Technical Assessment Solution
This project implements an end-to-end integration with the **Wafeq API** to authenticate via OAuth2, retrieve invoices with pagination, and export results to a structured CSV file.

---

## 🚀 Features

- ✅ OAuth2 Authorization Code Flow
- 🔁 Automatic Token Refresh
- 📄 Invoice listing with Pagination (per Wafeq API)
- ⚙️ Configurable organization and page size via `.env`
- 💾 CSV export of invoices and line items

---

## 🧱 Project Structure

|     File    |   Description 
|-------------|--------------
| `config.py` | Handles OAuth2 flow: building authorization URL, receiving callback, exchanging code for tokens, and saving credentials to `.env`. 
| `fetch.py`  | Fetches invoices from the Wafeq API, supports pagination and CSV export, and refreshes tokens automatically when needed. 
|   `.env`    | Configuration file for API credentials, organization ID, and pagination settings. 

---

## ⚙️ Environment Variables

Create a `.env` file in the project root with the following content:

```bash
# OAuth credentials
AUTH_URL=https://app.wafeq.com/oauth/authorize/
TOKEN_URL=https://app.wafeq.com/oauth/token/
CLIENT_ID=your_client_id_here
CLIENT_SECRET=your_client_secret_here
REDIRECT_URI=http://localhost:3000/callback

# Tokens (auto-saved by config.py)
AUTH_CODE=
ACCESS_TOKEN=
REFRESH_TOKEN=

# API Configuration
BASE_URL=https://api.wafeq.com/v1
ORG_ID=co_yourOrganizationID
PAGE_SIZE=50
CSV_FILE=invoices.csv
```

---

## 🪜 How to Run

### 1️⃣ Authorize and Save Tokens  
Run once to authenticate via OAuth2 and save tokens to `.env`:

```bash
python config.py
```
This will:  
- Open your browser for **Wafeq login**  
- Receive the authorization code via `http://localhost:3000/callback`  
- Exchange it for an **access token** and **refresh token**  
- Save both to your `.env` file automatically  

---
### 2️⃣ Fetch and Export Invoices  

Once tokens are stored, run:

```bash
python fetch.py
```

This will:
- Retrieve invoices for the configured organization
- Handle pagination automatically (via next or page=...)
- Refresh the access token if it expires
- Display a formatted table in the console
- Export all invoice and line item data to `invoices.csv`

---

## 📊 Example Console Output
```markdown
----------------------------------------------------------------------------------------------------------------------------------
Invoice No      | Date       | Customer        | Status |       Description        |    Price    |  Qty |  Line Total
----------------------------------------------------------------------------------------------------------------------------------
INV-001         | 2025-11-04 | rose taha       | SENT   |     Design services      |   1000.00   |   2  |    2000.00
INV-002         | 2025-11-04 | Wafeq           | DRAFT  |     Subscription         |     50.00   |   1  |      50.00
----------------------------------------------------------------------------------------------------------------------------------
                                    Total invoices returned by API (all): 3
                                      Total non-deleted invoices shown: 2
----------------------------------------------------------------------------------------------------------------------------------
[CSV] saved to invoices.csv
```
---

## 🧩 Notes  

- The code auto-detects the **Wafeq API pagination style** (`next` link or `?page=` pattern).  
- The **access token refresh** logic is fully implemented for long-running sessions.  
- The `.env` file is automatically updated with the latest tokens.  
- **CSV export** ensures data can be reused for reports or analysis.  
- **DELETED** invoices are ignored

---



