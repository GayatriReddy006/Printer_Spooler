"""
spooler.py - Core Printer Spooler & Synchronization Engine
Demonstrates Multithreading, Mutual Exclusion, FIFO Scheduling,
and Deadlock Prevention.
"""

import threading
import queue
import time
from datetime import datetime
from typing import Dict, List, Optional, Any


class PrintJob:
    """Represents a print job in the spooler system."""

    def __init__(self, job_id: int, user_name: str, document_name: str, pages: int):
        self.job_id: int = job_id
        self.user_name: str = user_name.strip()
        self.document_name: str = document_name.strip()
        self.pages: int = int(pages)
        self.submitted_at: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status: str = "WAITING"  # WAITING, PRINTING, COMPLETED, CANCELLED, FAILED
        self.progress_pages: int = 0
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.cancelled_at: Optional[str] = None
        self.error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to serializable dictionary."""
        progress_pct = 0
        if self.pages > 0:
            if self.status == "COMPLETED":
                progress_pct = 100
            elif self.status == "PRINTING":
                progress_pct = min(100, int((self.progress_pages / self.pages) * 100))

        return {
            "job_id": self.job_id,
            "user_name": self.user_name,
            "document_name": self.document_name,
            "pages": self.pages,
            "submitted_at": self.submitted_at,
            "status": self.status,
            "progress_pages": self.progress_pages,
            "progress_pct": progress_pct,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "cancelled_at": self.cancelled_at,
            "error_message": self.error_message,
        }


class ActivityLog:
    """Thread-safe circular log buffer for spooler events."""

    def __init__(self, max_entries: int = 150):
        self._max_entries = max_entries
        self._entries: List[Dict[str, Any]] = []
        self._entry_id = 0
        self._lock = threading.Lock()

    def add(self, event_type: str, message: str, level: str = "INFO") -> Dict[str, Any]:
        """Add an event to the log."""
        with self._lock:
            self._entry_id += 1
            entry = {
                "id": self._entry_id,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "event_type": event_type,
                "message": message,
                "level": level,  # INFO, SUCCESS, WARNING, ERROR, LOCK
            }
            self._entries.append(entry)
            if len(self._entries) > self._max_entries:
                self._entries.pop(0)
            return entry

    def get_entries(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return the most recent log entries."""
        with self._lock:
            return list(reversed(self._entries[-limit:]))

    def clear(self):
        """Clear all log entries."""
        with self._lock:
            self._entries.clear()
            self._entry_id = 0


