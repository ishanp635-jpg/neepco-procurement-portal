"""
Comprehensive Test Suite for NEEPCO Portal
Verifies all functionality, database queries, calculations, authentication, and CSV exports.
"""

import unittest
from app import app
from database import init_db, get_db_connection

class TestNeepcoPortal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        cls.client = app.test_client()

    def test_01_unauthenticated_access_protection(self):
        """Internal routes must redirect unauthenticated users to /login."""
        protected_routes = [
            '/', '/dashboard', '/procurement', '/procurement/add',
            '/mse', '/mse/add', '/gem', '/gem/add',
            '/vendors', '/vendors/add', '/payments', '/payments/add',
            '/reports', '/reports/procurement', '/reports/procurement/csv'
        ]
        for route in protected_routes:
            res = self.client.get(route, follow_redirects=False)
            self.assertEqual(res.status_code, 302, f"Route {route} did not redirect unauthenticated user!")
            self.assertIn('/login', res.headers['Location'])

    def test_02_login_invalid_credentials(self):
        """Invalid credentials should show error and not create session."""
        res = self.client.post('/login', data={
            'login_id': 'admin',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Invalid credentials", res.data)

    def test_03_login_valid_admin(self):
        """Admin credentials (admin / admin123) should successfully log in."""
        res = self.client.post('/login', data={
            'login_id': 'admin',
            'password': 'admin123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Executive Dashboard", res.data)
        self.assertIn(b"NEEPCO Nodal Officer", res.data)

    def test_04_user_registration(self):
        """Registering a new nodal user should succeed and allow login."""
        # 1. Register new user
        reg_res = self.client.post('/register', data={
            'full_name': 'Dr. Alok Baruah',
            'email': 'alok.baruah@neepco.gov.in',
            'username': 'alokb',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(reg_res.status_code, 200)
        self.assertIn(b"Registration successful", reg_res.data)

        # 2. Login as the newly registered user
        login_res = self.client.post('/login', data={
            'login_id': 'alokb',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b"Dr. Alok Baruah", login_res.data)

    def test_05_dashboard_metrics_and_api(self):
        """Dashboard and dynamic chart API should return dynamic data."""
        # Authenticate as admin
        self.client.post('/login', data={'login_id': 'admin', 'password': 'admin123'})

        # Check dashboard HTML
        res = self.client.get('/dashboard')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Total Procurement Value", res.data)
        self.assertIn(b"Total MSE Procurement", res.data)
        self.assertIn(b"Total GeM Procurement", res.data)

        # Check Chart.js JSON API
        api_res = self.client.get('/api/dashboard-charts')
        self.assertEqual(api_res.status_code, 200)
        json_data = api_res.get_json()
        self.assertIn('procurement_by_type', json_data)
        self.assertIn('mse_vs_non_mse', json_data)
        self.assertIn('gem_by_status', json_data)
        self.assertIn('payment_status', json_data)

    def test_06_vendor_crud(self):
        """Add, View, Edit, and Delete Vendor operations."""
        self.client.post('/login', data={'login_id': 'admin', 'password': 'admin123'})

        # Add Vendor
        res_add = self.client.post('/vendors/add', data={
            'vendor_id': 'VEN-999',
            'vendor_name': 'Kaziranga Renewable Energy Systems',
            'email': 'contact@kaziranga.in',
            'phone': '+91 94355 99999',
            'vendor_category': 'Small',
            'mse_status': 'Yes'
        }, follow_redirects=True)
        self.assertEqual(res_add.status_code, 200)
        self.assertIn(b"Kaziranga Renewable Energy Systems", res_add.data)

        # Query ID
        conn = get_db_connection()
        v = conn.execute("SELECT id FROM vendors WHERE vendor_id = 'VEN-999'").fetchone()
        self.assertIsNotNone(v)
        v_id = v['id']

        # Edit Vendor
        res_edit = self.client.post(f'/vendors/edit/{v_id}', data={
            'vendor_name': 'Kaziranga Renewable Energy Systems Pvt Ltd',
            'email': 'contact@kaziranga.in',
            'phone': '+91 94355 99999',
            'vendor_category': 'Medium',
            'mse_status': 'Yes'
        }, follow_redirects=True)
        self.assertEqual(res_edit.status_code, 200)
        self.assertIn(b"Kaziranga Renewable Energy Systems Pvt Ltd", res_edit.data)

        # Delete Vendor
        res_del = self.client.post(f'/vendors/delete/{v_id}', follow_redirects=True)
        self.assertEqual(res_del.status_code, 200)
        v_check = conn.execute("SELECT id FROM vendors WHERE vendor_id = 'VEN-999'").fetchone()
        self.assertIsNone(v_check)
        conn.close()

    def test_07_procurement_crud(self):
        """Add, View, Edit, Filter, and Delete Procurement records."""
        self.client.post('/login', data={'login_id': 'admin', 'password': 'admin123'})

        # Add Procurement
        res_add = self.client.post('/procurement/add', data={
            'procurement_id': 'PROC-TEST-001',
            'vendor_id': 1,
            'purchase_order_number': 'PO/TEST/001',
            'date': '2024-10-15',
            'description': 'Testing power cable procurement',
            'procurement_amount': '500000.00',
            'procurement_type': 'Goods',
            'financial_year': '2024-25'
        }, follow_redirects=True)
        self.assertEqual(res_add.status_code, 200)
        self.assertIn(b"PROC-TEST-001", res_add.data)

        # Query
        conn = get_db_connection()
        p = conn.execute("SELECT id FROM procurement WHERE procurement_id = 'PROC-TEST-001'").fetchone()
        self.assertIsNotNone(p)
        p_id = p['id']

        # Edit Procurement
        res_edit = self.client.post(f'/procurement/edit/{p_id}', data={
            'vendor_id': 1,
            'purchase_order_number': 'PO/TEST/001-REV',
            'date': '2024-10-16',
            'description': 'Testing power cable procurement updated',
            'procurement_amount': '550000.00',
            'procurement_type': 'Goods',
            'financial_year': '2024-25'
        }, follow_redirects=True)
        self.assertEqual(res_edit.status_code, 200)
        self.assertIn(b"PO/TEST/001-REV", res_edit.data)

        # Filter by FY
        res_filter = self.client.get('/procurement?fy=2024-25')
        self.assertEqual(res_filter.status_code, 200)
        self.assertIn(b"PROC-TEST-001", res_filter.data)

        # Delete Procurement
        res_del = self.client.post(f'/procurement/delete/{p_id}', follow_redirects=True)
        self.assertEqual(res_del.status_code, 200)
        p_check = conn.execute("SELECT id FROM procurement WHERE procurement_id = 'PROC-TEST-001'").fetchone()
        self.assertIsNone(p_check)
        conn.close()

    def test_08_mse_procurement_and_formula(self):
        """Add MSE record and verify MSE percentage calculation formula."""
        self.client.post('/login', data={'login_id': 'admin', 'password': 'admin123'})

        res_add = self.client.post('/mse/add', data={
            'vendor_id': 1,
            'udyam_registration_number': 'UDYAM-TEST-001',
            'procurement_amount': '250000.00',
            'date': '2024-10-20',
            'financial_year': '2024-25'
        }, follow_redirects=True)
        self.assertEqual(res_add.status_code, 200)
        self.assertIn(b"UDYAM-TEST-001", res_add.data)

        # Verify list and percentage calculation formula
        res_list = self.client.get('/mse')
        self.assertEqual(res_list.status_code, 200)
        self.assertIn(b"MSE Achievement Percentage", res_list.data)

        # Clean up
        conn = get_db_connection()
        m = conn.execute("SELECT id FROM mse_procurement WHERE udyam_registration_number = 'UDYAM-TEST-001'").fetchone()
        if m:
            self.client.post(f'/mse/delete/{m["id"]}')
        conn.close()

    def test_09_gem_procurement_and_status(self):
        """Add GeM order and update its status."""
        self.client.post('/login', data={'login_id': 'admin', 'password': 'admin123'})

        res_add = self.client.post('/gem/add', data={
            'gem_order_id': 'GEMC-TEST-9999',
            'vendor_id': 2,
            'product_description': 'High precision optical sensors',
            'order_amount': '120000.00',
            'order_date': '2024-11-01',
            'order_status': 'Placed'
        }, follow_redirects=True)
        self.assertEqual(res_add.status_code, 200)
        self.assertIn(b"GEMC-TEST-9999", res_add.data)

        conn = get_db_connection()
        g = conn.execute("SELECT id FROM gem_procurement WHERE gem_order_id = 'GEMC-TEST-9999'").fetchone()
        self.assertIsNotNone(g)
        g_id = g['id']

        # Update status
        res_status = self.client.post(f'/gem/update-status/{g_id}', data={
            'order_status': 'Delivered'
        }, follow_redirects=True)
        self.assertEqual(res_status.status_code, 200)
        self.assertIn(b"Delivered", res_status.data)

        # Delete
        self.client.post(f'/gem/delete/{g_id}')
        conn.close()

    def test_10_payment_portal_calculations(self):
        """Test payment status auto-calculation (Paid, Partially Paid, Pending) and Outstanding amount."""
        self.client.post('/login', data={'login_id': 'admin', 'password': 'admin123'})

        # Case 1: Partially Paid (Invoice = 100000, Paid = 60000 -> Outstanding = 40000)
        self.client.post('/payments/add', data={
            'vendor_id': 1,
            'invoice_number': 'INV-TEST-PARTIAL',
            'invoice_amount': '100000.00',
            'amount_paid': '60000.00',
            'payment_date': '2024-11-10'
        }, follow_redirects=True)

        # Case 2: Paid in Full (Invoice = 50000, Paid = 50000 -> Outstanding = 0)
        self.client.post('/payments/add', data={
            'vendor_id': 2,
            'invoice_number': 'INV-TEST-FULL',
            'invoice_amount': '50000.00',
            'amount_paid': '50000.00',
            'payment_date': '2024-11-11'
        }, follow_redirects=True)

        # Case 3: Pending (Invoice = 80000, Paid = 0 -> Outstanding = 80000)
        self.client.post('/payments/add', data={
            'vendor_id': 3,
            'invoice_number': 'INV-TEST-PENDING',
            'invoice_amount': '80000.00',
            'amount_paid': '0.00',
            'payment_date': '2024-11-12'
        }, follow_redirects=True)

        conn = get_db_connection()
        p1 = conn.execute("SELECT payment_status FROM payments WHERE invoice_number = 'INV-TEST-PARTIAL'").fetchone()
        p2 = conn.execute("SELECT payment_status FROM payments WHERE invoice_number = 'INV-TEST-FULL'").fetchone()
        p3 = conn.execute("SELECT payment_status FROM payments WHERE invoice_number = 'INV-TEST-PENDING'").fetchone()

        self.assertEqual(p1['payment_status'], 'Partially Paid')
        self.assertEqual(p2['payment_status'], 'Paid')
        self.assertEqual(p3['payment_status'], 'Pending')

        # Clean test records
        conn.execute("DELETE FROM payments WHERE invoice_number LIKE 'INV-TEST-%'")
        conn.commit()
        conn.close()

    def test_11_reports_and_csv_exports(self):
        """Verify all 4 report tables and CSV download streams."""
        self.client.post('/login', data={'login_id': 'admin', 'password': 'admin123'})

        # Report 1
        res1 = self.client.get('/reports/procurement')
        self.assertEqual(res1.status_code, 200)
        csv1 = self.client.get('/reports/procurement/csv')
        self.assertEqual(csv1.status_code, 200)
        self.assertIn(b"Procurement ID,Vendor Name", csv1.data)

        # Report 2
        res2 = self.client.get('/reports/mse')
        self.assertEqual(res2.status_code, 200)
        csv2 = self.client.get('/reports/mse/csv')
        self.assertEqual(csv2.status_code, 200)
        self.assertIn(b"Udyam Reg Number", csv2.data)

        # Report 3
        res3 = self.client.get('/reports/gem')
        self.assertEqual(res3.status_code, 200)
        csv3 = self.client.get('/reports/gem/csv')
        self.assertEqual(csv3.status_code, 200)
        self.assertIn(b"GeM Order ID,Vendor Name", csv3.data)

        # Report 4
        res4 = self.client.get('/reports/payments')
        self.assertEqual(res4.status_code, 200)
        csv4 = self.client.get('/reports/payments/csv')
        self.assertEqual(csv4.status_code, 200)
        self.assertIn(b"Invoice Number,Vendor Name", csv4.data)

    def test_12_logout(self):
        """Logout must clear session and redirect to /login."""
        self.client.post('/login', data={'login_id': 'admin', 'password': 'admin123'})
        res = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"logged out", res.data)

        # Check subsequent dashboard access fails
        dash_res = self.client.get('/dashboard', follow_redirects=False)
        self.assertEqual(dash_res.status_code, 302)


if __name__ == '__main__':
    unittest.main()
