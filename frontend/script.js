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
    const commitSha = deployment.commit_sha
        ? escapeHTML(deployment.commit_sha)
        : "—";
    const deployedAt = formatDate(deployment.deployed_at);
    const startedAt = formatDate(deployment.started_at);
    const completedAt = formatDate(deployment.completed_at);

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
                <span>Commit SHA</span>
                <strong>${commitSha}</strong>
            </div>
            <div class="detail-item">
                <span>Deployed At</span>
                <strong>${deployedAt}</strong>
            </div>
            <div class="detail-item">
                <span>Started At</span>
                <strong>${startedAt}</strong>
            </div>
            <div class="detail-item">
                <span>Completed At</span>
                <strong>${completedAt}</strong>
            </div>
        </div>
    `;
}

function renderDeploymentHistory(deployments, activeDeployment) {
    if (deployments.length === 0) {
        elements.table.innerHTML = `
            <tr>
                <td colspan="9" class="empty-state">
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
        const commitSha = deployment.commit_sha
            ? escapeHTML(deployment.commit_sha)
            : "—";
        const deployedAt = formatDate(deployment.deployed_at);
        const startedAt = formatDate(deployment.started_at);
        const completedAt = formatDate(deployment.completed_at);

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
                <td>${commitSha}</td>
                <td>${deployedAt}</td>
                <td>${startedAt}</td>
                <td>${completedAt}</td>
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
                        title="${canRollback ? "Restore this record in local deployment history only; Render will not be rolled back" : "Rollback unavailable"}"
                    >
                        Rollback (DB)
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


// ---------------------------------------------------------
// GitHub Actions integration
// ---------------------------------------------------------

const githubElements = {
    connection: document.getElementById("github-connection-status"),
    user: document.getElementById("github-user-name"),
    repository: document.getElementById("github-repository"),
    branch: document.getElementById("github-branch"),
    trigger: document.getElementById("github-trigger-btn"),
    runs: document.getElementById("github-runs-table"),
    refresh: document.getElementById("github-refresh-btn"),
    refreshRuns: document.getElementById("github-runs-refresh-btn")
};

let githubRepositories = [];

function setGitHubConnection(connected, label) {
    githubElements.connection.textContent = label;
    githubElements.connection.className =
        `status-pill ${connected ? "status-success" : "status-failed"}`;
}

function selectedGitHubRepository() {
    return githubRepositories.find(
        repo => repo.full_name === githubElements.repository.value
    );
}

function setGitHubRunMessage(message) {
    githubElements.runs.innerHTML = `
        <tr><td colspan="7" class="empty-state">${escapeHTML(message)}</td></tr>
    `;
}

async function loadGitHubUser() {
    try {
        const data = await apiRequest("/github/user");

        if (!data.connected || !data.user) {
            throw new Error("GitHub account is not connected");
        }

        githubElements.user.textContent =
            data.user.name || data.user.login || "Connected";
        setGitHubConnection(true, "Connected");
        return true;
    } catch (error) {
        githubElements.user.textContent = "GitHub connection unavailable";
        setGitHubConnection(false, "Disconnected");
        githubElements.trigger.disabled = true;
        setGitHubRunMessage(error.message);
        return false;
    }
}

async function loadGitHubRepositories() {
    try {
        const data = await apiRequest("/github/repositories");
        githubRepositories = Array.isArray(data.repositories)
            ? data.repositories
            : [];

        githubElements.repository.innerHTML = "";

        if (!githubRepositories.length) {
            githubElements.repository.innerHTML =
                '<option value="">No repositories found</option>';
            githubElements.branch.innerHTML =
                '<option value="">No branches available</option>';
            githubElements.trigger.disabled = true;
            return;
        }

        githubRepositories.forEach(repo => {
            const option = document.createElement("option");
            option.value = repo.full_name;
            option.textContent = repo.full_name;
            githubElements.repository.appendChild(option);
        });

        const preferred = githubRepositories.find(
            repo => repo.full_name === "Paridhi21shukla/Model-Setu"
        );

        if (preferred) {
            githubElements.repository.value = preferred.full_name;
        }

        await loadGitHubBranches();
    } catch (error) {
        githubElements.repository.innerHTML =
            '<option value="">Unable to load repositories</option>';
        githubElements.trigger.disabled = true;
        showNotification(`GitHub repositories: ${error.message}`, "error");
    }
}

