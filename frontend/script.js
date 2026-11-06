// Model-Setu Dashboard
// Connects the frontend to the Flask backend running on port 5001.

const API_BASE_URL = "http://127.0.0.1:5001";

const elements = {
    total: document.getElementById("total-deployments"),
    successful: document.getElementById("successful-deployments"),
    failed: document.getElementById("failed-deployments"),
    activeVersion: document.getElementById("active-version"),
    activeContent: document.getElementById("active-deployment-content"),
    table: document.getElementById("deployment-table"),
    backendStatus: document.getElementById("backend-status"),
    sidebarStatus: document.getElementById("sidebar-status"),
    sidebarDot: document.getElementById("sidebar-status-dot"),
    lastUpdated: document.getElementById("last-updated"),
    requests: document.getElementById("http-requests"),
    latency: document.getElementById("average-latency"),
    metricsStatus: document.getElementById("metrics-status"),
    notification: document.getElementById("notification")
};

let notificationTimeout;

async function apiRequest(endpoint, options = {}) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers: {
            ...(options.body ? { "Content-Type": "application/json" } : {}),
            ...options.headers
        }
    });

    const contentType = response.headers.get("content-type") || "";
    let data = {};

    if (contentType.includes("application/json")) {
        data = await response.json();
    } else {
        data = await response.text();
    }

    if (!response.ok) {
        const message =
            typeof data === "object" && data !== null
                ? data.error || data.message || `Request failed (${response.status})`
                : `Request failed (${response.status})`;

        throw new Error(message);
    }

    return data;
}

function showNotification(message, type = "success") {
    elements.notification.textContent = message;
    elements.notification.className = `notification ${type}`;

    clearTimeout(notificationTimeout);

    notificationTimeout = setTimeout(() => {
        elements.notification.className = "notification hidden";
    }, 5000);
}

function setBackendStatus(isOnline) {
    elements.backendStatus.textContent = isOnline ? "Online" : "Offline";
    elements.backendStatus.className =
        `status-text ${isOnline ? "online" : "offline"}`;

    elements.sidebarStatus.textContent = isOnline ? "Connected" : "Disconnected";
    elements.sidebarDot.className =
        `status-dot ${isOnline ? "online" : "offline"}`;
}

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => {
        const replacements = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#039;"
        };

        return replacements[character];
    });
}

function formatDate(value) {
    if (!value) return "Not available";

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return escapeHTML(value);
    }

    return date.toLocaleString();
}

function getStatusClass(status) {
    const normalized = String(status || "").toLowerCase();

    if (normalized === "success") return "status-success";
    if (normalized === "failed") return "status-failed";
    if (normalized === "pending") return "status-pending";

    return "status-unknown";
}

function getDeploymentArray(data) {
    if (Array.isArray(data)) return data;
    if (Array.isArray(data?.deployments)) return data.deployments;
    return [];
}

function renderStatistics(deployments) {
    const successful = deployments.filter(
        item => String(item.status).toLowerCase() === "success"
    ).length;

    const failed = deployments.filter(
        item => String(item.status).toLowerCase() === "failed"
    ).length;

    elements.total.textContent = deployments.length;
    elements.successful.textContent = successful;
    elements.failed.textContent = failed;
}

function renderActiveDeployment(deployment) {
    if (!deployment) {
        elements.activeVersion.textContent = "None";

        elements.activeContent.innerHTML = `
            <div class="empty-state">
                No active deployment found.<br>
                Create a successful deployment record first.
            </div>
        `;

        return;
    }

    const version = escapeHTML(deployment.version || "Unknown");
    const status = escapeHTML(deployment.status || "Unknown");
    const id = escapeHTML(deployment.id);
    const deployedAt = formatDate(deployment.deployed_at);

    elements.activeVersion.textContent = version;

    elements.activeContent.innerHTML = `
        <div class="active-version">
            <div>
                <h3>${version}</h3>
                <p>Deployment ID: #${id}</p>
            </div>
            <span class="status-pill ${getStatusClass(status)}">
                ${status}
            </span>
        </div>

        <div class="detail-grid">
            <div class="detail-item">
                <span>Deployment ID</span>
                <strong>#${id}</strong>
            </div>
            <div class="detail-item">
                <span>Version</span>
                <strong>${version}</strong>
            </div>
            <div class="detail-item">
                <span>Status</span>
                <strong>${status}</strong>
            </div>
            <div class="detail-item">
                <span>Deployed At</span>
                <strong>${deployedAt}</strong>
            </div>
        </div>
    `;
}

