# NEEPCO Procurement Data Portal & Vendor Payment Data Portal

An enterprise-grade, simple, and functional Academic Major Project built for **North Eastern Electric Power Corporation Limited (NEEPCO)**, a Schedule-'A' Mini Ratna CPSE under the Ministry of Power, Government of India.

The portal automates and monitors public procurement contracts, compliance with the **Public Procurement Policy for Micro and Small Enterprises (MSEs)**, orders from the **Government e-Marketplace (GeM)**, and **Vendor Payment disbursements** with automatic computation of outstanding liabilities.

---

## 🌟 Technology Stack

- **Backend:** Python 3 (Flask Framework)
- **WSGI Production Server:** Gunicorn 21+
- **Database:** SQLite3 (Configurable via `DATABASE_PATH`, auto-seeding without duplication)
- **Authentication:** Flask Sessions with `werkzeug.security` (PBKDF2/SHA-256 password hashing)
- **Frontend:** HTML5, CSS3, JavaScript (ES6)
- **UI Framework:** Bootstrap 5.3.3 + Bootstrap Icons 1.11.3
- **Data Visualizations:** Chart.js 4.4
- **Reporting:** Built-in dynamic CSV export engine

---

## 📁 Project Folder Structure

```
neepco_portal/
│
├── app.py                     # Main Flask web application, route controllers & API logic
├── database.py                # Database connection, schema definition & seed data loader
├── test_portal.py             # Automated unit and integration test suite
├── test_render_config.py      # Render production deployment configuration tests
├── requirements.txt           # Python package dependencies (Flask, Werkzeug, Gunicorn)
├── Procfile                   # Process file for Render / Gunicorn
├── render.yaml                # Render Blueprint Infrastructure-as-Code specification
├── neepco.db                  # Relational SQLite database file (auto-generated)
├── README.md                  # Complete documentation and deployment guide
│
├── static/
│   ├── css/
│   │   └── style.css          # Government-PSU Navy/Gold responsive design theme
│   └── js/
│       └── main.js            # Table search filters, alerts auto-dismiss, modals
│
└── templates/
    ├── base.html              # Base layout with PSU branding, top navbar & sidebar
    ├── dashboard.html         # Executive dashboard with 6 KPI cards & 4 Chart.js charts
    │
    ├── auth/
    │   ├── login.html         # Officer login page with credentials helper
    │   └── signup.html        # Officer registration page with field validation
    │
    ├── procurement/
    │   └── index.html         # Procurement contracts registry, search, FY filter & modal
    │
    ├── mse/
    │   └── index.html         # MSE procurement tracking & % compliance scoreboard
    │
    ├── gem/
    │   └── index.html         # GeM orders management & order status updater
    │
    ├── vendors/
    │   └── index.html         # Registered supplier directory with edit & delete modals
    │
    ├── payments/
    │   └── index.html         # Vendor invoices, payments & auto-calculated outstanding
    │
    └── reports/
        ├── index.html         # Central statutory reports hub
        ├── procurement.html   # Total Procurement Report with CSV download
        ├── mse.html           # MSE Procurement Audit Report with CSV download
        ├── gem.html           # GeM Fulfillment Report with CSV download
        └── payments.html      # Vendor Liabilities & Aging Report with CSV download
```

---

## ☁️ Deployment on Render

