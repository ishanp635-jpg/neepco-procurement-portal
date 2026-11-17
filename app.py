"""
NEEPCO Procurement Data Portal and Vendor Payment Data Portal
Main Application Controller
"""

import os
import csv
import io
from functools import wraps
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
)
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection, init_db

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'neepco_secure_portal_key_2025_academic_project')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'


# ---------------------------------------------------------
# Jinja Filters & Context Processors
# ---------------------------------------------------------
@app.template_filter('inr')
def inr_format(value):
    """Formats a number as Indian Currency format with commas: e.g. 14,50,000.00"""
    try:
        val = float(value)
        # Format with 2 decimals
        formatted_base = f"{val:,.2f}"
        return f"₹ {formatted_base}"
    except (ValueError, TypeError):
        return f"₹ 0.00"


@app.template_filter('number_only')
def number_only(value):
    """Formats a number with commas without the rupee sign."""
    try:
        val = float(value)
        return f"{val:,.2f}"
    except (ValueError, TypeError):
        return "0.00"


@app.context_processor
def inject_global_data():
    """Injects current logged-in user and portal branding into all templates."""
    return {
        'logged_in': 'user_id' in session,
        'current_user': session.get('full_name', 'Guest'),
        'current_username': session.get('username', ''),
        'portal_title': "NEEPCO Procurement & Vendor Payment Portal",
        'current_year': datetime.now().year
    }


