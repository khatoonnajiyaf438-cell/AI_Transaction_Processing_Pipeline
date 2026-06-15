const API_BASE = "/api/v1";

const uploadForm = document.querySelector("#upload-form");
const fileInput = document.querySelector("#csv-file");
const uploadMessage = document.querySelector("#upload-message");
const jobsList = document.querySelector("#jobs-list");
const statusFilter = document.querySelector("#status-filter");
const results = document.querySelector("#results");
const refreshButton = document.querySelector("#refresh-button");

let selectedJobId = null;

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = fileInput.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);
  uploadMessage.textContent = "Uploading...";
  uploadMessage.style.color = "#0f766e";

  try {
    const response = await fetch(`${API_BASE}/jobs/upload`, { method: "POST", body: formData });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Upload failed");
    selectedJobId = data.job_id;
    uploadMessage.textContent = `Job ${data.job_id} accepted.`;
    fileInput.value = "";
    await loadJobs();
  } catch (error) {
    uploadMessage.textContent = error.message;
    uploadMessage.style.color = "#b42318";
  }
});

statusFilter.addEventListener("change", loadJobs);
refreshButton.addEventListener("click", async () => {
  await loadJobs();
  if (selectedJobId) await loadResults(selectedJobId);
});

async function loadJobs() {
  const query = statusFilter.value ? `?status=${statusFilter.value}` : "";
  const response = await fetch(`${API_BASE}/jobs${query}`);
  const jobs = await response.json();

  jobsList.innerHTML = "";
  if (!jobs.length) {
    jobsList.innerHTML = `<p class="job-meta">No jobs found.</p>`;
    return;
  }

  jobs.forEach((job) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `job-item ${job.id === selectedJobId ? "active" : ""}`;
    button.innerHTML = `
      <div class="job-title">
        <span>${escapeHtml(job.file_name)}</span>
        <span class="badge ${job.status}">${job.status}</span>
      </div>
      <div class="job-meta">${job.row_count_clean}/${job.row_count_raw} rows · ${new Date(job.created_at).toLocaleString()}</div>
      <div class="job-meta">${job.id}</div>
    `;
    button.addEventListener("click", () => {
      selectedJobId = job.id;
      loadResults(job.id);
      loadJobs();
    });
    jobsList.appendChild(button);
  });
}

async function loadResults(jobId) {
  results.innerHTML = `<div class="results-empty">Loading job...</div>`;
  const statusResponse = await fetch(`${API_BASE}/jobs/${jobId}/status`);
  const statusData = await statusResponse.json();

  if (statusData.status !== "completed") {
    results.innerHTML = `
      <div class="results-empty">
        <div>
          <h2>${statusData.status}</h2>
          <p>${statusData.error_message || "Results are not ready yet."}</p>
        </div>
      </div>
    `;
    return;
  }

  const response = await fetch(`${API_BASE}/jobs/${jobId}/results`);
  const data = await response.json();
  const summary = data.summary;
  const anomalies = data.flagged_anomalies.slice(0, 8);

  results.innerHTML = `
    <div class="metrics">
      <div class="metric"><span>INR spend</span><strong>${summary.total_spend_inr}</strong></div>
      <div class="metric"><span>USD spend</span><strong>${summary.total_spend_usd}</strong></div>
      <div class="metric"><span>Risk</span><strong>${escapeHtml(summary.risk_level)}</strong></div>
    </div>
    <div class="narrative">
      <h2>Narrative</h2>
      <p>${escapeHtml(summary.narrative)}</p>
    </div>
    <div class="table-wrap">
      <h2>Anomalies (${summary.anomaly_count})</h2>
      <table>
        <thead><tr><th>Date</th><th>Merchant</th><th>Amount</th><th>Reason</th></tr></thead>
        <tbody>
          ${anomalies.map((item) => `
            <tr>
              <td>${item.date || ""}</td>
              <td>${escapeHtml(item.merchant)}</td>
              <td>${item.currency} ${item.amount}</td>
              <td>${escapeHtml(item.anomaly_reason || "")}</td>
            </tr>
          `).join("") || `<tr><td colspan="4">No anomalies.</td></tr>`}
        </tbody>
      </table>
    </div>
    <div class="table-wrap">
      <h2>Spend By Category</h2>
      <table>
        <thead><tr><th>Category</th><th>Currency Totals</th></tr></thead>
        <tbody>
          ${Object.entries(data.spend_by_category).map(([category, totals]) => `
            <tr><td>${escapeHtml(category)}</td><td>${escapeHtml(JSON.stringify(totals))}</td></tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

loadJobs();
setInterval(loadJobs, 8000);