class PrinterSpooler:
    """
    Simulates a centralized Printer Spooler shared across multiple network users.

    Synchronization Design:
    - self._state_lock (RLock): Protects internal state (jobs, counters, active_job_id).
    - self._printer_mutex (Lock): Represents the single physical printer hardware resource.
      Ensures strict Mutual Exclusion: only one job executes in the Critical Section at a time.
    - self._job_queue (queue.Queue): Thread-safe FIFO queue guaranteeing starvation-free,
      first-come-first-served job scheduling.
    - self._pause_event (Event): Controls execution flow (set = running, clear = paused).
    - self._stop_event (Event): Signals worker thread shutdown.
    - self._generation (int): Tracks active worker generation to prevent stale workers from
      mutating state after a reset.
    """

    def __init__(self, page_duration: float = 1.0, max_job_duration: float = 12.0, auto_start: bool = True):
        self.page_duration = float(page_duration)
        self.max_job_duration = float(max_job_duration)

        # Thread synchronization primitives
        self._state_lock = threading.RLock()
        self._printer_mutex = threading.Lock()
        self._job_queue: queue.Queue = queue.Queue()
        self._pause_event = threading.Event()
        self._stop_event = threading.Event()

        # State storage
        self._jobs: Dict[int, PrintJob] = {}
        self._job_counter: int = 0
        self._active_job_id: Optional[int] = None
        self._printer_state: str = "IDLE"  # IDLE, PRINTING, PAUSED, OFFLINE
        self._simulation_state: str = "RUNNING"  # RUNNING, PAUSED, STOPPED
        self._pages_printed_total: int = 0
        self._generation: int = 1
        self._worker_thread: Optional[threading.Thread] = None
        self._logs = ActivityLog()

        self._logs.add("SYSTEM", "Printer Spooler System initialized. Mutual Exclusion active.", "INFO")

        if auto_start:
            self.start()

    # -------------------------------------------------------------------------
    # Logging Helper
    # -------------------------------------------------------------------------
    def _log(self, event_type: str, message: str, level: str = "INFO"):
        self._logs.add(event_type, message, level)

    # -------------------------------------------------------------------------
    # Worker Thread Management
    # -------------------------------------------------------------------------
    def start(self) -> bool:
        """
        Start or resume the simulation worker thread.
        Guarantees no duplicate worker threads are spawned.
        """
        with self._state_lock:
            self._pause_event.set()
            self._simulation_state = "RUNNING"

            if self._printer_state == "PAUSED" and self._active_job_id is None:
                self._printer_state = "IDLE"

            # Check if worker thread is alive
            if self._worker_thread is not None and self._worker_thread.is_alive():
                self._log("SIMULATION", "Simulation started/already active.", "INFO")
                return True

            # Spawn new worker thread
            self._stop_event.clear()
            self._worker_thread = threading.Thread(
                target=self._worker_loop,
                args=(self._generation,),
                name=f"PrinterWorker-Gen{self._generation}",
                daemon=True,
            )
            self._worker_thread.start()
            self._log("WORKER", f"Printer worker thread started (Gen {self._generation}).", "SUCCESS")
            return True

    def pause(self) -> bool:
        """
        Pause the simulation.
        If a job is currently printing, it will finish printing safely before pausing,
        preventing inconsistent hardware or job states.
        """
        with self._state_lock:
            self._pause_event.clear()
            self._simulation_state = "PAUSED"

            if self._active_job_id is None:
                self._printer_state = "PAUSED"
                self._log("SIMULATION", "Simulation paused. Printer is now idle/paused.", "WARNING")
            else:
                self._log("SIMULATION", f"Simulation pause requested. Active Job #{self._active_job_id} will finish printing first.", "WARNING")
            return True

    def resume(self) -> bool:
        """Resume processing of waiting print jobs."""
        with self._state_lock:
            self._pause_event.set()
            self._simulation_state = "RUNNING"

            if self._active_job_id is None:
                self._printer_state = "IDLE"

            # If worker stopped or died, restart
            if self._worker_thread is None or not self._worker_thread.is_alive():
                self.start()

            self._log("SIMULATION", "Simulation resumed. Processing print queue.", "SUCCESS")
            return True

    def stop(self, timeout: float = 2.0) -> bool:
        """
        Safely stop the worker thread.
        """
        with self._state_lock:
            self._simulation_state = "STOPPED"
            self._stop_event.set()
            self._pause_event.set()
            worker = self._worker_thread

        if worker and worker.is_alive() and threading.current_thread() != worker:
            worker.join(timeout=timeout)
        return True

    def reset(self) -> bool:
        """
        Safely reset the entire simulation.
        - Stops current worker safely using generation tracking and thread join.
        - Empties the queue and clears job history.
        - Restores printer to IDLE and resets counters.
        - Restarts fresh worker thread with new generation.
        """
        with self._state_lock:
            # Invalidate previous worker generation and signal stop
            self._generation += 1
            self._stop_event.set()
            self._pause_event.set()  # Unblock if waiting in pause
            old_worker = self._worker_thread

        # Join previous worker outside state lock to prevent deadlock
        if old_worker and old_worker.is_alive() and threading.current_thread() != old_worker:
            old_worker.join(timeout=2.0)

        with self._state_lock:
            # Drain queue safely and reinitialize
            while not self._job_queue.empty():
                try:
                    self._job_queue.get_nowait()
                    self._job_queue.task_done()
                except (queue.Empty, ValueError):
                    break
            self._job_queue = queue.Queue()

            # Reset internal state
            self._jobs.clear()
            self._job_counter = 0
            self._active_job_id = None
            self._printer_state = "IDLE"
            self._simulation_state = "RUNNING"
            self._pages_printed_total = 0

            # Reset synchronization events for new generation
            self._stop_event = threading.Event()
            self._pause_event = threading.Event()
            self._pause_event.set()

            # Start fresh worker
            self._worker_thread = threading.Thread(
                target=self._worker_loop,
                args=(self._generation,),
                name=f"PrinterWorker-Gen{self._generation}",
                daemon=True,
            )
            self._worker_thread.start()

            self._logs.clear()
            self._log("RESET", "Simulation reset successfully. Queue cleared and worker reinitialized.", "SUCCESS")
            return True

    # -------------------------------------------------------------------------
    # Worker Thread Loop
    # -------------------------------------------------------------------------
    def _worker_loop(self, gen_id: int):
        """
        The continuous background thread simulating the physical printer consumer.
        Operates strictly under FIFO discipline and Mutual Exclusion.
        """
        while not self._stop_event.is_set() and self._generation == gen_id:
            # 1. Flow control: Check if simulation is paused
            if not self._pause_event.is_set():
                with self._state_lock:
                    if self._active_job_id is None:
                        self._printer_state = "PAUSED"
                self._pause_event.wait(timeout=0.2)
                continue

            # 2. Dequeue next job ID from thread-safe queue (FIFO order)
            try:
                job_id = self._job_queue.get(timeout=0.2)
            except queue.Empty:
                with self._state_lock:
                    if self._printer_state != "PAUSED" and self._active_job_id is None:
                        self._printer_state = "IDLE"
                continue

            # Exit if generation changed or stopped
            if self._stop_event.is_set() or self._generation != gen_id:
                break

            # 3. Check if job was cancelled while waiting in queue
            with self._state_lock:
                if self._generation != gen_id:
                    break
                job = self._jobs.get(job_id)
                if not job or job.status == "CANCELLED":
                    self._job_queue.task_done()
                    continue

                # Transition state to PRINTING atomically
                job.status = "PRINTING"
                job.started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._active_job_id = job_id
                self._printer_state = "PRINTING"
                user_name = job.user_name
                doc_name = job.document_name
                pages = job.pages

            self._log(
                "LOCK_ACQUIRED",
                f"MUTEX ACQUIRED: Printer granted exclusively to Job #{job_id} ({user_name}). Entering Critical Section.",
                "LOCK",
            )
            self._log(
                "PRINT_START",
                f"Started printing Job #{job_id}: '{doc_name}' ({pages} pages) for user '{user_name}'.",
                "INFO",
            )

            # 4. Critical Section: Mutual Exclusion on physical printer
            # Only ONE job can hold self._printer_mutex at any instant!
            with self._printer_mutex:
                try:
                    # Calculate per-page sleep time with duration cap
                    sleep_per_page = self.page_duration
                    if (pages * sleep_per_page) > self.max_job_duration:
                        sleep_per_page = max(0.05, self.max_job_duration / pages)

                    # Simulate page-by-page printing
                    for page in range(1, pages + 1):
                        if self._stop_event.is_set() or self._generation != gen_id:
                            break

                        # CRITICAL: Sleep happens OUTSIDE the state lock!
                        # We use _stop_event.wait(timeout) so that if stop or reset occurs,
                        # the worker wakes up immediately without lagging.
                        if self._stop_event.wait(timeout=sleep_per_page):
                            break

                        if self._generation != gen_id:
                            break

                        # Update job progress under state lock
                        with self._state_lock:
                            if self._generation == gen_id and job.status == "PRINTING":
                                job.progress_pages = page

                    # Mark job completed
                    with self._state_lock:
                        if self._generation == gen_id and not self._stop_event.is_set() and job.status == "PRINTING":
                            job.status = "COMPLETED"
                            job.progress_pages = pages
                            job.completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            self._pages_printed_total += pages
                            self._log(
                                "PRINT_COMPLETE",
                                f"Job #{job_id} ('{doc_name}') completed successfully ({pages}/{pages} pages printed).",
                                "SUCCESS",
                            )
                except Exception as exc:
                    with self._state_lock:
                        if self._generation == gen_id:
                            job.status = "FAILED"
                            job.error_message = str(exc)
                            self._log("ERROR", f"Job #{job_id} failed with error: {exc}", "ERROR")
                finally:
                    # Release printer resource and update state
                    with self._state_lock:
                        if self._generation == gen_id:
                            self._active_job_id = None
                            if not self._pause_event.is_set():
                                self._printer_state = "PAUSED"
                            else:
                                self._printer_state = "IDLE"
                            self._log(
                                "LOCK_RELEASED",
                                f"MUTEX RELEASED: Job #{job_id} exited Critical Section. Printer resource free.",
                                "INFO",
                            )
                    try:
                        self._job_queue.task_done()
                    except (ValueError, RuntimeError):
                        pass

    # -------------------------------------------------------------------------
    # Job Submission & Cancellation
    # -------------------------------------------------------------------------
    def submit_job(self, user_name: str, document_name: str, pages: Any) -> Dict[str, Any]:
        """
        Validate and submit a new print job.
        Thread-safe: can be called concurrently by multiple user threads.
        """
        # 1. Validation
        if not user_name or not isinstance(user_name, str) or not user_name.strip():
            raise ValueError("User name is required and cannot be empty.")

        clean_user = user_name.strip()
        if len(clean_user) > 50:
            raise ValueError("User name cannot exceed 50 characters.")

        if not document_name or not isinstance(document_name, str) or not document_name.strip():
            raise ValueError("Document name is required and cannot be empty.")

        clean_doc = document_name.strip()
        if len(clean_doc) > 100:
            raise ValueError("Document name cannot exceed 100 characters.")

        if isinstance(pages, bool):
            raise ValueError("Number of pages must be a valid integer.")

        if isinstance(pages, float):
            if not pages.is_integer():
                raise ValueError("Number of pages cannot be a fractional value.")
            pages_int = int(pages)
        elif isinstance(pages, int):
            pages_int = pages
        elif isinstance(pages, str):
            clean_pages = pages.strip()
            if "." in clean_pages:
                raise ValueError("Number of pages cannot be a fractional value.")
            try:
                pages_int = int(clean_pages)
            except (ValueError, TypeError):
                raise ValueError("Number of pages must be a valid integer.")
        else:
            raise ValueError("Number of pages must be a valid integer.")

        if pages_int <= 0:
            raise ValueError("Number of pages must be a positive integer greater than zero.")

        if pages_int > 200:
            raise ValueError("Number of pages cannot exceed 200 for simulated jobs.")

        # 2. Atomic Job Creation & Queue Enqueue
        with self._state_lock:
            self._job_counter += 1
            new_id = self._job_counter
            job = PrintJob(
                job_id=new_id,
                user_name=clean_user,
                document_name=clean_doc,
                pages=pages_int,
            )
            self._jobs[new_id] = job
            self._job_queue.put(new_id)

            self._log(
                "SUBMIT",
                f"Job #{new_id} ('{clean_doc}', {pages_int} pages) submitted by '{clean_user}'.",
                "INFO",
            )
            self._log(
                "QUEUE",
                f"Job #{new_id} placed in FIFO Print Queue (Position: {self._job_queue.qsize()}).",
                "INFO",
            )

            return job.to_dict()

    def cancel_job(self, job_id: int) -> Dict[str, Any]:
        """
        Cancel a print job.
        Rules:
        - Only jobs in 'WAITING' status can be cancelled.
        - Jobs currently 'PRINTING' or already 'COMPLETED' cannot be cancelled.
        """
        try:
            jid = int(job_id)
        except (ValueError, TypeError):
            raise ValueError("Invalid job ID format.")

        with self._state_lock:
            job = self._jobs.get(jid)
            if not job:
                raise KeyError(f"Job #{jid} does not exist.")

            if job.status == "PRINTING":
                raise ValueError(f"Cannot cancel Job #{jid}: The job is currently printing and holding the printer resource.")

            if job.status == "COMPLETED":
                raise ValueError(f"Cannot cancel Job #{jid}: The job has already completed.")

            if job.status == "CANCELLED":
                raise ValueError(f"Job #{jid} is already cancelled.")

            if job.status != "WAITING":
                raise ValueError(f"Cannot cancel Job #{jid} with status '{job.status}'.")

            # Atomically mark as cancelled
            job.status = "CANCELLED"
            job.cancelled_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            self._log("CANCEL", f"Job #{jid} ('{job.document_name}') cancelled by user '{job.user_name}'.", "WARNING")
            return job.to_dict()

    # -------------------------------------------------------------------------
    # Batch / Multi-User Simulation Helper
    # -------------------------------------------------------------------------
    def submit_concurrent_demo_jobs(self, jobs_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Simulate multiple client threads submitting jobs simultaneously.
        Demonstrates race-condition resistance and atomic queue ordering.
        """
        results = []
        threads = []
        lock = threading.Lock()

        def worker_submit(item):
            try:
                res = self.submit_job(item.get("user_name"), item.get("document_name"), item.get("pages"))
                with lock:
                    results.append({"success": True, "job": res})
            except Exception as e:
                with lock:
                    results.append({"success": False, "error": str(e)})

        for item in jobs_data:
            t = threading.Thread(target=worker_submit, args=(item,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        return results

    # -------------------------------------------------------------------------
    # Getters & Introspection
    # -------------------------------------------------------------------------
    def get_status(self) -> Dict[str, Any]:
        """Return comprehensive status of the printer and simulation."""
        with self._state_lock:
            active_job_dict = None
            if self._active_job_id and self._active_job_id in self._jobs:
                active_job_dict = self._jobs[self._active_job_id].to_dict()

            waiting_count = 0
            printing_count = 0
            completed_count = 0
            cancelled_count = 0
            failed_count = 0

            for j in self._jobs.values():
                if j.status == "WAITING":
                    waiting_count += 1
                elif j.status == "PRINTING":
                    printing_count += 1
                elif j.status == "COMPLETED":
                    completed_count += 1
                elif j.status == "CANCELLED":
                    cancelled_count += 1
                elif j.status == "FAILED":
                    failed_count += 1

            printer_locked = self._active_job_id is not None

            return {
                "simulation_state": self._simulation_state,  # RUNNING, PAUSED, STOPPED
                "printer_state": self._printer_state,        # IDLE, PRINTING, PAUSED, OFFLINE
                "printer_locked": printer_locked,
                "active_job": active_job_dict,
                "counts": {
                    "total": len(self._jobs),
                    "waiting": waiting_count,
                    "printing": printing_count,
                    "completed": completed_count,
                    "cancelled": cancelled_count,
                    "failed": failed_count,
                },
                "total_pages_printed": self._pages_printed_total,
                "queue_length": self._job_queue.qsize(),
                "page_duration": self.page_duration,
                "worker_alive": self._worker_thread.is_alive() if self._worker_thread else False,
            }

    def get_jobs(self) -> List[Dict[str, Any]]:
        """Return all jobs ordered by ID (FIFO submission sequence)."""
        with self._state_lock:
            return [job.to_dict() for job in sorted(self._jobs.values(), key=lambda j: j.job_id)]

    def get_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recent activity logs."""
        return self._logs.get_entries(limit=limit)

    def set_speed(self, page_duration: float):
        """Allow dynamic configuration of simulation speed."""
        dur = float(page_duration)
        if dur < 0.05:
            dur = 0.05
        if dur > 5.0:
            dur = 5.0
        self.page_duration = dur
        self._log("CONFIG", f"Printing speed updated: {self.page_duration:.2f}s per page.", "INFO")
