"""
test_api.py - Integration and API Endpoint Tests
Tests all Flask routes, REST API endpoints, static asset delivery, and simulation controls.
"""

import unittest
import json
import time
from app import app, spooler


class TestPrinterSpoolerAPI(unittest.TestCase):

    def setUp(self):
        # Configure app for testing
        app.config["TESTING"] = True
        self.client = app.test_client()
        # Fast execution for tests
        spooler.set_speed(0.05)
        spooler.reset()

    def tearDown(self):
        spooler.pause()

    # 1. Verify index HTML route serves successfully
    def test_01_index_route(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Printer Spooler System", response.data)
        self.assertIn(b"/static/css/style.css", response.data)
        self.assertIn(b"/static/js/script.js", response.data)

    # 2. Verify static assets exist and are served by Flask
    def test_02_static_assets_served(self):
        css_res = self.client.get("/static/css/style.css")
        self.assertEqual(css_res.status_code, 200)
        self.assertIn(b"--primary:", css_res.data)
        css_res.close()

        js_res = self.client.get("/static/js/script.js")
        self.assertEqual(js_res.status_code, 200)
        self.assertIn(b"Printer Spooler", js_res.data)
        js_res.close()

    # 3. Verify GET /api/status returns valid schema
    def test_03_get_status(self):
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        status = data["data"]
        self.assertIn("simulation_state", status)
        self.assertIn("printer_state", status)
        self.assertIn("counts", status)
        self.assertIn("total", status["counts"])
        self.assertIn("total_pages_printed", status)

    # 4. Verify GET /api/jobs returns job list
    def test_04_get_jobs(self):
        response = self.client.get("/api/jobs")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertIsInstance(data["data"], list)

    # 5. Verify GET /api/logs returns recent logs
    def test_05_get_logs(self):
        response = self.client.get("/api/logs?limit=10")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertIsInstance(data["data"], list)

    # 6. Verify POST /api/jobs with valid data creates a job
    def test_06_submit_valid_job_api(self):
        payload = {
            "user_name": "API Tester",
            "document_name": "Test_Spec.pdf",
            "pages": 3,
        }
        response = self.client.post("/api/jobs", json=payload)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["user_name"], "API Tester")
        self.assertEqual(data["data"]["pages"], 3)

    # 7. Verify POST /api/jobs rejects invalid data
    def test_07_submit_invalid_job_api(self):
        # Empty user name
        res = self.client.post("/api/jobs", json={"user_name": "", "document_name": "Doc.pdf", "pages": 3})
        self.assertEqual(res.status_code, 400)

        # Empty doc name
        res = self.client.post("/api/jobs", json={"user_name": "Bob", "document_name": "  ", "pages": 3})
        self.assertEqual(res.status_code, 400)

        # Zero or negative pages
        res = self.client.post("/api/jobs", json={"user_name": "Bob", "document_name": "Doc.pdf", "pages": 0})
        self.assertEqual(res.status_code, 400)
        res = self.client.post("/api/jobs", json={"user_name": "Bob", "document_name": "Doc.pdf", "pages": -4})
        self.assertEqual(res.status_code, 400)

        # Fractional pages (must be rejected!)
        res = self.client.post("/api/jobs", json={"user_name": "Bob", "document_name": "Doc.pdf", "pages": 4.5})
        self.assertEqual(res.status_code, 400)

        # Exceeds 200 pages
        res = self.client.post("/api/jobs", json={"user_name": "Bob", "document_name": "Doc.pdf", "pages": 300})
        self.assertEqual(res.status_code, 400)

        # Non-JSON body
        res = self.client.post("/api/jobs", data="not-json", content_type="text/plain")
        self.assertEqual(res.status_code, 400)

    # 8. Verify POST /api/jobs/<job_id>/cancel
    def test_08_cancel_job_api(self):
        # Pause so job stays WAITING
        self.client.post("/api/simulation/pause")

        # Submit job
        sub_res = self.client.post(
            "/api/jobs", json={"user_name": "CancelTester", "document_name": "ToCancel.pdf", "pages": 2}
        )
        job_id = json.loads(sub_res.data)["data"]["job_id"]

        # Cancel waiting job
        cancel_res = self.client.post(f"/api/jobs/{job_id}/cancel")
        self.assertEqual(cancel_res.status_code, 200)
        cdata = json.loads(cancel_res.data)
        self.assertTrue(cdata["success"])
        self.assertEqual(cdata["data"]["status"], "CANCELLED")

        # Cancel non-existent job returns 404
        nf_res = self.client.post("/api/jobs/99999/cancel")
        self.assertEqual(nf_res.status_code, 404)

    # 9. Verify batch concurrent submissions
    def test_09_batch_demo_api(self):
        response = self.client.post("/api/jobs/batch", json={})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertEqual(len(data["data"]), 4)

    # 10. Verify simulation control endpoints
    def test_10_simulation_controls_api(self):
        # Pause
        res = self.client.post("/api/simulation/pause")
        self.assertEqual(res.status_code, 200)
        status = json.loads(res.data)["data"]
        self.assertEqual(status["simulation_state"], "PAUSED")

        # Resume
        res = self.client.post("/api/simulation/resume")
        self.assertEqual(res.status_code, 200)
        status = json.loads(res.data)["data"]
        self.assertEqual(status["simulation_state"], "RUNNING")

        # Speed adjustment
        res = self.client.post("/api/simulation/speed", json={"speed": 0.3})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(spooler.page_duration, 0.3)

        # Reset
        res = self.client.post("/api/simulation/reset")
        self.assertEqual(res.status_code, 200)
        status = json.loads(res.data)["data"]
        self.assertEqual(status["counts"]["total"], 0)
        self.assertIsNone(status["active_job"])


if __name__ == "__main__":
    unittest.main()
