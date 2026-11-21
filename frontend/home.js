/* Model-Setu homepage interactions: links open the project's real services, not vendor documentation. */
const PROJECT = 'https://github.com/Paridhi21shukla/Model-Setu';
const BACKEND = 'https://model-setu-backend.onrender.com';

const techInfo = {
  github: {
    icon: '●', title: 'GitHub Repository',
    text: 'This is the source-code repository for Model-Setu. A push to the main branch starts the configured GitHub Actions workflow.',
    flow: ['Source code', 'Commit and push', 'CI workflow starts'],
    actions: [{ label: 'Open Model-Setu repository ↗', url: PROJECT, primary: true }, { label: 'View workflow runs ↗', url: `${PROJECT}/actions` }]
  },
  actions: {
    icon: '⌘', title: 'GitHub Actions · CI/CD',
    text: 'Open the actual workflow runs for this repository. The workflow checks out the code, runs automated tests and builds the container image before the deployment step.',
    flow: ['Checkout repository', 'Run tests', 'Build and publish image'],
    actions: [{ label: 'Open Model-Setu workflow runs ↗', url: `${PROJECT}/actions`, primary: true }, { label: 'Open repository ↗', url: PROJECT }]
  },
  docker: {
    icon: '▥', title: 'Docker · Container Build',
    text: 'Docker is the container build and runtime layer in this project. Use the commands below in the Model-Setu project terminal to inspect the containers and images running on your machine. The package link opens the GitHub Packages area, not Docker documentation.',
    flow: ['Dockerfile / build config', 'Container image', 'Running container'],
    commands: 'docker ps\ndocker images\ndocker compose ps\ndocker compose logs --tail=100',
    actions: [{ label: 'Open Model-Setu GitHub Packages ↗', url: 'https://github.com/users/Paridhi21shukla/packages?repo_name=Model-Setu', primary: true }, { label: 'Open project repository ↗', url: PROJECT }]
  },
  render: {
    icon: '☁', title: 'Render · Live Backend',
    text: 'Open the deployed Model-Setu backend health endpoint to inspect the live service response. The backend dashboard remains the place for deployment history and rollback operations.',
    flow: ['Container deployment', 'Render service', 'Live backend endpoint'],
    actions: [{ label: 'Check live backend health ↗', url: `${BACKEND}/health`, primary: true }, { label: 'Open backend metrics ↗', url: `${BACKEND}/metrics` }, { label: 'Open Model-Setu dashboard ↗', url: 'index.html' }]
  },
  prometheus: {
    icon: '♨', title: 'Prometheus · Live Metrics',
    text: 'These links open the Prometheus instance and metrics endpoints configured in the local Model-Setu monitoring setup. The targets page shows whether Prometheus is scraping the backend and ML service. The raw endpoints expose the metrics themselves.',
    flow: ['Backend /metrics · port 5001', 'ML service /metrics · port 5002', 'Prometheus · port 9090'],
    actions: [{ label: 'Open Prometheus Targets ↗', url: 'http://localhost:9090/targets', primary: true }, { label: 'Open Prometheus Graph ↗', url: 'http://localhost:9090/graph' }, { label: 'Backend metrics · :5001/metrics ↗', url: 'http://localhost:5001/metrics' }, { label: 'ML service metrics · :5002/metrics ↗', url: 'http://localhost:5002/metrics' }]
  },
  grafana: {
    icon: '◉', title: 'Grafana · Monitoring Dashboard',
    text: 'Open your locally running Grafana instance to view the provisioned Model-Setu monitoring dashboard. Grafana reads the Prometheus data source configured for this project.',
    flow: ['Prometheus data source', 'Model-Setu dashboard', 'Live monitoring panels'],
    actions: [{ label: 'Open Grafana ↗', url: 'http://localhost:3000', primary: true }, { label: 'Open Prometheus Targets ↗', url: 'http://localhost:9090/targets' }]
  }
};

const featureInfo = {
  cicd: { title: 'Automated CI/CD', text: 'A code push starts the GitHub Actions workflow. Tests and the container build run before the configured deployment continues.', flow: ['Code push', 'Automated tests and build', 'Cloud deployment'], actions: [{ label: 'View actual GitHub Actions runs ↗', url: `${PROJECT}/actions`, primary: true }] },
  management: { title: 'Model Management', text: 'Use the existing Model-Setu dashboard to inspect deployment history, active version and model information. Rollback is performed through the existing backend workflow.', flow: ['Model information', 'Deployment history', 'Version and rollback controls'], actions: [{ label: 'Open Model-Setu dashboard ↗', url: 'index.html', primary: true }] },
  monitoring: { title: 'Monitoring & Observability', text: 'Prometheus scrapes metrics exposed by the backend and ML service. Grafana visualizes the collected time-series data in your Model-Setu dashboard.', flow: ['Backend and ML metrics', 'Prometheus scrape and storage', 'Grafana panels'], actions: [{ label: 'Open Grafana ↗', url: 'http://localhost:3000', primary: true }, { label: 'Open Prometheus Targets ↗', url: 'http://localhost:9090/targets' }, { label: 'Open backend metrics ↗', url: 'http://localhost:5001/metrics' }, { label: 'Open ML metrics ↗', url: 'http://localhost:5002/metrics' }] },
  rollback: { title: 'Rollback', text: 'The existing dashboard sends a rollback request to the backend and polls the rollback status. Use that dashboard control to perform the real rollback; this homepage does not trigger a deployment change.', flow: ['Select a deployment', 'Request rollback in dashboard', 'Verify rollback status'], actions: [{ label: 'Open dashboard rollback controls ↗', url: 'index.html', primary: true }] }
};

