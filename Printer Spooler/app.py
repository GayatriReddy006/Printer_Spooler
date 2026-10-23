"""
app.py - Flask Web Application & REST API
Exposes endpoints for job management, simulation controls, and real-time status monitoring.
"""

from flask import Flask, render_template, jsonify, request
from spooler import PrinterSpooler

app = Flask(__name__)

# Initialize single global PrinterSpooler instance
# Default page_duration is 0.8s for smooth, interactive visual demonstration
spooler = PrinterSpooler(page_duration=0.8, max_job_duration=12.0, auto_start=True)


@app.route("/")
def index():
    """Render the main single-page dashboard."""
    return render_template("index.html")


# -----------------------------------------------------------------------------
# REST API: Status & Inspection
# -----------------------------------------------------------------------------
@app.route("/api/status", methods=["GET"])
def get_status():
    """Return printer state, simulation state, active job, and statistics."""
    try:
        status = spooler.get_status()
        return jsonify({"success": True, "data": status}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    """Return all print jobs ordered by submission ID."""
    try:
        jobs = spooler.get_jobs()
        return jsonify({"success": True, "data": jobs}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/logs", methods=["GET"])
def get_logs():
    """Return recent activity logs."""
    try:
        limit = request.args.get("limit", default=50, type=int)
        logs = spooler.get_logs(limit=limit)
        return jsonify({"success": True, "data": logs}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# -----------------------------------------------------------------------------
# REST API: Job Submission & Cancellation
# -----------------------------------------------------------------------------
@app.route("/api/jobs", methods=["POST"])
def submit_job():
    """Submit a new print job to the spooler."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "error": "Request body must be valid JSON."}), 400

    user_name = data.get("user_name")
    document_name = data.get("document_name")
    pages = data.get("pages")

    try:
        job = spooler.submit_job(user_name=user_name, document_name=document_name, pages=pages)
        return jsonify({
            "success": True,
            "message": f"Print job #{job['job_id']} submitted successfully.",
            "data": job
        }), 201
    except ValueError as val_err:
        return jsonify({"success": False, "error": str(val_err)}), 400
    except Exception as exc:
        return jsonify({"success": False, "error": f"Internal server error: {str(exc)}"}), 500


@app.route("/api/jobs/<int:job_id>/cancel", methods=["POST"])
def cancel_job(job_id):
    """Cancel a waiting job."""
    try:
        cancelled_job = spooler.cancel_job(job_id)
        return jsonify({
            "success": True,
            "message": f"Job #{job_id} cancelled successfully.",
            "data": cancelled_job
        }), 200
    except KeyError as k_err:
        return jsonify({"success": False, "error": str(k_err)}), 404
    except ValueError as val_err:
        return jsonify({"success": False, "error": str(val_err)}), 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/jobs/batch", methods=["POST"])
def submit_batch_jobs():
    """
    Simulate multiple concurrent users submitting print jobs simultaneously.
    Demonstrates thread safety and race condition avoidance.
    """
    data = request.get_json(silent=True) or {}
    sample_jobs = data.get("jobs", [
        {"user_name": "Alice (Finance)", "document_name": "Q3_Budget_Audit.xlsx", "pages": 4},
        {"user_name": "Bob (DevOps)", "document_name": "Server_Topology.pdf", "pages": 3},
        {"user_name": "Charlie (Legal)", "document_name": "NDA_Agreement_Final.docx", "pages": 5},
        {"user_name": "Diana (HR)", "document_name": "Offer_Letter_Pack.pdf", "pages": 2},
    ])

    results = spooler.submit_concurrent_demo_jobs(sample_jobs)
    return jsonify({
        "success": True,
        "message": f"{len(sample_jobs)} concurrent jobs dispatched.",
        "data": results
    }), 200


# -----------------------------------------------------------------------------
# REST API: Simulation Controls
# -----------------------------------------------------------------------------
@app.route("/api/simulation/start", methods=["POST"])
def start_simulation():
    """Start or resume the spooler simulation worker."""
    try:
        spooler.start()
        return jsonify({"success": True, "message": "Simulation started successfully.", "data": spooler.get_status()}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/simulation/pause", methods=["POST"])
def pause_simulation():
    """Pause the spooler simulation safely after any current job completes."""
    try:
        spooler.pause()
        return jsonify({"success": True, "message": "Simulation pause signaled.", "data": spooler.get_status()}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/simulation/resume", methods=["POST"])
def resume_simulation():
    """Resume processing the print queue."""
    try:
        spooler.resume()
        return jsonify({"success": True, "message": "Simulation resumed.", "data": spooler.get_status()}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/simulation/reset", methods=["POST"])
def reset_simulation():
    """Safely reset queue, history, and worker state."""
    try:
        spooler.reset()
        return jsonify({"success": True, "message": "Simulation reset successfully.", "data": spooler.get_status()}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/simulation/speed", methods=["POST"])
def set_speed():
    """Adjust simulated print duration per page."""
    data = request.get_json(silent=True) or {}
    speed = data.get("speed", 0.8)
    try:
        spooler.set_speed(float(speed))
        return jsonify({"success": True, "message": f"Printing speed set to {float(speed)}s/page."}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


if __name__ == "__main__":
    print("=" * 60)
    print(" Printer Spooler System (Dining Philosophers Synchronization)")
    print(" Running at http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=True)
