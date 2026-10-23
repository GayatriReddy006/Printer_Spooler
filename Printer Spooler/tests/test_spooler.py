"""
test_spooler.py - Comprehensive Unit & Integration Tests
Tests all 14 scenarios specified in the project requirements:
1. Valid job submission
2. Reject empty user/doc names
3. Reject 0, negative, or non-integer page counts
4. FIFO queue processing order
5. Single-job printing mutual exclusion
6. Concurrent job submissions from multiple threads
7. Safe cancellation of waiting job
8. Reject cancellation of printing or completed jobs
9. Pause simulation waits for active job to finish safely
10. Resume simulation continues queued jobs
11. Reset clears queue, history, and state safely
12. Repeated Start requests do not duplicate worker threads
13. Shared counters and states remain consistent
14. Worker thread cleanly shuts down without hanging
"""

import unittest
import time
import threading
from spooler import PrinterSpooler, PrintJob, ActivityLog


class TestPrinterSpooler(unittest.TestCase):

    def setUp(self):
        # Use very fast page duration (0.05s) for quick test execution
        self.spooler = PrinterSpooler(page_duration=0.05, max_job_duration=2.0, auto_start=True)

    def tearDown(self):
        # Safely shut down worker thread
        self.spooler._stop_event.set()
        self.spooler._pause_event.set()
        if self.spooler._worker_thread and self.spooler._worker_thread.is_alive():
            self.spooler._worker_thread.join(timeout=1.0)

    # 1. Submit a valid print job
    def test_01_submit_valid_job(self):
        job = self.spooler.submit_job("Alice", "Thesis_Chapter1.pdf", 5)
        self.assertIsNotNone(job)
        self.assertEqual(job["job_id"], 1)
        self.assertEqual(job["user_name"], "Alice")
        self.assertEqual(job["document_name"], "Thesis_Chapter1.pdf")
        self.assertEqual(job["pages"], 5)
        self.assertIn(job["status"], ["WAITING", "PRINTING"])

    # 2. Reject empty user name or document name
    def test_02_reject_empty_names(self):
        with self.assertRaises(ValueError):
            self.spooler.submit_job("", "ValidDoc.pdf", 3)
        with self.assertRaises(ValueError):
            self.spooler.submit_job("   ", "ValidDoc.pdf", 3)
        with self.assertRaises(ValueError):
            self.spooler.submit_job("Alice", "", 3)
        with self.assertRaises(ValueError):
            self.spooler.submit_job("Alice", "   ", 3)

    # 3. Reject zero, negative, or non-integer page counts
    def test_03_reject_invalid_page_counts(self):
        with self.assertRaises(ValueError):
            self.spooler.submit_job("Bob", "Doc.pdf", 0)
        with self.assertRaises(ValueError):
            self.spooler.submit_job("Bob", "Doc.pdf", -5)
        with self.assertRaises(ValueError):
            self.spooler.submit_job("Bob", "Doc.pdf", "five")
        with self.assertRaises(ValueError):
            self.spooler.submit_job("Bob", "Doc.pdf", None)
        with self.assertRaises(ValueError):
            self.spooler.submit_job("Bob", "Doc.pdf", 4.5)
        with self.assertRaises(ValueError):
            self.spooler.submit_job("Bob", "Doc.pdf", "4.5")
        with self.assertRaises(ValueError):
            self.spooler.submit_job("Bob", "Doc.pdf", True)

    # 4. Submit multiple jobs and verify FIFO processing
    def test_04_fifo_processing(self):
        # Pause spooler to load up the queue
        self.spooler.pause()
        time.sleep(0.1)

        job1 = self.spooler.submit_job("User1", "First.pdf", 1)
        job2 = self.spooler.submit_job("User2", "Second.pdf", 1)
        job3 = self.spooler.submit_job("User3", "Third.pdf", 1)

        jobs = self.spooler.get_jobs()
        self.assertEqual([j["job_id"] for j in jobs], [1, 2, 3])
        self.assertEqual([j["user_name"] for j in jobs], ["User1", "User2", "User3"])

        # Resume and let them process in order
        self.spooler.resume()
        # Wait for all 3 jobs (each 1 page * 0.05s = ~0.15s)
        time.sleep(0.5)

        updated_jobs = self.spooler.get_jobs()
        for j in updated_jobs:
            self.assertEqual(j["status"], "COMPLETED")

    # 5. Verify that only one job prints at any time (Mutual Exclusion)
    def test_05_mutual_exclusion(self):
        # Submit 3 jobs with several pages each
        self.spooler.submit_job("A", "DocA.pdf", 4)
        self.spooler.submit_job("B", "DocB.pdf", 4)
        self.spooler.submit_job("C", "DocC.pdf", 4)

        # Poll multiple times during active printing
        for _ in range(8):
            status = self.spooler.get_status()
            printing_count = status["counts"]["printing"]
            # Crucial assertion: never more than 1 job in PRINTING state simultaneously
            self.assertLessEqual(printing_count, 1)
            time.sleep(0.04)

    # 6. Submit jobs concurrently from multiple threads
    def test_06_concurrent_submissions(self):
        num_threads = 10
        threads = []
        errors = []

        def worker_task(idx):
            try:
                self.spooler.submit_job(f"User_{idx}", f"File_{idx}.pdf", 1)
            except Exception as e:
                errors.append(e)

        for i in range(num_threads):
            t = threading.Thread(target=worker_task, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        status = self.spooler.get_status()
        self.assertEqual(status["counts"]["total"], num_threads)

    # 7. Cancel a waiting job successfully
    def test_07_cancel_waiting_job(self):
        # Pause so jobs remain WAITING
        self.spooler.pause()
        time.sleep(0.1)

        j1 = self.spooler.submit_job("UserA", "Doc1.pdf", 2)
        j2 = self.spooler.submit_job("UserB", "Doc2.pdf", 2)

        # Cancel job 2 while in queue
        cancelled = self.spooler.cancel_job(j2["job_id"])
        self.assertEqual(cancelled["status"], "CANCELLED")

        # Resume and ensure job 1 prints, job 2 skipped
        self.spooler.resume()
        time.sleep(0.3)

        jobs = self.spooler.get_jobs()
        job2_final = [j for j in jobs if j["job_id"] == j2["job_id"]][0]
        self.assertEqual(job2_final["status"], "CANCELLED")

    # 8. Reject cancellation of a printing or completed job
    def test_08_reject_cancel_printing_or_completed(self):
        j = self.spooler.submit_job("Alice", "LongDoc.pdf", 6)
        # Wait until it enters PRINTING
        time.sleep(0.08)
        status = self.spooler.get_status()
        if status["active_job"] and status["active_job"]["job_id"] == j["job_id"]:
            with self.assertRaises(ValueError):
                self.spooler.cancel_job(j["job_id"])

        # Wait until job completes
        time.sleep(0.5)
        # Cannot cancel completed job
        with self.assertRaises(ValueError):
            self.spooler.cancel_job(j["job_id"])

    # 9. Verify that pause waits for the active job to finish
    def test_09_pause_finishes_active_job(self):
        # Submit a multi-page job and a second job
        j1 = self.spooler.submit_job("User1", "Job1.pdf", 3)
        j2 = self.spooler.submit_job("User2", "Job2.pdf", 2)

        time.sleep(0.06)  # j1 is now printing
        self.spooler.pause()

        # Job 1 must finish even though paused
        time.sleep(0.3)
        jobs = self.spooler.get_jobs()
        j1_state = [j for j in jobs if j["job_id"] == j1["job_id"]][0]
        j2_state = [j for j in jobs if j["job_id"] == j2["job_id"]][0]

        self.assertEqual(j1_state["status"], "COMPLETED")
        # Job 2 should still be waiting because simulation is paused
        self.assertEqual(j2_state["status"], "WAITING")

    # 10. Verify that resume continues queued jobs
    def test_10_resume_continues_queue(self):
        self.spooler.pause()
        time.sleep(0.05)
        j = self.spooler.submit_job("UserResume", "ResumeDoc.pdf", 1)

        self.assertEqual(self.spooler.get_status()["simulation_state"], "PAUSED")
        self.spooler.resume()
        self.assertEqual(self.spooler.get_status()["simulation_state"], "RUNNING")

        time.sleep(0.2)
        jobs = self.spooler.get_jobs()
        target = [item for item in jobs if item["job_id"] == j["job_id"]][0]
        self.assertEqual(target["status"], "COMPLETED")

    # 11. Verify that reset clears the simulation safely
    def test_11_reset_clears_simulation(self):
        self.spooler.submit_job("UserA", "DocA.pdf", 3)
        self.spooler.submit_job("UserB", "DocB.pdf", 3)
        time.sleep(0.1)

        worker_before = self.spooler._worker_thread
        gen_before = self.spooler._generation
        self.spooler.reset()
        status = self.spooler.get_status()

        self.assertFalse(worker_before.is_alive())
        self.assertGreater(self.spooler._generation, gen_before)
        self.assertIsNot(self.spooler._worker_thread, worker_before)
        self.assertEqual(status["counts"]["total"], 0)
        self.assertEqual(status["counts"]["waiting"], 0)
        self.assertIsNone(status["active_job"])
        self.assertEqual(len(self.spooler.get_jobs()), 0)
        self.assertTrue(status["worker_alive"])

    # 12. Verify that repeated Start requests do not create duplicate workers
    def test_12_repeated_start_idempotent(self):
        worker1 = self.spooler._worker_thread
        # Call start multiple times
        self.spooler.start()
        self.spooler.start()
        self.spooler.start()
        # The worker thread reference should be identical
        self.assertIs(self.spooler._worker_thread, worker1)

    # 13. Verify shared counters and job states remain consistent
    def test_13_state_and_counter_consistency(self):
        for i in range(5):
            self.spooler.submit_job(f"User_{i}", f"Doc_{i}.pdf", 1)

        time.sleep(0.5)
        status = self.spooler.get_status()
        counts = status["counts"]

        self.assertEqual(
            counts["total"],
            counts["waiting"] + counts["printing"] + counts["completed"] + counts["cancelled"] + counts["failed"],
        )
        self.assertEqual(status["total_pages_printed"], 5)

    # 14. Verify that worker threads can shut down without hanging
    def test_14_clean_shutdown(self):
        self.spooler._stop_event.set()
        self.spooler._pause_event.set()
        # Worker should terminate promptly
        self.spooler._worker_thread.join(timeout=1.0)
        self.assertFalse(self.spooler._worker_thread.is_alive())


if __name__ == "__main__":
    unittest.main()