const stageInfo = {
  build: { title: '01 · Build', text: 'GitHub Actions checks out the repository and builds the application container image using the project build configuration.', flow: ['GitHub push', 'CI workflow', 'Docker image build'], actions: [{ label: 'View workflow runs ↗', url: `${PROJECT}/actions`, primary: true }] },
  test: { title: '02 · Test', text: 'The automated test stage validates the application before the pipeline proceeds. Check the actual workflow run for the latest test result.', flow: ['Install dependencies', 'Run pytest', 'Continue on success'], actions: [{ label: 'View test results in Actions ↗', url: `${PROJECT}/actions`, primary: true }] },
  deploy: { title: '03 · Deploy', text: 'The configured Render service hosts the deployed backend. Check the live health endpoint to inspect the current service response.', flow: ['Container package', 'Render deployment', 'Live backend endpoint'], actions: [{ label: 'Check live backend health ↗', url: `${BACKEND}/health`, primary: true }, { label: 'Open dashboard ↗', url: 'index.html' }] },
  monitor: { title: '04 · Monitor', text: 'Prometheus collects metrics from the backend and ML service. Grafana presents those metrics in the Model-Setu monitoring dashboard.', flow: ['Expose service metrics', 'Prometheus scrape', 'Grafana visualization'], actions: [{ label: 'Open Grafana ↗', url: 'http://localhost:3000', primary: true }, { label: 'Open Prometheus Targets ↗', url: 'http://localhost:9090/targets' }, { label: 'Backend metrics ↗', url: 'http://localhost:5001/metrics' }, { label: 'ML service metrics ↗', url: 'http://localhost:5002/metrics' }] }
};

const modal = document.getElementById('infoModal');
const modalTitle = document.getElementById('modalTitle');
const modalText = document.getElementById('modalText');
const modalIcon = document.getElementById('modalIcon');
const modalFlow = document.getElementById('modalFlow');
const oldModalLink = document.getElementById('modalLink');
const modalActions = document.createElement('div');
modalActions.className = 'modal-actions';
oldModalLink.replaceWith(modalActions);

const style = document.createElement('style');
style.textContent = `.modal-actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:22px}.modal-action{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:11px 15px;border:1px solid rgba(0,224,255,.38);border-radius:12px;color:#dffaff;text-decoration:none;font:600 13px/1.3 inherit;background:rgba(0,190,220,.08);transition:.2s}.modal-action:hover{transform:translateY(-2px);background:rgba(0,210,240,.18);border-color:#00eaff}.modal-action.primary{background:linear-gradient(110deg,#00c8dc,#168ee8);color:#001724;border-color:transparent}.modal-command{width:100%;white-space:pre-wrap;overflow-wrap:anywhere;padding:13px;border-radius:10px;background:#031321;border:1px solid rgba(0,220,255,.2);color:#9fefff;font:12px/1.7 ui-monospace,monospace}.modal-copy{border:1px solid rgba(0,224,255,.35);border-radius:9px;background:#092b40;color:#bff8ff;padding:8px 12px;cursor:pointer}`;
document.head.appendChild(style);

function openInfo(info, kicker = 'MODEL-SETU COMPONENT') {
  modalTitle.textContent = info.title;
  modalText.textContent = info.text;
  modalIcon.textContent = info.icon || '◈';
  document.getElementById('modalKicker').textContent = kicker;
  modalFlow.replaceChildren(...(info.flow || []).map(item => { const el = document.createElement('span'); el.textContent = item; return el; }));
  modalActions.replaceChildren();
  (info.actions || []).forEach(action => {
    const link = document.createElement('a');
    link.className = `modal-action${action.primary ? ' primary' : ''}`;
    link.href = action.url;
    link.textContent = action.label;
    if (/^https?:/.test(action.url)) { link.target = '_blank'; link.rel = 'noopener noreferrer'; }
    modalActions.appendChild(link);
  });
  if (info.commands) {
    const block = document.createElement('div'); block.className = 'modal-command'; block.textContent = info.commands;
    const copy = document.createElement('button'); copy.className = 'modal-copy'; copy.type = 'button'; copy.textContent = 'Copy Docker commands';
    copy.addEventListener('click', async () => { try { await navigator.clipboard.writeText(info.commands); copy.textContent = 'Copied ✓'; } catch { copy.textContent = 'Copy unavailable — select commands'; } });
    modalActions.append(block, copy);
  }
  modal.classList.add('open'); modal.setAttribute('aria-hidden', 'false');
}
function closeInfo() { modal.classList.remove('open'); modal.setAttribute('aria-hidden', 'true'); }

document.querySelectorAll('[data-tech]').forEach(btn => btn.addEventListener('click', () => openInfo(techInfo[btn.dataset.tech])));
document.querySelectorAll('[data-feature]').forEach(btn => btn.addEventListener('click', () => openInfo(featureInfo[btn.dataset.feature], 'PLATFORM CAPABILITY')));
document.querySelectorAll('[data-stage]').forEach(btn => btn.addEventListener('click', () => openInfo(stageInfo[btn.dataset.stage], 'DEPLOYMENT WORKFLOW')));
document.getElementById('modalClose').addEventListener('click', closeInfo);
modal.addEventListener('click', e => { if (e.target === modal) closeInfo(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeInfo(); });
document.getElementById('menuToggle').addEventListener('click', () => document.getElementById('mainNav').classList.toggle('open'));
document.querySelectorAll('#mainNav a').forEach(a => a.addEventListener('click', () => document.getElementById('mainNav').classList.remove('open')));
