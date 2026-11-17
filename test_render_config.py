import os
import shutil
import sqlite3
import tempfile
import unittest

class RenderConfigTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.custom_db = os.path.join(self.temp_dir, "nested", "data", "test_neepco.db")
        os.environ['DATABASE_PATH'] = self.custom_db
        os.environ['SECRET_KEY'] = 'test-render-super-secret-key-12345'
        os.environ['PORT'] = '8080'
        os.environ['FLASK_DEBUG'] = 'False'

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        os.environ.pop('DATABASE_PATH', None)
        os.environ.pop('SECRET_KEY', None)
        os.environ.pop('PORT', None)
        os.environ.pop('FLASK_DEBUG', None)

    def test_database_path_auto_creation_and_seeding(self):
        """Verify DATABASE_PATH creates directories, tables, and seeds initial demo data."""
        from database import get_db_path, get_db_connection, init_db

        self.assertEqual(get_db_path(), self.custom_db)
        self.assertFalse(os.path.exists(self.custom_db))

        # Initialize DB
        init_db()

        self.assertTrue(os.path.exists(self.custom_db))
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check tables exist
        tables = [row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
        for expected in ['users', 'vendors', 'procurement', 'mse_procurement', 'gem_procurement', 'payments']:
            self.assertIn(expected, tables)

        # Check demo data counts
        user_cnt = cursor.execute("SELECT COUNT(*) AS c FROM users").fetchone()['c']
        vendor_cnt = cursor.execute("SELECT COUNT(*) AS c FROM vendors").fetchone()['c']
        proc_cnt = cursor.execute("SELECT COUNT(*) AS c FROM procurement").fetchone()['c']
        mse_cnt = cursor.execute("SELECT COUNT(*) AS c FROM mse_procurement").fetchone()['c']
        gem_cnt = cursor.execute("SELECT COUNT(*) AS c FROM gem_procurement").fetchone()['c']
        pay_cnt = cursor.execute("SELECT COUNT(*) AS c FROM payments").fetchone()['c']

        self.assertEqual(user_cnt, 1)
        self.assertEqual(vendor_cnt, 5)
        self.assertEqual(proc_cnt, 5)
        self.assertEqual(mse_cnt, 3)
        self.assertEqual(gem_cnt, 3)
        self.assertEqual(pay_cnt, 5)

        conn.close()
        print("[PASS] Database directory auto-creation, schema generation, and initial seed verified.")

    def test_no_duplicate_demo_data_and_record_preservation_on_restart(self):
        """Verify restarts do not duplicate demo data or erase existing records."""
        from database import init_db, get_db_connection

        init_db()

        # Add a custom user and custom vendor
        conn = get_db_connection()
        conn.execute("INSERT INTO vendors (vendor_id, vendor_name, email, phone, vendor_category, mse_status) VALUES (?, ?, ?, ?, ?, ?)",
                     ("VEND-CUSTOM-01", "Custom Render Vendor Pvt Ltd", "custom@render.test", "1234567890", "Goods", "MSE-Micro"))
        conn.commit()
        conn.close()

        # Simulate restart by calling init_db again
        init_db()
        init_db()

        conn = get_db_connection()
        cursor = conn.cursor()

        user_cnt = cursor.execute("SELECT COUNT(*) AS c FROM users").fetchone()['c']
        vendor_cnt = cursor.execute("SELECT COUNT(*) AS c FROM vendors").fetchone()['c']
        proc_cnt = cursor.execute("SELECT COUNT(*) AS c FROM procurement").fetchone()['c']

        # Counts must NOT duplicate (vendors should be 5 demo + 1 custom = 6)
        self.assertEqual(user_cnt, 1)
        self.assertEqual(vendor_cnt, 6)
        self.assertEqual(proc_cnt, 5)

        # Ensure custom vendor is preserved
        custom_vendor = cursor.execute("SELECT * FROM vendors WHERE vendor_id='VEND-CUSTOM-01'").fetchone()
        self.assertIsNotNone(custom_vendor)
        self.assertEqual(custom_vendor['vendor_name'], "Custom Render Vendor Pvt Ltd")

        conn.close()
        print("[PASS] Duplicate prevention and existing record preservation on restarts verified.")

    def test_secret_key_and_debug_env_vars(self):
        """Verify SECRET_KEY and FLASK_DEBUG are loaded from environment."""
        import importlib
        import app as app_module
        importlib.reload(app_module)

        self.assertEqual(app_module.app.secret_key, 'test-render-super-secret-key-12345')
        self.assertFalse(app_module.app.config['DEBUG'])
        print("[PASS] SECRET_KEY and FLASK_DEBUG environment variable loading verified.")

if __name__ == '__main__':
    unittest.main()
