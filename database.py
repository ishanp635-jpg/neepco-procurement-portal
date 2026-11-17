"""
NEEPCO Procurement & Vendor Payment Data Portal
Database Management & Initialization Module
"""

import os
import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'neepco_portal.db')


def get_db_connection():
    """Returns a SQLite database connection with row factory and foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """Initializes tables and seeds initial demo data if empty."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. Vendors Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id TEXT UNIQUE NOT NULL,
            vendor_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            vendor_category TEXT NOT NULL,
            mse_status TEXT NOT NULL
        );
    """)

    # 3. Procurement Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS procurement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            procurement_id TEXT UNIQUE NOT NULL,
            vendor_id INTEGER NOT NULL,
            purchase_order_number TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            procurement_amount REAL NOT NULL,
            procurement_type TEXT NOT NULL,
            financial_year TEXT NOT NULL,
            FOREIGN KEY (vendor_id) REFERENCES vendors (id) ON DELETE CASCADE
        );
    """)

    # 4. MSE Procurement Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mse_procurement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER NOT NULL,
            udyam_registration_number TEXT NOT NULL,
            procurement_amount REAL NOT NULL,
            date TEXT NOT NULL,
            financial_year TEXT NOT NULL,
            FOREIGN KEY (vendor_id) REFERENCES vendors (id) ON DELETE CASCADE
        );
    """)

    # 5. GeM Procurement Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gem_procurement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gem_order_id TEXT UNIQUE NOT NULL,
            vendor_id INTEGER NOT NULL,
            product_description TEXT NOT NULL,
            order_amount REAL NOT NULL,
            order_date TEXT NOT NULL,
            order_status TEXT NOT NULL,
            FOREIGN KEY (vendor_id) REFERENCES vendors (id) ON DELETE CASCADE
        );
    """)

    # 6. Payments Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER NOT NULL,
            invoice_number TEXT NOT NULL,
            invoice_amount REAL NOT NULL,
            amount_paid REAL NOT NULL,
            payment_date TEXT NOT NULL,
            payment_status TEXT NOT NULL,
            FOREIGN KEY (vendor_id) REFERENCES vendors (id) ON DELETE CASCADE
        );
    """)

    conn.commit()
    conn.close()

    # Seed demo records
    seed_demo_data()


def seed_demo_data():
    """Seeds initial demonstration data if tables are currently empty."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Seed Admin User if none exists
    cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
    if cursor.fetchone()[0] == 0:
        admin_pass_hash = generate_password_hash("admin123")
        cursor.execute("""
            INSERT INTO users (full_name, email, username, password_hash)
            VALUES (?, ?, ?, ?)
        """, ("NEEPCO Nodal Officer", "admin@neepco.gov.in", "admin", admin_pass_hash))

    # Check Vendors
    cursor.execute("SELECT COUNT(*) FROM vendors")
    vendor_count = cursor.fetchone()[0]

    if vendor_count == 0:
        # 5 Demo Vendors
        demo_vendors = [
            ('VEN-001', 'Brahmaputra Power Solutions Pvt Ltd', 'info@brahmaputrapower.in', '+91 94350 12345', 'Small', 'Yes'),
            ('VEN-002', 'Assam Electricals & Transformers', 'sales@assamelectricals.com', '+91 94351 67890', 'Medium', 'Yes'),
            ('VEN-003', 'Shillong Civil & Engineering Works', 'contact@shillongworks.org', '+91 98620 54321', 'Micro', 'Yes'),
            ('VEN-004', 'Eastern Heavy Turbines & Spares Ltd', 'support@easternturbines.co.in', '+91 98540 98765', 'Large Enterprise', 'No'),
            ('VEN-005', 'Meghalaya Green Energy Supplies', 'admin@meghalayagreen.com', '+91 97740 11223', 'Small', 'Yes')
        ]
        cursor.executemany("""
            INSERT INTO vendors (vendor_id, vendor_name, email, phone, vendor_category, mse_status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, demo_vendors)
        conn.commit()

        # Map vendor_id to database row ids
        cursor.execute("SELECT vendor_id, id FROM vendors")
        vendor_map = dict(cursor.fetchall())

        # 5 Demo Procurement records
        demo_procurement = [
            ('PROC-2024-001', vendor_map['VEN-001'], 'PO/NEEPCO/2024/081', '2024-05-15', 'Supply of 11kV Distribution Transformers and Switchgear', 1450000.00, 'Goods', '2024-25'),
            ('PROC-2024-002', vendor_map['VEN-003'], 'PO/NEEPCO/2024/095', '2024-06-20', 'Renovation and civil maintenance of substation building', 620000.00, 'Works', '2024-25'),
            ('PROC-2024-003', vendor_map['VEN-004'], 'PO/NEEPCO/2024/114', '2024-07-10', 'Hydro turbine runner blades and hydraulic overhaul spares', 4850000.00, 'Goods', '2024-25'),
            ('PROC-2024-004', vendor_map['VEN-002'], 'PO/NEEPCO/2024/130', '2024-08-05', 'Annual comprehensive maintenance contract for SCADA telemetry', 780000.00, 'Services', '2024-25'),
            ('PROC-2024-005', vendor_map['VEN-005'], 'PO/NEEPCO/2024/158', '2024-09-12', 'Environmental monitoring and solar auxiliary power panels', 950000.00, 'Goods', '2024-25')
        ]
        cursor.executemany("""
            INSERT INTO procurement (procurement_id, vendor_id, purchase_order_number, date, description, procurement_amount, procurement_type, financial_year)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, demo_procurement)

        # 3 Demo MSE Procurement records
        demo_mse = [
            (vendor_map['VEN-001'], 'UDYAM-AS-03-0012458', 1450000.00, '2024-05-15', '2024-25'),
            (vendor_map['VEN-003'], 'UDYAM-ML-01-0004921', 620000.00, '2024-06-20', '2024-25'),
            (vendor_map['VEN-005'], 'UDYAM-ML-02-0008763', 950000.00, '2024-09-12', '2024-25')
        ]
        cursor.executemany("""
            INSERT INTO mse_procurement (vendor_id, udyam_registration_number, procurement_amount, date, financial_year)
            VALUES (?, ?, ?, ?, ?)
        """, demo_mse)

        # 3 Demo GeM Procurement records
        demo_gem = [
            ('GEMC-5116877239101', vendor_map['VEN-001'], 'Industrial UPS & Battery Bank Systems 10kVA', 320000.00, '2024-05-22', 'Completed'),
            ('GEMC-5116877401923', vendor_map['VEN-002'], 'Digital Multimeters, Calibrators and Testing Equipments', 185000.00, '2024-07-02', 'Delivered'),
            ('GEMC-5116877892150', vendor_map['VEN-005'], 'Solar Inverters and Monocrystalline PV Modules', 540000.00, '2024-08-18', 'In Progress')
        ]
        cursor.executemany("""
            INSERT INTO gem_procurement (gem_order_id, vendor_id, product_description, order_amount, order_date, order_status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, demo_gem)

        # 5 Demo Payment records
        demo_payments = [
            (vendor_map['VEN-001'], 'INV/BPS/2024/041', 1450000.00, 1450000.00, '2024-06-05', 'Paid'),
            (vendor_map['VEN-003'], 'INV/SWE/2024/019', 620000.00, 400000.00, '2024-07-15', 'Partially Paid'),
            (vendor_map['VEN-004'], 'INV/EHT/2024/112', 4850000.00, 0.00, '2024-08-01', 'Pending'),
            (vendor_map['VEN-002'], 'INV/AET/2024/088', 780000.00, 780000.00, '2024-08-28', 'Paid'),
            (vendor_map['VEN-005'], 'INV/MGE/2024/056', 950000.00, 500000.00, '2024-09-30', 'Partially Paid')
        ]
        cursor.executemany("""
            INSERT INTO payments (vendor_id, invoice_number, invoice_amount, amount_paid, payment_date, payment_status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, demo_payments)

        conn.commit()

    conn.close()


if __name__ == '__main__':
    init_db()
    print("Database initialized and verified successfully.")