# ---------------------------------------------------------
# Authentication Decorator
# ---------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this portal section.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ---------------------------------------------------------
# 1. User Authentication Module
# ---------------------------------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validations
        if not full_name or not email or not username or not password or not confirm_password:
            flash("All fields are required.", "danger")
            return render_template('register.html', full_name=full_name, email=email, username=username)

        if password != confirm_password:
            flash("Passwords do not match. Please verify and try again.", "danger")
            return render_template('register.html', full_name=full_name, email=email, username=username)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "warning")
            return render_template('register.html', full_name=full_name, email=email, username=username)

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check existing username or email
        existing_user = cursor.execute(
            "SELECT id FROM users WHERE username = ? OR email = ?",
            (username, email)
        ).fetchone()

        if existing_user:
            conn.close()
            flash("Username or Email is already registered. Please choose another or login.", "danger")
            return render_template('register.html', full_name=full_name, email=email, username=username)

        password_hash = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (full_name, email, username, password_hash)
            VALUES (?, ?, ?, ?)
        """, (full_name, email, username, password_hash))
        conn.commit()
        conn.close()

        flash("Registration successful! You may now log in with your credentials.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        login_id = request.form.get('login_id', '').strip().lower()
        password = request.form.get('password', '')

        if not login_id or not password:
            flash("Please enter both username/email and password.", "warning")
            return render_template('login.html', login_id=login_id)

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE LOWER(username) = ? OR LOWER(email) = ?",
            (login_id, login_id)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['email'] = user['email']
            flash(f"Welcome back, {user['full_name']}! Authentication successful.", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials. Please check your username/email and password.", "danger")
            return render_template('login.html', login_id=login_id)

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("You have been securely logged out.", "info")
    return redirect(url_for('login'))


# ---------------------------------------------------------
# 2. Dashboard
# ---------------------------------------------------------
@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()

    # 1. Total procurement value
    total_procurement = conn.execute("SELECT COALESCE(SUM(procurement_amount), 0) FROM procurement").fetchone()[0]

    # 2. Total MSE procurement
    total_mse = conn.execute("SELECT COALESCE(SUM(procurement_amount), 0) FROM mse_procurement").fetchone()[0]

    # 3. Total GeM procurement
    total_gem = conn.execute("SELECT COALESCE(SUM(order_amount), 0) FROM gem_procurement").fetchone()[0]

    # 4. Total vendors
    total_vendors = conn.execute("SELECT COUNT(*) FROM vendors").fetchone()[0]

    # 5. Total payments
    total_payments_paid = conn.execute("SELECT COALESCE(SUM(amount_paid), 0) FROM payments").fetchone()[0]
    total_invoiced = conn.execute("SELECT COALESCE(SUM(invoice_amount), 0) FROM payments").fetchone()[0]

    # 6. Pending payments
    pending_payments_val = total_invoiced - total_payments_paid
    if pending_payments_val < 0:
        pending_payments_val = 0.0

    # MSE Percentage
    mse_percentage = (total_mse / total_procurement * 100) if total_procurement > 0 else 0.0

    # Non-MSE Procurement
    non_mse_val = max(0.0, total_procurement - total_mse)

    # Recent procurement records (top 5)
    recent_procurements = conn.execute("""
        SELECT p.*, v.vendor_name 
        FROM procurement p
        JOIN vendors v ON p.vendor_id = v.id
        ORDER BY p.date DESC
        LIMIT 5
    """).fetchall()

    # Recent payments (top 5)
    recent_payments = conn.execute("""
        SELECT py.*, v.vendor_name 
        FROM payments py
        JOIN vendors v ON py.vendor_id = v.id
        ORDER BY py.payment_date DESC
        LIMIT 5
    """).fetchall()

    conn.close()

    return render_template(
        'dashboard.html',
        total_procurement=total_procurement,
        total_mse=total_mse,
        total_gem=total_gem,
        total_vendors=total_vendors,
        total_payments_paid=total_payments_paid,
        pending_payments_val=pending_payments_val,
        total_invoiced=total_invoiced,
        mse_percentage=round(mse_percentage, 2),
        non_mse_val=non_mse_val,
        recent_procurements=recent_procurements,
        recent_payments=recent_payments
    )


@app.route('/api/dashboard-charts')
@login_required
def api_dashboard_charts():
    """Provides dynamic JSON data for Chart.js rendering."""
    conn = get_db_connection()

    # Chart 1: Procurement by Type
    type_data = conn.execute("""
        SELECT procurement_type, COALESCE(SUM(procurement_amount), 0) as total
        FROM procurement
        GROUP BY procurement_type
    """).fetchall()
    type_labels = [row['procurement_type'] for row in type_data] or ['Goods', 'Works', 'Services', 'Consultancy']
    type_values = [row['total'] for row in type_data] or [0, 0, 0, 0]

    # Chart 2: MSE vs Non-MSE
    total_proc = conn.execute("SELECT COALESCE(SUM(procurement_amount), 0) FROM procurement").fetchone()[0]
    total_mse = conn.execute("SELECT COALESCE(SUM(procurement_amount), 0) FROM mse_procurement").fetchone()[0]
    non_mse = max(0.0, total_proc - total_mse)

    # Chart 3: GeM by Status
    gem_data = conn.execute("""
        SELECT order_status, COALESCE(SUM(order_amount), 0) as total, COUNT(*) as count
        FROM gem_procurement
        GROUP BY order_status
    """).fetchall()
    gem_labels = [row['order_status'] for row in gem_data] or ['Completed', 'Delivered', 'In Progress', 'Placed']
    gem_values = [row['total'] for row in gem_data] or [0, 0, 0, 0]

    # Chart 4: Paid vs Pending payments
    total_paid = conn.execute("SELECT COALESCE(SUM(amount_paid), 0) FROM payments").fetchone()[0]
    total_inv = conn.execute("SELECT COALESCE(SUM(invoice_amount), 0) FROM payments").fetchone()[0]
    pending_bal = max(0.0, total_inv - total_paid)

    conn.close()

    return jsonify({
        'procurement_by_type': {
            'labels': type_labels,
            'values': type_values
        },
        'mse_vs_non_mse': {
            'labels': ['MSE Procurement', 'Non-MSE Procurement'],
            'values': [total_mse, non_mse]
        },
        'gem_by_status': {
            'labels': gem_labels,
            'values': gem_values
        },
        'payment_status': {
            'labels': ['Amount Paid', 'Pending / Outstanding'],
            'values': [total_paid, pending_bal]
        }
    })


# ---------------------------------------------------------
# 3. Procurement Portal
# ---------------------------------------------------------
@app.route('/procurement')
@login_required
def procurement_list():
    search_q = request.args.get('q', '').strip()
    selected_fy = request.args.get('fy', '').strip()

    conn = get_db_connection()

    # Get distinct FYs for filter dropdown
    fys = [r['financial_year'] for r in conn.execute(
        "SELECT DISTINCT financial_year FROM procurement ORDER BY financial_year DESC"
    ).fetchall()]

    query = """
        SELECT p.*, v.vendor_name, v.vendor_id as ven_code 
        FROM procurement p
        JOIN vendors v ON p.vendor_id = v.id
        WHERE 1=1
    """
    params = []

    if search_q:
        query += """ AND (
            p.procurement_id LIKE ? OR 
            p.purchase_order_number LIKE ? OR 
            p.description LIKE ? OR 
            v.vendor_name LIKE ?
        )"""
        term = f"%{search_q}%"
        params.extend([term, term, term, term])

    if selected_fy:
        query += " AND p.financial_year = ?"
        params.append(selected_fy)

    query += " ORDER BY p.date DESC"

    records = conn.execute(query, params).fetchall()

    total_procurement_value = sum(r['procurement_amount'] for r in records)

    conn.close()

    return render_template(
        'procurement/list.html',
        records=records,
        fys=fys,
        search_q=search_q,
        selected_fy=selected_fy,
        total_procurement_value=total_procurement_value
    )


@app.route('/procurement/add', methods=['GET', 'POST'])
@login_required
def procurement_add():
    conn = get_db_connection()

    if request.method == 'POST':
        procurement_id = request.form.get('procurement_id', '').strip().upper()
        vendor_id = request.form.get('vendor_id')
        po_number = request.form.get('purchase_order_number', '').strip()
        date = request.form.get('date', '').strip()
        description = request.form.get('description', '').strip()
        procurement_amount = request.form.get('procurement_amount', '0').strip()
        procurement_type = request.form.get('procurement_type', 'Goods').strip()
        financial_year = request.form.get('financial_year', '2024-25').strip()

        # Validation
        if not (procurement_id and vendor_id and po_number and date and description and procurement_amount):
            flash("All mandatory fields must be completed.", "danger")
            vendors = conn.execute("SELECT id, vendor_name, vendor_id FROM vendors ORDER BY vendor_name").fetchall()
            conn.close()
            return render_template('procurement/form.html', vendors=vendors, form_data=request.form)

        # Check duplicate procurement_id
        existing = conn.execute("SELECT id FROM procurement WHERE procurement_id = ?", (procurement_id,)).fetchone()
        if existing:
            flash(f"Procurement ID '{procurement_id}' already exists in database.", "danger")
            vendors = conn.execute("SELECT id, vendor_name, vendor_id FROM vendors ORDER BY vendor_name").fetchall()
            conn.close()
            return render_template('procurement/form.html', vendors=vendors, form_data=request.form)

        try:
            amt = float(procurement_amount)
            if amt < 0:
                raise ValueError
        except ValueError:
            flash("Procurement amount must be a positive number.", "danger")
            vendors = conn.execute("SELECT id, vendor_name, vendor_id FROM vendors ORDER BY vendor_name").fetchall()
            conn.close()
            return render_template('procurement/form.html', vendors=vendors, form_data=request.form)

        conn.execute("""
            INSERT INTO procurement (
                procurement_id, vendor_id, purchase_order_number, date, 
                description, procurement_amount, procurement_type, financial_year
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (procurement_id, vendor_id, po_number, date, description, amt, procurement_type, financial_year))
        conn.commit()
        conn.close()

        flash(f"Procurement record '{procurement_id}' added successfully.", "success")
        return redirect(url_for('procurement_list'))

    vendors = conn.execute("SELECT id, vendor_name, vendor_id FROM vendors ORDER BY vendor_name").fetchall()
    conn.close()
    return render_template('procurement/form.html', vendors=vendors, form_data={})


