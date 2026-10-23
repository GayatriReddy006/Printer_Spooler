/**
 * script.js - Printer Spooler & Dining Philosophers Dashboard
 * Vanilla JavaScript implementation connecting the frontend interface to the Flask REST API.
 * Multithreaded OS simulation monitoring, process synchronization, and visualizer.
 */

(function () {
    'use strict';

    // -------------------------------------------------------------------------
    // 1. State Management & Configuration
    // -------------------------------------------------------------------------
    const POLLING_INTERVAL_MS = 1000;
    let pollTimer = null;
    let isPollingActive = true;
    let lastRenderedLogId = 0;
    let currentSpeed = 0.8;

    // Fixed / baseline philosopher profiles for the Dining Philosophers model
    const BASE_PHILOSOPHERS = [
        { name: "Alice (Finance)", shortName: "Alice", angle: -90 },
        { name: "Bob (Engineering)", shortName: "Bob", angle: -18 },
        { name: "Charlie (Research)", shortName: "Charlie", angle: 54 },
        { name: "Diana (Legal)", shortName: "Diana", angle: 126 },
        { name: "Guest User", shortName: "Guest", angle: 198 }
    ];

    // -------------------------------------------------------------------------
    // 2. DOM Elements Cache
    // -------------------------------------------------------------------------
    const DOM = {
        // Toasts
        toastContainer: document.getElementById('toast-container'),

        // Header Status
        pollIndicator: document.getElementById('poll-indicator'),
        connText: document.getElementById('conn-text'),
        simStateBadge: document.getElementById('sim-state-badge'),
        mutexStateBadge: document.getElementById('mutex-state-badge'),

        // Stats Counters
        statTotal: document.getElementById('stat-total'),
        statWaiting: document.getElementById('stat-waiting'),
        statPrinting: document.getElementById('stat-printing'),
        statCompleted: document.getElementById('stat-completed'),
        statCancelled: document.getElementById('stat-cancelled'),
        statPages: document.getElementById('stat-pages'),

        // Job Form
        jobForm: document.getElementById('job-form'),
        inputUserName: document.getElementById('user_name'),
        inputDocName: document.getElementById('document_name'),
        inputPages: document.getElementById('pages'),
        submitBtn: document.getElementById('submit-btn'),
        batchDemoBtn: document.getElementById('btn-batch-demo'),
        chipBtns: document.querySelectorAll('.chip-btn'),
        chipDocs: document.querySelectorAll('.chip-doc'),

        // Controls
        btnStart: document.getElementById('btn-start'),
        btnPause: document.getElementById('btn-pause'),
        btnResume: document.getElementById('btn-resume'),
        btnReset: document.getElementById('btn-reset'),
        currentSpeedVal: document.getElementById('current-speed-val'),
        speedBtns: document.querySelectorAll('.btn-speed'),

        // Printer Monitor
        lockBanner: document.getElementById('lock-banner'),
        lockStatusText: document.getElementById('lock-status-text'),
        lockIconSvg: document.getElementById('lock-icon-svg'),
        printerDeviceBox: document.getElementById('printer-device-box'),
        printerLed: document.getElementById('printer-led'),
        lcdLine1: document.getElementById('lcd-line1'),
        lcdLine2: document.getElementById('lcd-line2'),
        noJobMsg: document.getElementById('no-job-msg'),
        activeJobData: document.getElementById('active-job-data'),
        activeJobIdPill: document.getElementById('active-job-id-pill'),
        activeDocTitle: document.getElementById('active-doc-title'),
        activeUserName: document.getElementById('active-user-name'),
        activePageCount: document.getElementById('active-page-count'),
        activeProgressBar: document.getElementById('active-progress-bar'),

        // Dining Philosophers SVG Canvas
        topologySvg: document.getElementById('topology-svg'),
        svgConnectors: document.getElementById('svg-connectors'),
        svgUserNodes: document.getElementById('svg-user-nodes'),
        centerCircle: document.getElementById('center-circle'),

        // Queue Table
        queueCountBadge: document.getElementById('queue-count-badge'),
        jobsTable: document.getElementById('jobs-table'),
        jobsTbody: document.getElementById('jobs-tbody'),
        jobsEmptyRow: document.getElementById('jobs-empty-row'),

        // Activity Logs
        logStreamBox: document.getElementById('log-stream-box'),
        autoscrollCb: document.getElementById('autoscroll-cb'),
        btnClearLogView: document.getElementById('btn-clear-log-view'),
    };

    // -------------------------------------------------------------------------
    // 3. Notification (Toast) System
    // -------------------------------------------------------------------------
    function showToast(title, message, type = 'info', duration = 4000) {
        if (!DOM.toastContainer) return;

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.setAttribute('role', 'alert');

        let iconSvg = '';
        if (type === 'success') {
            iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`;
        } else if (type === 'error') {
            iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>`;
        } else if (type === 'warning') {
            iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`;
        } else {
            iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;
        }

        toast.innerHTML = `
            <div class="toast-icon">${iconSvg}</div>
            <div class="toast-body">
                <div class="toast-title">${escapeHtml(title)}</div>
                <div class="toast-message">${escapeHtml(message)}</div>
            </div>
            <button type="button" class="toast-close" aria-label="Close notification">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
            </button>
        `;

        const closeBtn = toast.querySelector('.toast-close');
        closeBtn.addEventListener('click', () => removeToast(toast));

        DOM.toastContainer.appendChild(toast);

        if (duration > 0) {
            setTimeout(() => {
                removeToast(toast);
            }, duration);
        }
    }

    function removeToast(toast) {
        if (!toast || !toast.parentNode) return;
        toast.classList.add('toast-fadeout');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }

    function escapeHtml(str) {
        if (str === null || str === undefined) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // -------------------------------------------------------------------------
    // 4. API Request Helper
    // -------------------------------------------------------------------------
    async function apiRequest(endpoint, method = 'GET', data = null) {
        const options = {
            method,
            headers: {
                'Accept': 'application/json',
            }
        };

        if (data !== null) {
            options.headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(data);
        }

        const response = await fetch(endpoint, options);
        let result = {};
        try {
            result = await response.json();
        } catch (e) {
            result = { success: false, error: 'Invalid response from server.' };
        }

        if (!response.ok) {
            const errorMsg = result.error || `HTTP error ${response.status}`;
            throw new Error(errorMsg);
        }

        return result;
    }

    // -------------------------------------------------------------------------
    // 5. Form Handling & Job Submission
    // -------------------------------------------------------------------------
    function initFormHandlers() {
        // Quick user fill chips
        DOM.chipBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                DOM.inputUserName.value = btn.dataset.fill || '';
                DOM.inputUserName.focus();
            });
        });

        // Quick document presets
        DOM.chipDocs.forEach(btn => {
            btn.addEventListener('click', () => {
                DOM.inputDocName.value = btn.dataset.doc || '';
                DOM.inputPages.value = btn.dataset.pages || 4;
                DOM.inputDocName.focus();
            });
        });

        // Form Submission with Strict Client-Side Validation
        DOM.jobForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const userName = DOM.inputUserName.value.trim();
            const docName = DOM.inputDocName.value.trim();
            const rawPages = DOM.inputPages.value;

            // Strict Validation
            if (!userName) {
                showToast('Validation Error', 'User Name is required.', 'warning');
                DOM.inputUserName.focus();
                return;
            }
            if (userName.length > 50) {
                showToast('Validation Error', 'User Name cannot exceed 50 characters.', 'warning');
                return;
            }

            if (!docName) {
                showToast('Validation Error', 'Document Name is required.', 'warning');
                DOM.inputDocName.focus();
                return;
            }
            if (docName.length > 100) {
                showToast('Validation Error', 'Document Name cannot exceed 100 characters.', 'warning');
                return;
            }

            const pagesNum = Number(rawPages);
            if (!rawPages || isNaN(pagesNum) || !Number.isInteger(pagesNum) || pagesNum <= 0) {
                showToast('Validation Error', 'Pages must be a positive whole integer greater than zero.', 'warning');
                DOM.inputPages.focus();
                return;
            }

            if (pagesNum > 100) {
                showToast('Validation Error', 'Pages cannot exceed 100 for this simulation.', 'warning');
                DOM.inputPages.focus();
                return;
            }

            // Disable button during submission
            const originalBtnHtml = DOM.submitBtn.innerHTML;
            DOM.submitBtn.disabled = true;
            DOM.submitBtn.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin">
                    <circle cx="12" cy="12" r="10" stroke-dasharray="32" stroke-linecap="round"></circle>
                </svg> Submitting...
            `;

            try {
                const res = await apiRequest('/api/jobs', 'POST', {
                    user_name: userName,
                    document_name: docName,
                    pages: pagesNum
                });

                showToast('Print Job Submitted', res.message || `Job #${res.data.job_id} queued successfully!`, 'success');

                // Clear document name and keep user name for rapid entry
                DOM.inputDocName.value = '';
                DOM.inputPages.value = '4';
                DOM.inputDocName.focus();

                // Trigger immediate poll update
                await pollData();
            } catch (err) {
                showToast('Submission Failed', err.message, 'error');
            } finally {
                DOM.submitBtn.disabled = false;
                DOM.submitBtn.innerHTML = originalBtnHtml;
            }
        });

        // Simulate Multi-User Concurrent Traffic Button
        DOM.batchDemoBtn.addEventListener('click', async () => {
            const originalBtnHtml = DOM.batchDemoBtn.innerHTML;
            DOM.batchDemoBtn.disabled = true;
            DOM.batchDemoBtn.innerHTML = `
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin">
                    <circle cx="12" cy="12" r="10" stroke-dasharray="32" stroke-linecap="round"></circle>
                </svg> Dispatching 4 Concurrent Threads...
            `;

            try {
                const res = await apiRequest('/api/jobs/batch', 'POST', {});
                showToast('Multi-User Simulation', res.message || '4 concurrent jobs submitted across threads.', 'success');
                await pollData();
            } catch (err) {
                showToast('Traffic Demo Failed', err.message, 'error');
            } finally {
                DOM.batchDemoBtn.disabled = false;
                DOM.batchDemoBtn.innerHTML = originalBtnHtml;
            }
        });
    }

    // -------------------------------------------------------------------------
    // 6. Simulation Lifecycle Controls & Speed
    // -------------------------------------------------------------------------
    function initControlHandlers() {
        // Start simulation
        DOM.btnStart.addEventListener('click', async () => {
            try {
                const res = await apiRequest('/api/simulation/start', 'POST');
                showToast('Simulation Control', res.message || 'Simulation worker started.', 'success');
                await pollData();
            } catch (err) {
                showToast('Action Failed', err.message, 'error');
            }
        });

        // Pause simulation
        DOM.btnPause.addEventListener('click', async () => {
            try {
                const res = await apiRequest('/api/simulation/pause', 'POST');
                showToast('Simulation Paused', res.message || 'Worker will pause safely.', 'warning');
                await pollData();
            } catch (err) {
                showToast('Action Failed', err.message, 'error');
            }
        });

        // Resume simulation
        DOM.btnResume.addEventListener('click', async () => {
            try {
                const res = await apiRequest('/api/simulation/resume', 'POST');
                showToast('Simulation Resumed', res.message || 'Print queue processing resumed.', 'success');
                await pollData();
            } catch (err) {
                showToast('Action Failed', err.message, 'error');
            }
        });

        // Reset simulation
        DOM.btnReset.addEventListener('click', async () => {
            const confirmed = window.confirm(
                'Are you sure you want to reset the simulation?\n\n' +
                'This will safely terminate the active worker, clear all jobs from the FIFO queue, ' +
                'and reset all statistics.'
            );
            if (!confirmed) return;

            try {
                const res = await apiRequest('/api/simulation/reset', 'POST');
                showToast('Simulation Reset', res.message || 'Queue cleared and worker reinitialized.', 'success');
                DOM.jobsTbody.innerHTML = '';
                if (DOM.jobsEmptyRow) DOM.jobsTbody.appendChild(DOM.jobsEmptyRow);
                lastRenderedLogId = 0;
                DOM.logStreamBox.innerHTML = '';
                await pollData();
            } catch (err) {
                showToast('Reset Failed', err.message, 'error');
            }
        });

        // Speed buttons
        DOM.speedBtns.forEach(btn => {
            btn.addEventListener('click', async () => {
                const speed = parseFloat(btn.dataset.speed);
                if (isNaN(speed)) return;

                try {
                    await apiRequest('/api/simulation/speed', 'POST', { speed });
                    DOM.speedBtns.forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    currentSpeed = speed;
                    DOM.currentSpeedVal.textContent = `${speed.toFixed(1)}s / page`;
                    showToast('Speed Updated', `Print duration set to ${speed.toFixed(1)}s per page.`, 'info');
                } catch (err) {
                    showToast('Speed Change Failed', err.message, 'error');
                }
            });
        });

        // Clear Log View
        DOM.btnClearLogView.addEventListener('click', () => {
            DOM.logStreamBox.innerHTML = '';
            showToast('Log Cleared', 'Activity stream view cleared from screen.', 'info', 2000);
        });

        // Job cancellation delegation in table
        DOM.jobsTbody.addEventListener('click', async (e) => {
            const target = e.target.closest('.btn-cancel-job');
            if (!target) return;

            const jobId = target.dataset.jobId;
            if (!jobId) return;

            target.disabled = true;
            target.textContent = 'Cancelling...';

            try {
                const res = await apiRequest(`/api/jobs/${jobId}/cancel`, 'POST');
                showToast('Job Cancelled', res.message || `Job #${jobId} cancelled.`, 'warning');
                await pollData();
            } catch (err) {
                showToast('Cancellation Failed', err.message, 'error');
                target.disabled = false;
                target.textContent = 'Cancel';
            }
        });
    }

    // -------------------------------------------------------------------------
    // 7. Polling & Real-Time Data Synchronization
    // -------------------------------------------------------------------------
    async function pollData() {
        try {
            const [statusRes, jobsRes, logsRes] = await Promise.all([
                apiRequest('/api/status'),
                apiRequest('/api/jobs'),
                apiRequest('/api/logs?limit=40')
            ]);

            // Update Connection Indicator
            setConnectionStatus(true);

            const status = statusRes.data;
            const jobs = jobsRes.data;
            const logs = logsRes.data;

            // 1. Update Header Badges & Pill States
            updateHeaderStatus(status);

            // 2. Update Numerical Dashboard Statistics
            updateStatistics(status);

            // 3. Update Hardware Printer & Active Job Card
            updatePrinterDevice(status);

            // 4. Update Print Queue Table
            updateJobsTable(jobs);

            // 5. Update Activity Log Stream
            updateActivityLogs(logs);

            // 6. Update Dynamic Dining Philosophers SVG Model
            updatePhilosophersTopology(status, jobs);

        } catch (err) {
            setConnectionStatus(false);
            console.warn('[PrinterSpooler] Polling error:', err.message);
        }
    }

    function setConnectionStatus(online) {
        const pulseDot = DOM.pollIndicator ? DOM.pollIndicator.querySelector('.pulse-dot') : null;
        if (online) {
            if (pulseDot) {
                pulseDot.classList.remove('error');
                pulseDot.classList.add('active');
            }
            if (DOM.connText) DOM.connText.textContent = 'Live Polling (1.0s)';
        } else {
            if (pulseDot) {
                pulseDot.classList.remove('active');
                pulseDot.classList.add('error');
            }
            if (DOM.connText) DOM.connText.textContent = 'Reconnecting...';
        }
    }

    // -------------------------------------------------------------------------
    // 8. View Renderers
    // -------------------------------------------------------------------------
    function updateHeaderStatus(status) {
        if (!status) return;

        // Simulation state badge
        if (DOM.simStateBadge) {
            const state = status.simulation_state || 'UNKNOWN';
            DOM.simStateBadge.textContent = state;
            DOM.simStateBadge.className = 'pill-value';
            if (state === 'RUNNING') DOM.simStateBadge.classList.add('badge-running');
            else if (state === 'PAUSED') DOM.simStateBadge.classList.add('badge-paused');
            else DOM.simStateBadge.classList.add('badge-stopped');
        }

        // Printer Mutex pill
        if (DOM.mutexStateBadge) {
            const isLocked = !!status.printer_locked;
            if (isLocked) {
                DOM.mutexStateBadge.textContent = `LOCKED (Job #${status.active_job ? status.active_job.job_id : '?'})`;
                DOM.mutexStateBadge.className = 'pill-value badge-printing';
            } else {
                DOM.mutexStateBadge.textContent = 'UNLOCKED';
                DOM.mutexStateBadge.className = 'pill-value badge-idle';
            }
        }
    }

    function updateStatistics(status) {
        if (!status || !status.counts) return;

        const counts = status.counts;
        if (DOM.statTotal) DOM.statTotal.textContent = counts.total || 0;
        if (DOM.statWaiting) DOM.statWaiting.textContent = counts.waiting || 0;
        if (DOM.statPrinting) DOM.statPrinting.textContent = counts.printing || 0;
        if (DOM.statCompleted) DOM.statCompleted.textContent = counts.completed || 0;
        if (DOM.statCancelled) DOM.statCancelled.textContent = (counts.cancelled || 0) + (counts.failed || 0);
        if (DOM.statPages) DOM.statPages.textContent = status.total_pages_printed || 0;

        // Sync speed display if changed externally
        if (status.page_duration && Math.abs(currentSpeed - status.page_duration) > 0.01) {
            currentSpeed = status.page_duration;
            if (DOM.currentSpeedVal) {
                DOM.currentSpeedVal.textContent = `${currentSpeed.toFixed(1)}s / page`;
            }
            DOM.speedBtns.forEach(b => {
                b.classList.toggle('active', Math.abs(parseFloat(b.dataset.speed) - currentSpeed) < 0.05);
            });
        }
    }

    function updatePrinterDevice(status) {
        if (!status) return;

        const activeJob = status.active_job;
        const isPrinting = status.printer_state === 'PRINTING' && !!activeJob;
        const isPaused = status.simulation_state === 'PAUSED';

        // 1. Lock indicator banner
        if (DOM.lockBanner) {
            if (isPrinting) {
                DOM.lockBanner.classList.add('locked');
                DOM.lockStatusText.textContent = `MUTEX LOCKED: Job #${activeJob.job_id} in Critical Section`;
                DOM.lockIconSvg.innerHTML = `
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                        <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                    </svg>
                `;
            } else {
                DOM.lockBanner.classList.remove('locked');
                DOM.lockStatusText.textContent = 'MUTEX UNLOCKED (Printer Idle)';
                DOM.lockIconSvg.innerHTML = `
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                        <path d="M7 11V7a5 5 0 0 1 9.9-1"></path>
                    </svg>
                `;
            }
        }

        // 2. Hardware printer animations & LCD
        if (DOM.printerDeviceBox) {
            DOM.printerDeviceBox.classList.toggle('printing', isPrinting);
        }

        if (DOM.printerLed) {
            DOM.printerLed.classList.remove('led-printing', 'led-paused');
            if (isPrinting) {
                DOM.printerLed.classList.add('led-printing');
            } else if (isPaused) {
                DOM.printerLed.classList.add('led-paused');
            }
        }

        if (DOM.lcdLine1 && DOM.lcdLine2) {
            if (isPrinting) {
                DOM.lcdLine1.textContent = `PRINTING JOB #${activeJob.job_id}`;
                DOM.lcdLine2.textContent = `PAGE ${activeJob.progress_pages}/${activeJob.pages} (${activeJob.progress_pct}%)`;
            } else if (isPaused) {
                DOM.lcdLine1.textContent = 'SIMULATION PAUSED';
                DOM.lcdLine2.textContent = `QUEUE: ${status.queue_length || 0} WAITING`;
            } else {
                DOM.lcdLine1.textContent = 'PRINTER READY';
                DOM.lcdLine2.textContent = status.queue_length > 0 ? `QUEUE: ${status.queue_length} JOBS` : 'MUTEX RELEASED';
            }
        }

        // 3. Active job info container
        if (isPrinting) {
            DOM.noJobMsg.classList.add('hidden');
            DOM.activeJobData.classList.remove('hidden');

            if (DOM.activeJobIdPill) DOM.activeJobIdPill.textContent = `Job #${activeJob.job_id}`;
            if (DOM.activeDocTitle) DOM.activeDocTitle.textContent = activeJob.document_name;
            if (DOM.activeUserName) DOM.activeUserName.textContent = activeJob.user_name;
            if (DOM.activePageCount) {
                DOM.activePageCount.textContent = `${activeJob.progress_pages} / ${activeJob.pages} pages (${activeJob.progress_pct}%)`;
            }
            if (DOM.activeProgressBar) {
                DOM.activeProgressBar.style.width = `${activeJob.progress_pct}%`;
            }
        } else {
            DOM.noJobMsg.classList.remove('hidden');
            DOM.activeJobData.classList.add('hidden');
        }
    }

    function updateJobsTable(jobs) {
        if (!DOM.jobsTbody) return;

        if (!jobs || jobs.length === 0) {
            DOM.jobsTbody.innerHTML = `
                <tr class="empty-row" id="jobs-empty-row">
                    <td colspan="8">
                        <div class="empty-state">
                            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                <polyline points="14 2 14 8 20 8"></polyline>
                            </svg>
                            <p>No print jobs submitted yet</p>
                            <span>Use the form above or click "Simulate Multi-User Traffic"</span>
                        </div>
                    </td>
                </tr>
            `;
            if (DOM.queueCountBadge) DOM.queueCountBadge.textContent = '0 Jobs in Queue';
            return;
        }

        // Count waiting
        const waitingCount = jobs.filter(j => j.status === 'WAITING').length;
        if (DOM.queueCountBadge) {
            DOM.queueCountBadge.textContent = `${waitingCount} Waiting / ${jobs.length} Total`;
        }

        // Render rows
        const rowsHtml = jobs.map(job => {
            let statusBadge = '';
            let actionBtn = '<span style="color: #94a3b8;">—</span>';

            switch (job.status) {
                case 'WAITING':
                    statusBadge = `<span class="badge badge-waiting">WAITING</span>`;
                    actionBtn = `<button type="button" class="btn-cancel-job" data-job-id="${job.job_id}" title="Remove job from queue">Cancel</button>`;
                    break;
                case 'PRINTING':
                    statusBadge = `<span class="badge badge-printing pulse">PRINTING</span>`;
                    break;
                case 'COMPLETED':
                    statusBadge = `<span class="badge badge-completed">COMPLETED</span>`;
                    break;
                case 'CANCELLED':
                    statusBadge = `<span class="badge badge-cancelled">CANCELLED</span>`;
                    break;
                case 'FAILED':
                    statusBadge = `<span class="badge badge-failed">FAILED</span>`;
                    break;
                default:
                    statusBadge = `<span class="badge">${escapeHtml(job.status)}</span>`;
            }

            return `
                <tr data-job-id="${job.job_id}">
                    <td class="job-id-cell">#${job.job_id}</td>
                    <td><strong>${escapeHtml(job.user_name)}</strong></td>
                    <td class="doc-name-cell">${escapeHtml(job.document_name)}</td>
                    <td>${job.pages} p.</td>
                    <td style="font-size: 0.78rem; color: #64748b;">${escapeHtml(job.submitted_at || '—')}</td>
                    <td>${statusBadge}</td>
                    <td>
                        <div style="font-size: 0.75rem; font-weight: 500;">${job.progress_pages} / ${job.pages} (${job.progress_pct}%)</div>
                        <div class="mini-progress-track">
                            <div class="mini-progress-fill" style="width: ${job.progress_pct}%;"></div>
                        </div>
                    </td>
                    <td style="text-align: center;">${actionBtn}</td>
                </tr>
            `;
        }).join('');

        DOM.jobsTbody.innerHTML = rowsHtml;
    }

    function updateActivityLogs(logs) {
        if (!DOM.logStreamBox || !logs) return;

        // Logs are returned newest first from backend API
        // Reverse to display chronologically (oldest to newest)
        const chronologicalLogs = [...logs].reverse();

        // Check if logs changed
        if (chronologicalLogs.length === 0) {
            DOM.logStreamBox.innerHTML = `<div style="color: #64748b; padding: 0.5rem;">No activity recorded yet.</div>`;
            return;
        }

        const latestEntry = chronologicalLogs[chronologicalLogs.length - 1];
        if (latestEntry.id === lastRenderedLogId && DOM.logStreamBox.children.length === chronologicalLogs.length) {
            return; // No new logs
        }
        lastRenderedLogId = latestEntry.id;

        const entriesHtml = chronologicalLogs.map(entry => {
            const levelClass = `log-badge-${entry.level || 'INFO'}`;
            return `
                <div class="log-entry">
                    <span class="log-time">[${escapeHtml(entry.timestamp)}]</span>
                    <span class="log-badge ${levelClass}">${escapeHtml(entry.level || 'INFO')}</span>
                    <span class="log-event">${escapeHtml(entry.event_type)}:</span>
                    <span class="log-msg">${escapeHtml(entry.message)}</span>
                </div>
            `;
        }).join('');

        DOM.logStreamBox.innerHTML = entriesHtml;

        // Auto-scroll to bottom if enabled
        if (DOM.autoscrollCb && DOM.autoscrollCb.checked) {
            DOM.logStreamBox.scrollTop = DOM.logStreamBox.scrollHeight;
        }
    }

    // -------------------------------------------------------------------------
    // 9. Dining Philosophers Analogy Visualization (SVG Rendering)
    // -------------------------------------------------------------------------
    function updatePhilosophersTopology(status, jobs) {
        if (!DOM.svgConnectors || !DOM.svgUserNodes) return;

        const centerX = 250;
        const centerY = 160;
        const radius = 110;

        // 1. Identify distinct users from jobs and defaults
        const activeJob = status ? status.active_job : null;
        const printingUserName = activeJob ? activeJob.user_name : null;

        // Map users waiting in queue
        const waitingUsersMap = {};
        if (jobs) {
            jobs.filter(j => j.status === 'WAITING').forEach((j, idx) => {
                if (!waitingUsersMap[j.user_name]) {
                    waitingUsersMap[j.user_name] = idx + 1; // 1-indexed queue position
                }
            });
        }

        // Map users with completed jobs
        const completedUsersSet = new Set();
        if (jobs) {
            jobs.filter(j => j.status === 'COMPLETED').forEach(j => {
                completedUsersSet.add(j.user_name);
            });
        }

        // Build list of 5 philosophers to render
        const philosophers = BASE_PHILOSOPHERS.map((base, idx) => {
            const rad = (base.angle * Math.PI) / 180;
            const x = centerX + radius * Math.cos(rad);
            const y = centerY + radius * Math.sin(rad);

            let state = 'IDLE'; // IDLE (Thinking), WAITING (Hungry), PRINTING (Eating), COMPLETED (Finished)
            let queuePos = null;

            if (printingUserName && printingUserName.includes(base.shortName)) {
                state = 'PRINTING';
            } else {
                for (const uName of Object.keys(waitingUsersMap)) {
                    if (uName.includes(base.shortName)) {
                        state = 'WAITING';
                        queuePos = waitingUsersMap[uName];
                        break;
                    }
                }
                if (state === 'IDLE') {
                    for (const uName of completedUsersSet) {
                        if (uName.includes(base.shortName)) {
                            state = 'COMPLETED';
                            break;
                        }
                    }
                }
            }

            return {
                id: idx,
                name: base.name,
                shortName: base.shortName,
                x,
                y,
                state,
                queuePos
            };
        });

        // 2. Render Connector Lines
        let connectorsHtml = '';
        philosophers.forEach(p => {
            if (p.state === 'PRINTING') {
                // Mutex Held / Eating: Bold glowing teal line
                connectorsHtml += `
                    <line x1="${p.x}" y1="${p.y}" x2="${centerX}" y2="${centerY}"
                          stroke="#0d9488" stroke-width="3.5" stroke-linecap="round">
                        <animate attributeName="stroke-opacity" values="1;0.4;1" dur="1s" repeatCount="indefinite" />
                    </line>
                `;
            } else if (p.state === 'WAITING') {
                // Hungry / Queued: Animated dashed amber line pointing to center
                connectorsHtml += `
                    <line x1="${p.x}" y1="${p.y}" x2="${centerX}" y2="${centerY}"
                          stroke="#f59e0b" stroke-width="2" stroke-dasharray="6,4">
                        <animate attributeName="stroke-dashoffset" values="20;0" dur="0.8s" repeatCount="indefinite" />
                    </line>
                `;
            } else {
                // Idle / Thinking: Thin dashed grey line
                connectorsHtml += `
                    <line x1="${p.x}" y1="${p.y}" x2="${centerX}" y2="${centerY}"
                          stroke="#cbd5e1" stroke-width="1.2" stroke-dasharray="3,3" stroke-opacity="0.7" />
                `;
            }
        });
        DOM.svgConnectors.innerHTML = connectorsHtml;

        // 3. Render Center Printer Node
        if (DOM.centerCircle) {
            if (printingUserName) {
                DOM.centerCircle.setAttribute('fill', '#0d9488');
                DOM.centerCircle.setAttribute('stroke', '#2dd4bf');
            } else {
                DOM.centerCircle.setAttribute('fill', '#0284c7');
                DOM.centerCircle.setAttribute('stroke', '#38bdf8');
            }
        }

        // 4. Render Surrounding Philosopher Nodes
        let nodesHtml = '';
        philosophers.forEach(p => {
            let fillColor = '#94a3b8';
            let strokeColor = '#64748b';
            let statusText = 'Thinking';
            let statusSubText = 'Idle';

            if (p.state === 'PRINTING') {
                fillColor = '#0d9488';
                strokeColor = '#2dd4bf';
                statusText = 'EATING';
                statusSubText = 'Mutex Held';
            } else if (p.state === 'WAITING') {
                fillColor = '#f59e0b';
                strokeColor = '#fbbf24';
                statusText = 'HUNGRY';
                statusSubText = p.queuePos ? `Queued #${p.queuePos}` : 'In Queue';
            } else if (p.state === 'COMPLETED') {
                fillColor = '#10b981';
                strokeColor = '#34d399';
                statusText = 'Finished';
                statusSubText = 'Done';
            }

            // Offset labels based on position to avoid overlapping center
            const isTop = p.y < centerY;
            const textY = isTop ? p.y - 28 : p.y + 32;

            nodesHtml += `
                <g class="philosopher-node" transform="translate(0, 0)">
                    ${p.state === 'PRINTING' ? `
                        <circle cx="${p.x}" cy="${p.y}" r="26" fill="none" stroke="#2dd4bf" stroke-width="2" opacity="0.6">
                            <animate attributeName="r" values="22;30;22" dur="1.5s" repeatCount="indefinite" />
                            <animate attributeName="opacity" values="0.8;0;0.8" dur="1.5s" repeatCount="indefinite" />
                        </circle>
                    ` : ''}
                    <circle cx="${p.x}" cy="${p.y}" r="20" fill="${fillColor}" stroke="${strokeColor}" stroke-width="2.5" />
                    <!-- User Icon Silhouette -->
                    <circle cx="${p.x}" cy="${p.y - 5}" r="5" fill="#ffffff" />
                    <path d="M ${p.x - 9} ${p.y + 11} C ${p.x - 9} ${p.y + 4}, ${p.x + 9} ${p.y + 4}, ${p.x + 9} ${p.y + 11} Z" fill="#ffffff" />
                    <!-- Text Labels -->
                    <text x="${p.x}" y="${textY}" text-anchor="middle" font-size="10.5" font-weight="600" fill="#0f172a" font-family="Inter, sans-serif">
                        ${escapeHtml(p.shortName)}
                    </text>
                    <text x="${p.x}" y="${textY + (isTop ? -11 : 12)}" text-anchor="middle" font-size="8.5" font-weight="500" fill="${strokeColor}" font-family="Inter, sans-serif">
                        ${statusText} (${statusSubText})
                    </text>
                </g>
            `;
        });
        DOM.svgUserNodes.innerHTML = nodesHtml;
    }

    // -------------------------------------------------------------------------
    // 10. Initialization
    // -------------------------------------------------------------------------
    function init() {
        initFormHandlers();
        initControlHandlers();

        // Initial fetch
        pollData();

        // Start real-time polling loop
        pollTimer = setInterval(() => {
            if (isPollingActive) {
                pollData();
            }
        }, POLLING_INTERVAL_MS);

        // Visibility handling to pause polling if tab is inactive
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                isPollingActive = false;
            } else {
                isPollingActive = true;
                pollData();
            }
        });
    }

    // Run when DOM is fully loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
