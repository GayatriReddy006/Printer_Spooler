# Printer Spooler System
### Process Synchronization & Dining Philosophers Resource Model

An interactive operating system simulation demonstrating **Multithreading**, **Mutual Exclusion (Mutex)**, **FIFO Scheduling**, **Starvation-Freedom**, and **Deadlock Prevention** through the classic **Dining Philosophers** analogy.

---

## 🌟 Key Features

- **Centralized FIFO Spooler**: Simulates a high-performance print spooler that decouples client applications from slow printing hardware.
- **Strict Mutual Exclusion (Mutex)**: Protects physical printer hardware access using `threading.Lock`. Ensures only one print job occupies the Critical Section at any time.
- **Starvation-Free FIFO Discipline**: Uses Python's thread-safe `queue.Queue` to service print jobs in exact submission sequence.
- **Deadlock Prevention**: Mathematically eliminates deadlocks by breaking Coffman's *Circular Wait* and *Hold and Wait* conditions.
- **Multi-User Traffic Simulation**: Dispatches concurrent print requests across multiple simultaneous threads to prove thread safety and race-condition immunity.
- **Dynamic Dining Philosophers Visualization**: Real-time SVG topology displaying client threads (philosophers) transitioning between *Thinking (Idle)*, *Hungry (Queued)*, *Eating (Mutex Held)*, and *Finished*.
- **Interactive Control Panel**: Start, Pause (with active job drain protection), Resume, Reset (with generation tracking and worker shutdown synchronization), and dynamic print speed tuning (0.3s to 1.5s per page).
- **Live Activity Log Stream**: Monitored real-time event trace of lock acquisitions, releases, queue operations, and state transitions.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.10+ & Flask 3.x
- **Concurrency & Synchronization Primitives**:
  - `threading.Lock`: Mutual exclusion lock for the physical printer resource.
  - `threading.RLock`: Re-entrant lock for internal spooler state variables and job dictionaries.
  - `threading.Event`: Flow control signals (`_pause_event`, `_stop_event`) for safe pauses and instant worker cancellation.
  - `queue.Queue`: Thread-safe FIFO scheduling queue.
- **Frontend**: Vanilla HTML5, CSS3 (Modern Glassmorphism & Card System), and Vanilla JavaScript (ES6+ `fetch()` API). No external frameworks required.
- **Testing**: Python `unittest` framework (24 passing unit & API integration tests).

---

## 📁 Project Directory Structure

```text
Printer Spooler/
├── app.py                      # Flask web application & REST API routes
├── spooler.py                  # Core multithreaded spooler & synchronization engine
├── requirements.txt            # Python dependencies (Flask>=3.0.0)
├── README.md                   # Beginner-friendly setup, theory & user guide
├── templates/
│   └── index.html              # Modern, responsive dashboard interface
├── static/
│   ├── css/
│   │   └── style.css           # Complete responsive stylesheet & animations
│   └── js/
│       └── script.js           # Vanilla JS connecting dashboard to Flask API
└── tests/
    ├── test_spooler.py         # 14 core unit tests for multithreading & synchronization
    └── test_api.py             # 10 integration tests for Flask REST endpoints & assets
```

---

## 💻 Windows Installation & Setup Guide

### 1. Prerequisites
Ensure you have **Python 3.10 or newer** installed on your system. You can verify this in PowerShell or Command Prompt:

```powershell
python --version
```

### 2. Open Project Folder
Open PowerShell and navigate to the project directory:

```powershell
cd "c:\Users\gayat\OneDrive\Desktop\Printer Spooler"
```

### 3. Create a Virtual Environment (Recommended)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(If PowerShell displays an execution policy restriction, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in your session).*

### 4. Install Dependencies
```powershell
pip install -r requirements.txt
```

---

## 🚀 Running the Application

Start the Flask server with:

```powershell
python app.py
```

You should see output similar to:
```text
============================================================
 Printer Spooler System (Dining Philosophers Synchronization)
 Running at http://127.0.0.1:5000
============================================================
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

Open your browser and navigate to:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🧪 Running Automated Tests

To run the complete automated test suite (24 unit and API integration tests):

```powershell
python -m unittest discover -s tests
```

To run individual test files:
```powershell
# Core synchronization tests (14 tests)
python -m unittest tests/test_spooler.py