This application is fully production-ready for deployment on **[Render](https://render.com)**.

### Deployment Parameters Summary

| Setting | Value |
| :--- | :--- |
| **Environment / Runtime** | `Python` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn --bind 0.0.0.0:$PORT app:app` |
| **Flask Entry Point** | `app.py` |
| **Flask Application Callable** | `app` |

---

### Step-by-Step Render Deployment Guide

#### Method 1: Using the Render Web Dashboard (Recommended)

1. **Push your code to GitHub / GitLab:**
   Ensure `app.py`, `database.py`, `requirements.txt`, `Procfile`, `templates/`, and `static/` are committed and pushed to your Git repository.

2. **Create a New Web Service on Render:**
   - Go to your [Render Dashboard](https://dashboard.render.com/).
   - Click **New +** and select **Web Service**.
   - Connect your GitHub repository containing the project.

3. **Configure Service Details:**
   - **Name:** `neepco-portal` (or any chosen name)
   - **Region:** Any preferred region (e.g., Oregon, Frankfurt, Singapore)
   - **Branch:** `main`
   - **Runtime:** `Python 3`
   - **Build Command:**
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command:**
     ```bash
     gunicorn --bind 0.0.0.0:$PORT app:app
     ```

4. **Configure Environment Variables:**
   Under the **Environment Variables** section, add:
   
   | Key | Value | Description |
   | :--- | :--- | :--- |
   | `PYTHON_VERSION` | `3.11.9` | Ensures a stable Python 3 runtime on Render. |
   | `SECRET_KEY` | *(Generate a 32+ char random string)* | Used by Flask sessions to sign session cookies. |
   | `DATABASE_PATH` | `/var/data/neepco.db` | Absolute path where SQLite database is stored. |
   | `FLASK_DEBUG` | `False` | Disables debug mode in production. |

   > **Generating a strong SECRET_KEY:**
   > You can generate a secure key in your terminal using:
   > ```bash
   > python -c "import secrets; print(secrets.token_hex(32))"
   > ```

5. **Attach Persistent Storage (Crucial for SQLite Data Persistence):**
   *Note: Standard cloud containers are ephemeral; without a persistent disk, database files created inside the container will reset on every redeploy.*
   - In your Render Web Service settings, go to the **Disks** tab.
   - Click **Add Disk**.
   - **Name:** `neepco-data`
   - **Mount Path:** `/var/data`
   - **Size:** `1 GB` (sufficient for hundreds of thousands of records).
   - Save changes.
   - The application automatically ensures that when `DATABASE_PATH=/var/data/neepco.db` is configured, `/var/data` is detected, existing data is preserved, and tables are created automatically without erasing previous records!

6. **Deploy:**
   Click **Create Web Service**. Render will install requirements, start Gunicorn, and provide your live HTTPS URL (e.g. `https://neepco-portal.onrender.com`).

---

#### Method 2: Deploy Using Render Blueprint (`render.yaml`)

This repository contains a pre-configured [`render.yaml`](file:///C:/Users/admin/.gemini/antigravity/scratch/neepco_portal/render.yaml) file.
1. On Render, click **New +** $\rightarrow$ **Blueprint**.
2. Connect your Git repository.
3. Render will automatically parse `render.yaml`, configure the Web Service, attach the `/var/data` persistent disk, generate a secure `SECRET_KEY`, and deploy with Gunicorn.

---

## 🔑 Demo Login Credentials

The application automatically seeds demo records if the database is newly initialized:

| Field | Credentials |
| :--- | :--- |
| **Username** | `admin` *(or email: `admin@neepco.gov.in`)* |
| **Password** | `admin123` |
| **Designation** | Er. R. K. Sharma, Chief General Manager (Procurement) |

> **User Registration:** You can register additional officer accounts at any time via `/signup`.

---

## 💻 Running Locally

### Step 1: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 2: Run Application
```powershell
python app.py
```
Or with custom local environment variables:
```powershell
$env:PORT="5000"
$env:FLASK_DEBUG="True"
python app.py
```
Open **`http://127.0.0.1:5000`** in your browser.

---

## 🧪 Automated Testing

Run the included automated test suites:

```powershell
# 1. Full portal features, authentication, CRUD, and CSV exports
python test_portal.py

# 2. Render deployment, DATABASE_PATH directory auto-creation, and restart idempotency
python test_render_config.py
```
Output:
```
Ran 9 tests in 1.379s
OK
[PASS] Unauthorized access protection verified for all routes.
[PASS] Admin login verified successfully.
[PASS] User signup and login verified successfully.
[PASS] Procurement add and listing verified.
[PASS] MSE procurement add and formula percentage verified.
[PASS] GeM order creation verified.
[PASS] Vendor management verified.
[PASS] Payment partial status & outstanding formula verified.
[PASS] All 4 CSV export reports tested and verified.
```