async function loadGitHubBranches() {
    const repo = selectedGitHubRepository();

    githubElements.trigger.disabled = true;
    githubElements.branch.innerHTML =
        '<option value="">Loading branches...</option>';

    if (!repo) return;

    try {
        const [owner, repoName] = repo.full_name.split("/");
        const data = await apiRequest(
            `/github/repositories/${encodeURIComponent(owner)}/${encodeURIComponent(repoName)}/branches`
        );

        const branches = Array.isArray(data.branches) ? data.branches : [];
        githubElements.branch.innerHTML = "";

        if (!branches.length) {
            githubElements.branch.innerHTML =
                '<option value="">No branches found</option>';
            return;
        }

        branches.forEach(branch => {
            const option = document.createElement("option");
            option.value = branch.name;
            option.textContent = branch.name;
            githubElements.branch.appendChild(option);
        });

        githubElements.branch.value = repo.default_branch || branches[0].name;
        githubElements.trigger.disabled = false;
        await loadGitHubWorkflowRuns();
    } catch (error) {
        githubElements.branch.innerHTML =
            '<option value="">Unable to load branches</option>';
        showNotification(`GitHub branches: ${error.message}`, "error");
    }
}

async function loadGitHubWorkflowRuns() {
    const repo = selectedGitHubRepository();
    if (!repo) return;

    const [owner, repoName] = repo.full_name.split("/");
    const branch = githubElements.branch.value;

    setGitHubRunMessage("Loading workflow runs...");

    try {
        const params = new URLSearchParams({ owner, repo: repoName });
        if (branch) params.set("branch", branch);

        const data = await apiRequest(
            `/github/workflows/runs?${params.toString()}`
        );

        const runs = Array.isArray(data.runs) ? data.runs : [];

        if (!runs.length) {
            setGitHubRunMessage("No workflow runs found for this selection.");
            return;
        }

        githubElements.runs.innerHTML = runs.map(run => {
            const status = escapeHTML(run.status || "unknown");
            const conclusion = escapeHTML(run.conclusion || "—");
            const url = typeof run.url === "string" &&
                /^https:\/\/github\.com\//.test(run.url)
                ? run.url
                : "";

            return `
                <tr>
                    <td><strong>${escapeHTML(run.name || "Workflow")}</strong></td>
                    <td>${escapeHTML(run.branch || "—")}</td>
                    <td>${escapeHTML(run.event || "—")}</td>
                    <td><span class="status-pill ${getStatusClass(status)}">${status}</span></td>
                    <td>${escapeHTML(conclusion)}</td>
                    <td>${formatDate(run.created_at)}</td>
                    <td>${url
                        ? `<a class="github-run-link" href="${escapeHTML(url)}" target="_blank" rel="noopener noreferrer">View run ↗</a>`
                        : "—"
                    }</td>
                </tr>
            `;
        }).join("");
    } catch (error) {
        setGitHubRunMessage(`Unable to load workflow runs: ${error.message}`);
    }
}

async function triggerGitHubWorkflow() {
    const repo = selectedGitHubRepository();
    const branch = githubElements.branch.value;

    if (!repo || !branch) {
        showNotification("Select a repository and branch first.", "error");
        return;
    }

    const confirmed = window.confirm(
        `Trigger the GitHub Actions CI workflow for ${repo.full_name} (${branch})?`
    );

    if (!confirmed) return;

    githubElements.trigger.disabled = true;
    githubElements.trigger.textContent = "Triggering...";

    try {
        const [owner, repoName] = repo.full_name.split("/");

        const result = await apiRequest("/github/workflows/dispatch", {
            method: "POST",
            body: JSON.stringify({ owner, repo: repoName, branch })
        });

        if (result.triggered !== true) {
            throw new Error("GitHub did not confirm workflow dispatch.");
        }

        showNotification(
            "GitHub accepted the workflow trigger. Refresh runs to check its result.",
            "success"
        );

        await loadGitHubWorkflowRuns();
    } catch (error) {
        showNotification(`Workflow trigger failed: ${error.message}`, "error");
    } finally {
        githubElements.trigger.disabled = false;
        githubElements.trigger.textContent = "▶ Trigger CI Workflow";
    }
}

async function loadGitHubIntegration() {
    const connected = await loadGitHubUser();
    if (!connected) return;

    await loadGitHubRepositories();
}

if (githubElements.repository) {
    githubElements.repository.addEventListener("change", loadGitHubBranches);
    githubElements.branch.addEventListener("change", loadGitHubWorkflowRuns);
    githubElements.trigger.addEventListener("click", triggerGitHubWorkflow);
    githubElements.refresh.addEventListener("click", loadGitHubIntegration);
    githubElements.refreshRuns.addEventListener("click", loadGitHubWorkflowRuns);

    loadGitHubIntegration();
}