@app.route('/procurement/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def procurement_edit(id):
    conn = get_db_connection()
    record = conn.execute("SELECT * FROM procurement WHERE id = ?", (id,)).fetchone()
    if not record:
        conn.close()
        flash("Procurement record not found.", "warning")
        return redirect(url_for('procurement_list'))

    if request.method == 'POST':
        vendor_id = request.form.get('vendor_id')
        po_number = request.form.get('purchase_order_number', '').strip()
        date = request.form.get('date', '').strip()
        description = request.form.get('description', '').strip()
        procurement_amount = request.form.get('procurement_amount', '0').strip()
        procurement_type = request.form.get('procurement_type', 'Goods').strip()
        financial_year = request.form.get('financial_year', '2024-25').strip()

        try:
            amt = float(procurement_amount)
            if amt < 0:
                raise ValueError
        except ValueError:
            flash("Procurement amount must be a valid positive number.", "danger")
            vendors = conn.execute("SELECT id, vendor_name, vendor_id FROM vendors ORDER BY vendor_name").fetchall()
            conn.close()
            return render_template('procurement/form.html', vendors=vendors, form_data=request.form, is_edit=True, record_id=id)

        conn.execute("""
            UPDATE procurement
            SET vendor_id = ?, purchase_order_number = ?, date = ?, 
                description = ?, procurement_amount = ?, procurement_type = ?, financial_year = ?
            WHERE id = ?
        """, (vendor_id, po_number, date, description, amt, procurement_type, financial_year, id))
        conn.commit()
        conn.close()

        flash(f"Procurement record '{record['procurement_id']}' updated successfully.", "success")
        return redirect(url_for('procurement_list'))

    vendors = conn.execute("SELECT id, vendor_name, vendor_id FROM vendors ORDER BY vendor_name").fetchall()
    conn.close()
    return render_template('procurement/form.html', vendors=vendors, form_data=record, is_edit=True, record_id=id)


@app.route('/procurement/delete/<int:id>', methods=['POST'])
@login_required
def procurement_delete(id):
    conn = get_db_connection()
    record = conn.execute("SELECT procurement_id FROM procurement WHERE id = ?", (id,)).fetchone()
    if record:
        conn.execute("DELETE FROM procurement WHERE id = ?", (id,))
        conn.commit()
        flash(f"Procurement record '{record['procurement_id']}' deleted successfully.", "success")
    else:
        flash("Record not found.", "warning")
    conn.close()
    return redirect(url_for('procurement_list'))


# ---------------------------------------------------------
# 4. MSE Procurement Module
# ---------------------------------------------------------
@app.route('/mse')
@login_required
def mse_list():
    selected_fy = request.args.get('fy', '').strip()
    conn = get_db_connection()

    fys = [r['financial_year'] for r in conn.execute(
        "SELECT DISTINCT financial_year FROM mse_procurement ORDER BY financial_year DESC"
    ).fetchall()]

    query = """
        SELECT m.*, v.vendor_name, v.vendor_category, v.vendor_id as ven_code
        FROM mse_procurement m
        JOIN vendors v ON m.vendor_id = v.id
        WHERE 1=1
    """
    params = []
    if selected_fy:
        query += " AND m.financial_year = ?"
        params.append(selected_fy)

    query += " ORDER BY m.date DESC"
    records = conn.execute(query, params).fetchall()

    # Formula Calculations
    total_mse_procurement = sum(r['procurement_amount'] for r in records)

    # Total procurement for percentage calculation
    if selected_fy:
        total_overall = conn.execute(
            "SELECT COALESCE(SUM(procurement_amount), 0) FROM procurement WHERE financial_year = ?",
            (selected_fy,)
        ).fetchone()[0]
    else:
        total_overall = conn.execute(
            "SELECT COALESCE(SUM(procurement_amount), 0) FROM procurement"
        ).fetchone()[0]

    # Formula: MSE Procurement Percentage = (Total MSE Procurement / Total Procurement Value) * 100
    if total_overall > 0:
        mse_percentage = (total_mse_procurement / total_overall) * 100
    else:
        mse_percentage = 0.0

    conn.close()

    return render_template(
        'mse/list.html',
        records=records,
        fys=fys,
        selected_fy=selected_fy,
        total_mse_procurement=total_mse_procurement,
        total_overall=total_overall,
        mse_percentage=round(mse_percentage, 2)
    )


@app.route('/mse/add', methods=['GET', 'POST'])
@login_required
def mse_add():
    conn = get_db_connection()

    if request.method == 'POST':
        vendor_id = request.form.get('vendor_id')
        udyam_number = request.form.get('udyam_registration_number', '').strip().upper()
        procurement_amount = request.form.get('procurement_amount', '0').strip()
        date = request.form.get('date', '').strip()
        financial_year = request.form.get('financial_year', '2024-25').strip()

        if not (vendor_id and udyam_number and procurement_amount and date and financial_year):
            flash("All fields are required to register MSE procurement.", "danger")
            vendors = conn.execute("SELECT id, vendor_name, vendor_id, vendor_category FROM vendors ORDER BY vendor_name").fetchall()
            conn.close()
            return render_template('mse/form.html', vendors=vendors, form_data=request.form)

        try:
            amt = float(procurement_amount)
            if amt < 0:
                raise ValueError
        except ValueError:
            flash("Procurement amount must be a valid positive number.", "danger")
            vendors = conn.execute("SELECT id, vendor_name, vendor_id, vendor_category FROM vendors ORDER BY vendor_name").fetchall()
            conn.close()
            return render_template('mse/form.html', vendors=vendors, form_data=request.form)

        conn.execute("""
            INSERT INTO mse_procurement (vendor_id, udyam_registration_number, procurement_amount, date, financial_year)
            VALUES (?, ?, ?, ?, ?)
        """, (vendor_id, udyam_number, amt, date, financial_year))
        conn.commit()
        conn.close()

        flash("MSE Procurement record created successfully.", "success")
        return redirect(url_for('mse_list'))

    vendors = conn.execute("SELECT id, vendor_name, vendor_id, vendor_category FROM vendors ORDER BY vendor_name").fetchall()
    conn.close()
    return render_template('mse/form.html', vendors=vendors, form_data={})


@app.route('/mse/delete/<int:id>', methods=['POST'])
@login_required
def mse_delete(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM mse_procurement WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash("MSE Procurement record deleted successfully.", "success")
    return redirect(url_for('mse_list'))


# ---------------------------------------------------------
# 5. GeM Procurement Module
# ---------------------------------------------------------
@app.route('/gem')
@login_required
def gem_list():
    status_filter = request.args.get('status', '').strip()
    search_q = request.args.get('q', '').strip()

    conn = get_db_connection()
    query = """
        SELECT g.*, v.vendor_name, v.vendor_id as ven_code
        FROM gem_procurement g
        JOIN vendors v ON g.vendor_id = v.id
        WHERE 1=1
    """
    params = []

    if status_filter:
        query += " AND g.order_status = ?"
        params.append(status_filter)

    if search_q:
        query += " AND (g.gem_order_id LIKE ? OR g.product_description LIKE ? OR v.vendor_name LIKE ?)"
        term = f"%{search_q}%"
        params.extend([term, term, term])

    query += " ORDER BY g.order_date DESC"

    records = conn.execute(query, params).fetchall()
    total_gem_procurement = sum(r['order_amount'] for r in records)

    conn.close()

    return render_template(
        'gem/list.html',
        records=records,
        status_filter=status_filter,
        search_q=search_q,
        total_gem_procurement=total_gem_procurement
    )


@app.route('/gem/add', methods=['GET', 'POST'])
@login_required
def gem_add():
    conn = get_db_connection()

    if request.method == 'POST':
        gem_order_id = request.form.get('gem_order_id', '').strip().upper()
        vendor_id = request.form.get('vendor_id')
        product_description = request.form.get('product_description', '').strip()
        order_amount = request.form.get('order_amount', '0').strip()
        order_date = request.form.get('order_date', '').strip()
        order_status = request.form.get('order_status', 'Placed').strip()

        if not (gem_order_id and vendor_id and product_description and order_amount and order_date):
            flash("All fields are required.", "danger")
            vendors = conn.execute("SELECT id, vendor_name, vendor_id FROM vendors ORDER BY vendor_name").fetchall()
            conn.close()
            return render_template('gem/form.html', vendors=vendors, form_data=request.form)

        # Check duplicate GeM Order ID
        existing = conn.execute("SELECT id FROM gem_procurement WHERE gem_order_id = ?", (gem_order_id,)).fetchone()
        if existing:
            flash(f"GeM Order ID '{gem_order_id}' already exists.", "danger")
            vendors = conn.execute("SELECT id, vendor_name, vendor_id FROM vendors ORDER BY vendor_name").fetchall()
            conn.close()
            return render_template('gem/form.html', vendors=vendors, form_data=request.form)

        try:
            amt = float(order_amount)
            if amt < 0:
                raise ValueError
        except ValueError:
            flash("Order amount must be a positive number.", "danger")
            vendors = conn.execute("SELECT id, vendor_name, vendor_id FROM vendors ORDER BY vendor_name").fetchall()
            conn.close()
            return render_template('gem/form.html', vendors=vendors, form_data=request.form)

        conn.execute("""
            INSERT INTO gem_procurement (gem_order_id, vendor_id, product_description, order_amount, order_date, order_status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (gem_order_id, vendor_id, product_description, amt, order_date, order_status))
        conn.commit()
        conn.close()

        flash(f"GeM Order '{gem_order_id}' recorded successfully.", "success")
        return redirect(url_for('gem_list'))

    vendors = conn.execute("SELECT id, vendor_name, vendor_id FROM vendors ORDER BY vendor_name").fetchall()
    conn.close()
    return render_template('gem/form.html', vendors=vendors, form_data={})


@app.route('/gem/update-status/<int:id>', methods=['POST'])
@login_required
def gem_update_status(id):
    new_status = request.form.get('order_status', '').strip()
    if new_status in ['Placed', 'In Progress', 'Delivered', 'Completed', 'Cancelled']:
        conn = get_db_connection()
        conn.execute("UPDATE gem_procurement SET order_status = ? WHERE id = ?", (new_status, id))
        conn.commit()
        conn.close()
        flash(f"Order status updated to '{new_status}'.", "success")
    else:
        flash("Invalid status selected.", "danger")
    return redirect(url_for('gem_list'))


@app.route('/gem/delete/<int:id>', methods=['POST'])
@login_required
def gem_delete(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM gem_procurement WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash("GeM order deleted successfully.", "success")
    return redirect(url_for('gem_list'))


# ---------------------------------------------------------
# 6. Vendor Management Module
# ---------------------------------------------------------
@app.route('/vendors')
@login_required
def vendor_list():
    search_q = request.args.get('q', '').strip()
    conn = get_db_connection()

    query = """
        SELECT v.*,
            (SELECT COUNT(*) FROM procurement p WHERE p.vendor_id = v.id) as proc_count,
            (SELECT COUNT(*) FROM payments py WHERE py.vendor_id = v.id) as pay_count
        FROM vendors v
        WHERE 1=1
    """
    params = []
    if search_q:
        query += " AND (v.vendor_name LIKE ? OR v.vendor_id LIKE ? OR v.email LIKE ? OR v.vendor_category LIKE ?)"
        term = f"%{search_q}%"
        params.extend([term, term, term, term])

    query += " ORDER BY v.vendor_id ASC"
    vendors = conn.execute(query, params).fetchall()
    conn.close()

    return render_template('vendors/list.html', vendors=vendors, search_q=search_q)


@app.route('/vendors/add', methods=['GET', 'POST'])
@login_required
def vendor_add():
    if request.method == 'POST':
        vendor_id = request.form.get('vendor_id', '').strip().upper()
        vendor_name = request.form.get('vendor_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        vendor_category = request.form.get('vendor_category', 'Small').strip()
        mse_status = request.form.get('mse_status', 'No').strip()

        if not (vendor_id and vendor_name and vendor_category and mse_status):
            flash("Vendor ID, Name, Category, and MSE Status are required.", "danger")
            return render_template('vendors/form.html', form_data=request.form)

        conn = get_db_connection()
        existing = conn.execute("SELECT id FROM vendors WHERE vendor_id = ?", (vendor_id,)).fetchone()
        if existing:
            conn.close()
            flash(f"Vendor ID '{vendor_id}' is already registered.", "danger")
            return render_template('vendors/form.html', form_data=request.form)

        conn.execute("""
            INSERT INTO vendors (vendor_id, vendor_name, email, phone, vendor_category, mse_status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (vendor_id, vendor_name, email, phone, vendor_category, mse_status))
        conn.commit()
        conn.close()

        flash(f"Vendor '{vendor_name}' ({vendor_id}) added successfully.", "success")
        return redirect(url_for('vendor_list'))

    return render_template('vendors/form.html', form_data={})


@app.route('/vendors/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def vendor_edit(id):
    conn = get_db_connection()
    vendor = conn.execute("SELECT * FROM vendors WHERE id = ?", (id,)).fetchone()
    if not vendor:
        conn.close()
        flash("Vendor record not found.", "warning")
        return redirect(url_for('vendor_list'))

    if request.method == 'POST':
        vendor_name = request.form.get('vendor_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        vendor_category = request.form.get('vendor_category', 'Small').strip()
        mse_status = request.form.get('mse_status', 'No').strip()

        conn.execute("""
            UPDATE vendors
            SET vendor_name = ?, email = ?, phone = ?, vendor_category = ?, mse_status = ?
            WHERE id = ?
        """, (vendor_name, email, phone, vendor_category, mse_status, id))
        conn.commit()
        conn.close()

        flash(f"Vendor '{vendor_name}' updated successfully.", "success")
        return redirect(url_for('vendor_list'))

    conn.close()
    return render_template('vendors/form.html', form_data=vendor, is_edit=True, vendor_id=id)


@app.route('/vendors/delete/<int:id>', methods=['POST'])
@login_required
def vendor_delete(id):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM vendors WHERE id = ?", (id,))
        conn.commit()
        flash("Vendor and associated records deleted successfully.", "success")
    except Exception as e:
        flash(f"Unable to delete vendor: {str(e)}", "danger")
    finally:
        conn.close()
    return redirect(url_for('vendor_list'))


# ---------------------------------------------------------
# 7. Vendor Payment Portal
# ---------------------------------------------------------
@app.route('/payments')
@login_required
def payment_list():
    status_filter = request.args.get('status', '').strip()
    search_q = request.args.get('q', '').strip()

    conn = get_db_connection()
    query = """
        SELECT py.*, v.vendor_name, v.vendor_id as ven_code
        FROM payments py
        JOIN vendors v ON py.vendor_id = v.id
        WHERE 1=1
    """
    params = []

    if status_filter:
        query += " AND py.payment_status = ?"
        params.append(status_filter)

    if search_q:
        query += " AND (py.invoice_number LIKE ? OR v.vendor_name LIKE ?)"
        term = f"%{search_q}%"
        params.extend([term, term])

    query += " ORDER BY py.payment_date DESC"
    records = conn.execute(query, params).fetchall()

    total_invoice_amount = sum(r['invoice_amount'] for r in records)
    total_amount_paid = sum(r['amount_paid'] for r in records)
    total_outstanding = max(0.0, total_invoice_amount - total_amount_paid)

    conn.close()

    return render_template(
        'payments/list.html',
        records=records,
        status_filter=status_filter,
        search_q=search_q,
        total_invoice_amount=total_invoice_amount,
        total_amount_paid=total_amount_paid,
        total_outstanding=total_outstanding
    )


@app.route('/payments/add', methods=['GET', 'POST'])
@login_required
def payment_add():
    conn = get_db_connection()

    if request.method == 'POST':
        vendor_id = request.form.get('vendor_id')
        invoice_number = request.form.get('invoice_number', '').strip().upper()
        invoice_amount = request.form.get('invoice_amount', '0').strip()
        amount_paid = request.form.get('amount_paid', '0').strip()
        payment_date = request.form.get('payment_date', '').strip()

        if not (vendor_id and invoice_number and invoice_amount and payment_date):
            flash("Vendor, Invoice Number, Invoice Amount and Date are required.", "danger")
            vendors = conn.execute("SELECT id, vendor_name, vendor_id FROM vendors ORDER BY vendor_name").fetchall()
            conn.close()
            return render_template('payments/form.html', vendors=vendors, form_data=request.form)

        try:
            inv_amt = float(invoice_amount)
            paid_amt = float(amount_paid) if amount_paid else 0.0
            if inv_amt < 0 or paid_amt < 0:
                raise ValueError
        except ValueError:
            flash("Amounts must be positive numeric values.", "danger")
            vendors = conn.execute("SELECT id, vendor_name, vendor_id FROM vendors ORDER BY vendor_name").fetchall()
            conn.close()
            return render_template('payments/form.html', vendors=vendors, form_data=request.form)

        # Automatic Payment Status calculation:
        # Paid, Partially Paid, Pending
        if paid_amt >= inv_amt:
            payment_status = 'Paid'
        elif paid_amt > 0:
            payment_status = 'Partially Paid'
        else:
            payment_status = 'Pending'

        conn.execute("""
            INSERT INTO payments (vendor_id, invoice_number, invoice_amount, amount_paid, payment_date, payment_status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (vendor_id, invoice_number, inv_amt, paid_amt, payment_date, payment_status))
        conn.commit()
        conn.close()

        flash(f"Payment record for invoice '{invoice_number}' created successfully.", "success")
        return redirect(url_for('payment_list'))

    vendors = conn.execute("SELECT id, vendor_name, vendor_id FROM vendors ORDER BY vendor_name").fetchall()
    conn.close()
    return render_template('payments/form.html', vendors=vendors, form_data={})


@app.route('/payments/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def payment_edit(id):
    conn = get_db_connection()
    record = conn.execute("SELECT * FROM payments WHERE id = ?", (id,)).fetchone()
    if not record:
        conn.close()
        flash("Payment record not found.", "warning")
        return redirect(url_for('payment_list'))

    if request.method == 'POST':
        vendor_id = request.form.get('vendor_id')
        invoice_number = request.form.get('invoice_number', '').strip().upper()
        invoice_amount = request.form.get('invoice_amount', '0').strip()
        amount_paid = request.form.get('amount_paid', '0').strip()
        payment_date = request.form.get('payment_date', '').strip()

        try:
            inv_amt = float(invoice_amount)
            paid_amt = float(amount_paid) if amount_paid else 0.0
            if inv_amt < 0 or paid_amt < 0:
                raise ValueError
        except ValueError:
            flash("Amounts must be positive numbers.", "danger")
            vendors = conn.execute("SELECT id, vendor_name, vendor_id FROM vendors ORDER BY vendor_name").fetchall()
            conn.close()
            return render_template('payments/form.html', vendors=vendors, form_data=request.form, is_edit=True, record_id=id)

        # Recalculate status
        if paid_amt >= inv_amt:
            payment_status = 'Paid'
        elif paid_amt > 0:
            payment_status = 'Partially Paid'
        else:
            payment_status = 'Pending'

        conn.execute("""
            UPDATE payments
            SET vendor_id = ?, invoice_number = ?, invoice_amount = ?, 
                amount_paid = ?, payment_date = ?, payment_status = ?
            WHERE id = ?
        """, (vendor_id, invoice_number, inv_amt, paid_amt, payment_date, payment_status, id))
        conn.commit()
        conn.close()

        flash("Payment record updated successfully.", "success")
        return redirect(url_for('payment_list'))

    vendors = conn.execute("SELECT id, vendor_name, vendor_id FROM vendors ORDER BY vendor_name").fetchall()
    conn.close()
    return render_template('payments/form.html', vendors=vendors, form_data=record, is_edit=True, record_id=id)


@app.route('/payments/delete/<int:id>', methods=['POST'])
@login_required
def payment_delete(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM payments WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash("Payment record deleted successfully.", "success")
    return redirect(url_for('payment_list'))


# ---------------------------------------------------------
# 8. Reports Module
# ---------------------------------------------------------
@app.route('/reports')
@login_required
def reports_index():
    return render_template('reports/index.html')


# Report 1: Total Procurement Report
@app.route('/reports/procurement')
@login_required
def report_procurement():
    fy = request.args.get('fy', '').strip()
    from_date = request.args.get('from_date', '').strip()
    to_date = request.args.get('to_date', '').strip()

    conn = get_db_connection()
    fys = [r['financial_year'] for r in conn.execute(
        "SELECT DISTINCT financial_year FROM procurement ORDER BY financial_year DESC"
    ).fetchall()]

    query = """
        SELECT p.*, v.vendor_name, v.vendor_id as ven_code 
        FROM procurement p
        JOIN vendors v ON p.vendor_id = v.id
        WHERE 1=1
    """
    params = []
    if fy:
        query += " AND p.financial_year = ?"
        params.append(fy)
    if from_date:
        query += " AND p.date >= ?"
        params.append(from_date)
    if to_date:
        query += " AND p.date <= ?"
        params.append(to_date)

    query += " ORDER BY p.date ASC"
    records = conn.execute(query, params).fetchall()

    total_amount = sum(r['procurement_amount'] for r in records)
    conn.close()

    return render_template(
        'reports/procurement_report.html',
        records=records,
        fys=fys,
        fy=fy,
        from_date=from_date,
        to_date=to_date,
        total_amount=total_amount
    )


@app.route('/reports/procurement/csv')
@login_required
def report_procurement_csv():
    fy = request.args.get('fy', '').strip()
    from_date = request.args.get('from_date', '').strip()
    to_date = request.args.get('to_date', '').strip()

    conn = get_db_connection()
    query = """
        SELECT p.procurement_id, v.vendor_name, v.vendor_id, p.purchase_order_number, 
               p.date, p.description, p.procurement_type, p.financial_year, p.procurement_amount
        FROM procurement p
        JOIN vendors v ON p.vendor_id = v.id
        WHERE 1=1
    """
    params = []
    if fy:
        query += " AND p.financial_year = ?"
        params.append(fy)
    if from_date:
        query += " AND p.date >= ?"
        params.append(from_date)
    if to_date:
        query += " AND p.date <= ?"
        params.append(to_date)

    query += " ORDER BY p.date ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Procurement ID", "Vendor Name", "Vendor Code", "PO Number", 
        "Date", "Description", "Type", "Financial Year", "Amount (INR)"
    ])

    total = 0.0
    for r in rows:
        total += r['procurement_amount']
        writer.writerow([
            r['procurement_id'], r['vendor_name'], r['vendor_id'], r['purchase_order_number'],
            r['date'], r['description'], r['procurement_type'], r['financial_year'], f"{r['procurement_amount']:.2f}"
        ])
    writer.writerow(["TOTAL", "", "", "", "", "", "", "", f"{total:.2f}"])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=neepco_procurement_report.csv"}
    )


# Report 2: MSE Procurement Report
@app.route('/reports/mse')
@login_required
def report_mse():
    fy = request.args.get('fy', '').strip()
    from_date = request.args.get('from_date', '').strip()
    to_date = request.args.get('to_date', '').strip()

    conn = get_db_connection()
    fys = [r['financial_year'] for r in conn.execute(
        "SELECT DISTINCT financial_year FROM mse_procurement ORDER BY financial_year DESC"
    ).fetchall()]

    query = """
        SELECT m.*, v.vendor_name, v.vendor_category, v.vendor_id as ven_code 
        FROM mse_procurement m
        JOIN vendors v ON m.vendor_id = v.id
        WHERE 1=1
    """
    params = []
    if fy:
        query += " AND m.financial_year = ?"
        params.append(fy)
    if from_date:
        query += " AND m.date >= ?"
        params.append(from_date)
    if to_date:
        query += " AND m.date <= ?"
        params.append(to_date)

    query += " ORDER BY m.date ASC"
    records = conn.execute(query, params).fetchall()

    total_mse = sum(r['procurement_amount'] for r in records)

    # Calculate overall procurement for ratio
    if fy:
        total_overall = conn.execute(
            "SELECT COALESCE(SUM(procurement_amount), 0) FROM procurement WHERE financial_year = ?", (fy,)
        ).fetchone()[0]
    else:
        total_overall = conn.execute(
            "SELECT COALESCE(SUM(procurement_amount), 0) FROM procurement"
        ).fetchone()[0]

    mse_pct = (total_mse / total_overall * 100) if total_overall > 0 else 0.0

    conn.close()

    return render_template(
        'reports/mse_report.html',
        records=records,
        fys=fys,
        fy=fy,
        from_date=from_date,
        to_date=to_date,
        total_mse=total_mse,
        total_overall=total_overall,
        mse_pct=round(mse_pct, 2)
    )


@app.route('/reports/mse/csv')
@login_required
def report_mse_csv():
    fy = request.args.get('fy', '').strip()
    from_date = request.args.get('from_date', '').strip()
    to_date = request.args.get('to_date', '').strip()

    conn = get_db_connection()
    query = """
        SELECT m.id, v.vendor_name, v.vendor_id, v.vendor_category, 
               m.udyam_registration_number, m.date, m.financial_year, m.procurement_amount
        FROM mse_procurement m
        JOIN vendors v ON m.vendor_id = v.id
        WHERE 1=1
    """
    params = []
    if fy:
        query += " AND m.financial_year = ?"
        params.append(fy)
    if from_date:
        query += " AND m.date >= ?"
        params.append(from_date)
    if to_date:
        query += " AND m.date <= ?"
        params.append(to_date)

    query += " ORDER BY m.date ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Record ID", "Vendor Name", "Vendor Code", "Vendor Category", 
        "Udyam Reg Number", "Date", "Financial Year", "Amount (INR)"
    ])

    total = 0.0
    for r in rows:
        total += r['procurement_amount']
        writer.writerow([
            r['id'], r['vendor_name'], r['vendor_id'], r['vendor_category'],
            r['udyam_registration_number'], r['date'], r['financial_year'], f"{r['procurement_amount']:.2f}"
        ])
    writer.writerow(["TOTAL", "", "", "", "", "", "", f"{total:.2f}"])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=neepco_mse_procurement_report.csv"}
    )


# Report 3: GeM Procurement Report
@app.route('/reports/gem')
@login_required
def report_gem():
    status = request.args.get('status', '').strip()
    from_date = request.args.get('from_date', '').strip()
    to_date = request.args.get('to_date', '').strip()

    conn = get_db_connection()
    query = """
        SELECT g.*, v.vendor_name, v.vendor_id as ven_code 
        FROM gem_procurement g
        JOIN vendors v ON g.vendor_id = v.id
        WHERE 1=1
    """
    params = []
    if status:
        query += " AND g.order_status = ?"
        params.append(status)
    if from_date:
        query += " AND g.order_date >= ?"
        params.append(from_date)
    if to_date:
        query += " AND g.order_date <= ?"
        params.append(to_date)

    query += " ORDER BY g.order_date ASC"
    records = conn.execute(query, params).fetchall()

    total_amount = sum(r['order_amount'] for r in records)
    conn.close()

    return render_template(
        'reports/gem_report.html',
        records=records,
        status=status,
        from_date=from_date,
        to_date=to_date,
        total_amount=total_amount
    )


@app.route('/reports/gem/csv')
@login_required
def report_gem_csv():
    status = request.args.get('status', '').strip()
    from_date = request.args.get('from_date', '').strip()
    to_date = request.args.get('to_date', '').strip()

    conn = get_db_connection()
    query = """
        SELECT g.gem_order_id, v.vendor_name, v.vendor_id, 
               g.product_description, g.order_date, g.order_status, g.order_amount
        FROM gem_procurement g
        JOIN vendors v ON g.vendor_id = v.id
        WHERE 1=1
    """
    params = []
    if status:
        query += " AND g.order_status = ?"
        params.append(status)
    if from_date:
        query += " AND g.order_date >= ?"
        params.append(from_date)
    if to_date:
        query += " AND g.order_date <= ?"
        params.append(to_date)

    query += " ORDER BY g.order_date ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "GeM Order ID", "Vendor Name", "Vendor Code", 
        "Product Description", "Order Date", "Status", "Order Amount (INR)"
    ])

    total = 0.0
    for r in rows:
        total += r['order_amount']
        writer.writerow([
            r['gem_order_id'], r['vendor_name'], r['vendor_id'],
            r['product_description'], r['order_date'], r['order_status'], f"{r['order_amount']:.2f}"
        ])
    writer.writerow(["TOTAL", "", "", "", "", "", f"{total:.2f}"])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=neepco_gem_report.csv"}
    )


# Report 4: Vendor Payment Report
@app.route('/reports/payments')
@login_required
def report_payments():
    status = request.args.get('status', '').strip()
    from_date = request.args.get('from_date', '').strip()
    to_date = request.args.get('to_date', '').strip()

    conn = get_db_connection()
    query = """
        SELECT py.*, v.vendor_name, v.vendor_id as ven_code 
        FROM payments py
        JOIN vendors v ON py.vendor_id = v.id
        WHERE 1=1
    """
    params = []
    if status:
        query += " AND py.payment_status = ?"
        params.append(status)
    if from_date:
        query += " AND py.payment_date >= ?"
        params.append(from_date)
    if to_date:
        query += " AND py.payment_date <= ?"
        params.append(to_date)

    query += " ORDER BY py.payment_date ASC"
    records = conn.execute(query, params).fetchall()

    total_invoice = sum(r['invoice_amount'] for r in records)
    total_paid = sum(r['amount_paid'] for r in records)
    total_outstanding = max(0.0, total_invoice - total_paid)

    conn.close()

    return render_template(
        'reports/payment_report.html',
        records=records,
        status=status,
        from_date=from_date,
        to_date=to_date,
        total_invoice=total_invoice,
        total_paid=total_paid,
        total_outstanding=total_outstanding
    )


@app.route('/reports/payments/csv')
@login_required
def report_payments_csv():
    status = request.args.get('status', '').strip()
    from_date = request.args.get('from_date', '').strip()
    to_date = request.args.get('to_date', '').strip()

    conn = get_db_connection()
    query = """
        SELECT py.invoice_number, v.vendor_name, v.vendor_id, 
               py.payment_date, py.invoice_amount, py.amount_paid, py.payment_status
        FROM payments py
        JOIN vendors v ON py.vendor_id = v.id
        WHERE 1=1
    """
    params = []
    if status:
        query += " AND py.payment_status = ?"
        params.append(status)
    if from_date:
        query += " AND py.payment_date >= ?"
        params.append(from_date)
    if to_date:
        query += " AND py.payment_date <= ?"
        params.append(to_date)

    query += " ORDER BY py.payment_date ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Invoice Number", "Vendor Name", "Vendor Code", "Payment Date", 
        "Invoice Amount (INR)", "Amount Paid (INR)", "Outstanding Amount (INR)", "Status"
    ])

    tot_inv, tot_pd, tot_out = 0.0, 0.0, 0.0
    for r in rows:
        inv = r['invoice_amount']
        pd = r['amount_paid']
        out = max(0.0, inv - pd)
        tot_inv += inv
        tot_pd += pd
        tot_out += out
        writer.writerow([
            r['invoice_number'], r['vendor_name'], r['vendor_id'], r['payment_date'],
            f"{inv:.2f}", f"{pd:.2f}", f"{out:.2f}", r['payment_status']
        ])
    writer.writerow(["TOTAL", "", "", "", f"{tot_inv:.2f}", f"{tot_pd:.2f}", f"{tot_out:.2f}", ""])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=neepco_vendor_payment_report.csv"}
    )


# ---------------------------------------------------------
# Application Startup
# ---------------------------------------------------------
if __name__ == '__main__':
    # Initialize DB schema and seed demo records if needed
    init_db()
    print("=" * 70)
    print("NEEPCO Procurement & Vendor Payment Portal is starting...")
    print("Local Server URL: http://127.0.0.1:5000")
    print("Default Admin Login: admin / admin123")
    print("=" * 70)
    app.run(debug=True, host='127.0.0.1', port=5000)