function renderDeploymentHistory(deployments, activeDeployment) {
    if (deployments.length === 0) {
        elements.table.innerHTML = `
            <tr>
                <td colspan="6" class="empty-state">
                    No deployment records found.
                </td>
            </tr>
        `;
        return;
    }

    const activeId = activeDeployment
        ? String(activeDeployment.id)
        : null;

    elements.table.innerHTML = deployments.map(deployment => {
        const id = escapeHTML(deployment.id);
        const version = escapeHTML(deployment.version || "Unknown");
        const status = escapeHTML(deployment.status || "Unknown");
        const date = formatDate(deployment.deployed_at);

        const isActive =
            deployment.is_active === true ||
            String(deployment.is_active) === "1" ||
            (activeId !== null && String(deployment.id) === activeId);

        const canRollback =
            String(deployment.status).toLowerCase() === "success" &&
            !isActive;

        return `
            <tr>
                <td>#${id}</td>
                <td><strong>${version}</strong></td>
                <td>
                    <span class="status-pill ${getStatusClass(status)}">
                        ${status}
                    </span>
                </td>
                <td>${date}</td>
                <td>
                    ${
                        isActive
                            ? '<span class="active-label">● Active</span>'
                            : '<span class="muted-label">—</span>'
                    }
                </td>
                <td>
                    <button
                        class="rollback-button"
                        data-id="${id}"
                        ${canRollback ? "" : "disabled"}
                        title="${canRollback ? "Roll back to this successful record" : "Rollback unavailable"}"
                    >
                        Rollback
                    </button>
                </td>
            </tr>
        `;
    }).join("");

    elements.table.querySelectorAll(".rollback-button:not(:disabled)")
        .forEach(button => {
            button.addEventListener("click", () => {
                rollbackDeployment(button.dataset.id);
            });
        });
}

async function loadBackendHealth() {
    try {
        await apiRequest("/health");
        setBackendStatus(true);
        return true;
    } catch (error) {
        setBackendStatus(false);
        return false;
    }
}

async function loadDeployments() {
    const data = await apiRequest("/deployments");
    const deployments = getDeploymentArray(data);

    let activeDeployment = null;

    try {
        const activeData = await apiRequest("/active-deployment");
        activeDeployment = activeData.active_deployment || null;
    } catch (error) {
        // A 404 here means no active deployment has been recorded.
        activeDeployment = null;
    }

    renderStatistics(deployments);
    renderActiveDeployment(activeDeployment);
    renderDeploymentHistory(deployments, activeDeployment);
}

function parsePrometheusMetric(metricsText, metricName) {
    const escapedName = metricName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const pattern = new RegExp(
        `^${escapedName}(?:\\{[^}]*\\})?\\s+([0-9.eE+-]+)\\s*$`,
        "gm"
    );

    const matches = [...metricsText.matchAll(pattern)];

    return matches.reduce((total, match) => {
        const value = Number(match[1]);
        return Number.isFinite(value) ? total + value : total;
    }, 0);
}

async function loadMetrics() {
    try {
        const metricsText = await apiRequest("/metrics");

        if (typeof metricsText !== "string") {
            throw new Error("Unexpected metrics response format");
        }

        const requestCount = parsePrometheusMetric(
            metricsText,
            "model_setu_http_requests_total"
        );

        const durationSum = parsePrometheusMetric(
            metricsText,
            "model_setu_http_request_duration_seconds_sum"
        );

        const durationCount = parsePrometheusMetric(
            metricsText,
            "model_setu_http_request_duration_seconds_count"
        );

        const hasRequestMetric =
            /^model_setu_http_requests_total(?:\{[^}]*\})?\s+/m.test(metricsText);

        const hasDurationMetric =
            /^model_setu_http_request_duration_seconds_(?:sum|count)(?:\{[^}]*\})?\s+/m.test(metricsText);

        elements.requests.textContent = hasRequestMetric
            ? Math.round(requestCount).toLocaleString()
            : "No data";

        elements.latency.textContent =
            durationCount > 0 && hasDurationMetric
                ? `${((durationSum / durationCount) * 1000).toFixed(2)} ms`
                : "No data";

        elements.metricsStatus.textContent = "Available";
    } catch (error) {
        elements.requests.textContent = "Unavailable";
        elements.latency.textContent = "Unavailable";
        elements.metricsStatus.textContent = "Offline";
    }
}

async function rollbackDeployment(deploymentId) {
    const confirmed = window.confirm(
        `Are you sure you want to make deployment #${deploymentId} active?`
    );

    if (!confirmed) return;

    try {
        await apiRequest(`/rollback/${encodeURIComponent(deploymentId)}`, {
            method: "POST"
        });

        showNotification(
            `Rollback successful. Deployment #${deploymentId} is now active.`,
            "success"
        );

        await refreshDashboard();
    } catch (error) {
        showNotification(`Rollback failed: ${error.message}`, "error");
    }
}

async function refreshDashboard() {
    const isOnline = await loadBackendHealth();

    if (!isOnline) {
        elements.total.textContent = "—";
        elements.successful.textContent = "—";
        elements.failed.textContent = "—";
        elements.activeVersion.textContent = "—";

        elements.activeContent.innerHTML = `
            <div class="empty-state">
                Backend is not reachable.<br>
                Start the Flask server on port 5001.
            </div>
        `;

        elements.table.innerHTML = `
            <tr>
                <td colspan="6" class="empty-state">
                    Unable to load deployments. Backend is offline.
                </td>
            </tr>
        `;

        elements.requests.textContent = "—";
        elements.latency.textContent = "—";
        elements.metricsStatus.textContent = "Offline";

        elements.lastUpdated.textContent = "Backend connection failed.";
        return;
    }

    try {
        await loadDeployments();
    } catch (error) {
        showNotification(`Could not load deployments: ${error.message}`, "error");
    }

    await loadMetrics();

    elements.lastUpdated.textContent =
        `Last checked: ${new Date().toLocaleTimeString()}`;
}

document.getElementById("refresh-btn")
    .addEventListener("click", refreshDashboard);

document.getElementById("history-refresh-btn")
    .addEventListener("click", refreshDashboard);

// Initial dashboard load.
refreshDashboard();