# REST API & frontend integration tests (10 tests)
python -m unittest tests/test_api.py
```

---

## 🔬 Operating System Concepts & Synchronization Explanations

### 1. What is a Spooler (SPOOL)?
**SPOOL** stands for *Simultaneous Peripheral Operations On-Line*. Physical output devices (like printers) operate several orders of magnitude slower than CPUs and application threads. Without a spooler, an application printing a 50-page document would freeze while waiting for each page to physically print. A spooler accepts the job into a memory buffer/queue, allows the client thread to continue immediately, and delegates printing to a dedicated background consumer worker.

### 2. Critical Section & Mutual Exclusion (Mutex)
The physical printer is a **non-shareable resource**. If two threads send text to the printer at the same time, lines of text would interleave, resulting in corrupted output. The code segment that interacts with the printer is the **Critical Section**. We enforce **Mutual Exclusion** using `threading.Lock`:
```python
with self._printer_mutex:
    # Only ONE job can execute this section at any instant!
    for page in range(1, pages + 1):
        ...
```

### 3. FIFO Scheduling & Starvation Freedom
Jobs are managed using `queue.Queue`. Because requests are dequeued strictly in first-come, first-served order, every job is guaranteed to be processed eventually. No process suffers from indefinite postponement (**Starvation Freedom**).

### 4. Deadlock Prevention via Coffman Conditions
According to Edward G. Coffman Jr. (1971), deadlock requires four simultaneous conditions:
1. **Mutual Exclusion**: Resources cannot be shared. *(Present by hardware necessity)*
2. **Hold and Wait**: A process holds a resource while requesting another. *(Eliminated: client threads never hold resources; they enqueue a request and release)*
3. **No Preemption**: Resources cannot be forcibly seized. *(Present: active print jobs are never aborted midway)*
4. **Circular Wait**: A closed chain of processes exists where each waits for a resource held by the next. *(Eliminated: all jobs request access through a single linear FIFO queue)*

By breaking **Hold and Wait** and **Circular Wait**, our system is mathematically immune to deadlocks.

### 5. Safe Reset & Worker Thread Lifecycle
When resetting the simulation:
- The active worker generation counter (`self._generation`) is incremented.
- The previous worker's stop event (`_stop_event`) is signaled.
- The main thread joins the previous worker **outside** the state lock, guaranteeing that the old thread exits completely before a new worker thread is spawned.
- An old worker is prevented from mutating the state of subsequent worker generations.

---

## 📡 REST API Reference

| Endpoint | Method | Description |
|:---|:---:|:---|
| `/` | `GET` | Renders the single-page dashboard. |
| `/api/status` | `GET` | Returns printer status, simulation state, active job, and statistics. |
| `/api/jobs` | `GET` | Returns all print jobs in FIFO submission order. |
| `/api/logs` | `GET` | Returns the most recent activity log entries. |
| `/api/jobs` | `POST` | Submits a print job (`user_name`, `document_name`, `pages`). |
| `/api/jobs/<job_id>/cancel` | `POST` | Cancels a waiting job. Rejects jobs currently printing or completed. |
| `/api/jobs/batch` | `POST` | Dispatches 4 concurrent jobs simultaneously across separate client threads. |
| `/api/simulation/start` | `POST` | Starts or unpauses the background worker thread. |
| `/api/simulation/pause` | `POST` | Safely pauses processing after the current active job finishes. |
| `/api/simulation/resume` | `POST` | Resumes queue processing. |
| `/api/simulation/reset` | `POST` | Drains queue, resets counters, and restarts a fresh worker thread. |
| `/api/simulation/speed` | `POST` | Sets simulated duration per page (`speed` in seconds). |

---

## 🎓 Viva / Oral Exam Quick Reference

- **Q: Why use `queue.Queue` instead of a Python `list`?**
  - *A:* `queue.Queue` provides built-in thread synchronization with blocking `get()` and thread-safe atomic `put()`. Python lists require manual locking and risk race conditions when multiple threads append/pop simultaneously.
- **Q: Why does pausing allow the current job to finish?**
  - *A:* Abruptly killing a thread during an active print job leaves shared hardware in an undefined state and causes paper jams or corrupted files. The spooler honors the pause after the current job safely exits the Critical Section.
- **Q: How does this map to Dining Philosophers?**
  - *A:* Philosophers represent competing client threads. The forks/table resource represents the shared printer. By placing requests into a centralized FIFO queue rather than letting threads scramble to acquire multiple locks, deadlock and starvation are prevented.
