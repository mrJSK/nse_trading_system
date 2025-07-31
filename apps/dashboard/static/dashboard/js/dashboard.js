// apps/dashboard/static/dashboard/js/dashboard.js

// Global variables for task monitoring
let taskMonitorInterval = null;
let currentTaskId = null;

// Initialize dashboard
document.addEventListener("DOMContentLoaded", function () {
  // Auto-refresh dashboard every 30 seconds
  setInterval(function () {
    updateLastUpdateTime();
  }, 30000);

  // Initialize task monitoring for running tasks
  initializeTaskMonitoring();
});

function updateLastUpdateTime() {
  const now = new Date();
  const timeString = now.toLocaleString("en-IN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  const lastUpdateElement = document.getElementById("lastUpdate");
  if (lastUpdateElement) {
    lastUpdateElement.textContent = timeString;
  }
}

function refreshDashboard() {
  // Show loading indicator
  const refreshBtn = document.querySelector(".btn-primary");
  if (refreshBtn) {
    const originalText = refreshBtn.innerHTML;
    refreshBtn.innerHTML =
      '<i class="fas fa-spinner fa-spin"></i> Refreshing...';
    refreshBtn.disabled = true;

    // Reload the page
    setTimeout(() => {
      window.location.reload();
    }, 500);
  }
}

function initializeTaskMonitoring() {
  // Check for running tasks on page load
  const runningTasks = document.querySelectorAll(
    ".task-item .badge.bg-warning"
  );
  runningTasks.forEach((badge) => {
    if (badge.textContent.trim().toLowerCase() === "running") {
      const taskItem = badge.closest(".task-item");
      const taskId = taskItem.dataset.taskId;
      if (taskId) {
        startTaskMonitoring(taskId);
      }
    }
  });
}

function startTaskMonitoring(taskId) {
  currentTaskId = taskId;

  // Clear any existing interval
  if (taskMonitorInterval) {
    clearInterval(taskMonitorInterval);
  }

  // Start monitoring
  taskMonitorInterval = setInterval(() => {
    checkTaskStatus(taskId);
  }, 2000);
}

function checkTaskStatus(taskId) {
  fetch(`/dashboard/task-status/${taskId}/`)
    .then((response) => response.json())
    .then((data) => {
      updateTaskStatus(taskId, data);

      // Stop monitoring if task is completed or failed
      if (data.status === "completed" || data.status === "failed") {
        clearInterval(taskMonitorInterval);
        taskMonitorInterval = null;
        currentTaskId = null;
      }
    })
    .catch((error) => {
      console.error("Error checking task status:", error);
    });
}

function updateTaskStatus(taskId, data) {
  const taskItem = document.querySelector(`[data-task-id="${taskId}"]`);
  if (!taskItem) return;

  const badge = taskItem.querySelector(".badge");
  if (badge) {
    badge.textContent =
      data.status.charAt(0).toUpperCase() + data.status.slice(1);
    badge.className = "badge " + getBadgeClass(data.status);
  }
}

function getBadgeClass(status) {
  switch (status.toLowerCase()) {
    case "completed":
      return "bg-success";
    case "failed":
      return "bg-danger";
    case "running":
      return "bg-warning";
    default:
      return "bg-secondary";
  }
}

function updateTaskCommand() {
  const select = document.getElementById("taskSelect");
  const selectedOption = select.options[select.selectedIndex];
  const command = selectedOption.getAttribute("data-command") || "";
  const description =
    selectedOption.getAttribute("data-description") ||
    "Select a task to see its description.";
  const category = selectedOption.getAttribute("data-category") || "";

  document.getElementById("taskCommand").value = command;
  document.getElementById(
    "taskDescription"
  ).innerHTML = `<strong>${category}:</strong> ${description}`;
}

function viewCompanyDetails(symbol) {
  const modal = new bootstrap.Modal(document.getElementById("companyModal"));
  const modalBody = document.getElementById("companyDetails");

  modalBody.innerHTML = `
        <div class="text-center">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Loading company details...</p>
        </div>
    `;

  modal.show();

  fetch(`/dashboard/api/company/${symbol}/`)
    .then((response) => response.json())
    .then((data) => {
      if (data.error) {
        modalBody.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
        return;
      }

      modalBody.innerHTML = generateCompanyDetailsHTML(data);
    })
    .catch((error) => {
      console.error("Error loading company details:", error);
      modalBody.innerHTML = `<div class="alert alert-danger">Error loading company details: ${error.message}</div>`;
    });
}

function generateCompanyDetailsHTML(data) {
  return `
        <div class="row">
            <div class="col-md-6">
                <h6><i class="fas fa-info-circle"></i> Basic Information</h6>
                <table class="table table-sm">
                    <tr><td><strong>Symbol:</strong></td><td>${
                      data.basic_info.symbol
                    }</td></tr>
                    <tr><td><strong>Name:</strong></td><td>${
                      data.basic_info.name
                    }</td></tr>
                    <tr><td><strong>Industry:</strong></td><td>${
                      data.basic_info.industry || "N/A"
                    }</td></tr>
                    <tr><td><strong>BSE Code:</strong></td><td>${
                      data.basic_info.bse_code || "N/A"
                    }</td></tr>
                    <tr><td><strong>NSE Code:</strong></td><td>${
                      data.basic_info.nse_code || "N/A"
                    }</td></tr>
                    <tr><td><strong>Website:</strong></td><td>
                        ${
                          data.basic_info.website
                            ? `<a href="${data.basic_info.website}" target="_blank" class="btn btn-sm btn-outline-primary">
                                <i class="fas fa-external-link-alt"></i> Visit
                            </a>`
                            : "N/A"
                        }
                    </td></tr>
                </table>
                
                <h6 class="mt-3"><i class="fas fa-chart-bar"></i> Valuation Metrics</h6>
                <table class="table table-sm">
                    <tr><td><strong>Market Cap:</strong></td><td>₹${formatNumber(
                      data.valuation_metrics?.market_cap
                    )} Cr</td></tr>
                    <tr><td><strong>Current Price:</strong></td><td>₹${formatNumber(
                      data.valuation_metrics?.current_price,
                      2
                    )}</td></tr>
                    <tr><td><strong>P/E Ratio:</strong></td><td>${formatNumber(
                      data.valuation_metrics?.stock_pe,
                      1
                    )}</td></tr>
                    <tr><td><strong>Book Value:</strong></td><td>₹${formatNumber(
                      data.valuation_metrics?.book_value,
                      2
                    )}</td></tr>
                    <tr><td><strong>Dividend Yield:</strong></td><td>${formatNumber(
                      data.valuation_metrics?.dividend_yield,
                      2
                    )}%</td></tr>
                    <tr><td><strong>52W High:</strong></td><td>₹${formatNumber(
                      data.valuation_metrics?.high_52_week,
                      2
                    )}</td></tr>
                    <tr><td><strong>52W Low:</strong></td><td>₹${formatNumber(
                      data.valuation_metrics?.low_52_week,
                      2
                    )}</td></tr>
                </table>
            </div>
            
            <div class="col-md-6">
                <h6><i class="fas fa-coins"></i> Profitability Metrics</h6>
                <table class="table table-sm">
                    <tr><td><strong>ROE:</strong></td><td><span class="${getColorClass(
                      data.profitability_metrics?.roe,
                      15,
                      10
                    )}">${formatNumber(
    data.profitability_metrics?.roe,
    1
  )}%</span></td></tr>
                    <tr><td><strong>ROCE:</strong></td><td><span class="${getColorClass(
                      data.profitability_metrics?.roce,
                      15,
                      10
                    )}">${formatNumber(
    data.profitability_metrics?.roce,
    1
  )}%</span></td></tr>
                </table>
                
                <h6 class="mt-3"><i class="fas fa-trending-up"></i> Growth Metrics</h6>
                <table class="table table-sm">
                    <tr><td><strong>Sales Growth (1Y):</strong></td><td><span class="${getColorClass(
                      data.growth_metrics?.sales_growth_1y,
                      10,
                      0
                    )}">${formatNumber(
    data.growth_metrics?.sales_growth_1y,
    1
  )}%</span></td></tr>
                    <tr><td><strong>Sales Growth (3Y):</strong></td><td><span class="${getColorClass(
                      data.growth_metrics?.sales_growth_3y,
                      10,
                      0
                    )}">${formatNumber(
    data.growth_metrics?.sales_growth_3y,
    1
  )}%</span></td></tr>
                    <tr><td><strong>Sales Growth (5Y):</strong></td><td><span class="${getColorClass(
                      data.growth_metrics?.sales_growth_5y,
                      10,
                      0
                    )}">${formatNumber(
    data.growth_metrics?.sales_growth_5y,
    1
  )}%</span></td></tr>
                    <tr><td><strong>Profit Growth (1Y):</strong></td><td><span class="${getColorClass(
                      data.growth_metrics?.profit_growth_1y,
                      10,
                      0
                    )}">${formatNumber(
    data.growth_metrics?.profit_growth_1y,
    1
  )}%</span></td></tr>
                    <tr><td><strong>Profit Growth (3Y):</strong></td><td><span class="${getColorClass(
                      data.growth_metrics?.profit_growth_3y,
                      10,
                      0
                    )}">${formatNumber(
    data.growth_metrics?.profit_growth_3y,
    1
  )}%</span></td></tr>
                    <tr><td><strong>Profit Growth (5Y):</strong></td><td><span class="${getColorClass(
                      data.growth_metrics?.profit_growth_5y,
                      10,
                      0
                    )}">${formatNumber(
    data.growth_metrics?.profit_growth_5y,
    1
  )}%</span></td></tr>
                </table>
                
                <h6 class="mt-3"><i class="fas fa-star"></i> Fundamental Scores</h6>
                <table class="table table-sm">
                    <tr><td><strong>Overall Score:</strong></td><td>
                        <span class="badge ${getScoreBadgeClass(
                          data.fundamental_scores?.overall_score
                        )}">
                            ${formatNumber(
                              data.fundamental_scores?.overall_score,
                              0
                            )}
                        </span>
                    </td></tr>
                    <tr><td><strong>Valuation Score:</strong></td><td>
                        <span class="badge ${getScoreBadgeClass(
                          data.fundamental_scores?.valuation_score
                        )}">
                            ${formatNumber(
                              data.fundamental_scores?.valuation_score,
                              0
                            )}
                        </span>
                    </td></tr>
                    <tr><td><strong>Profitability Score:</strong></td><td>
                        <span class="badge ${getScoreBadgeClass(
                          data.fundamental_scores?.profitability_score
                        )}">
                            ${formatNumber(
                              data.fundamental_scores?.profitability_score,
                              0
                            )}
                        </span>
                    </td></tr>
                    <tr><td><strong>Growth Score:</strong></td><td>
                        <span class="badge ${getScoreBadgeClass(
                          data.fundamental_scores?.growth_score
                        )}">
                            ${formatNumber(
                              data.fundamental_scores?.growth_score,
                              0
                            )}
                        </span>
                    </td></tr>
                </table>
            </div>
        </div>
        
        ${
          data.basic_info.about
            ? `
            <div class="mt-3">
                <h6><i class="fas fa-info"></i> About</h6>
                <p class="text-muted">${data.basic_info.about}</p>
            </div>
        `
            : ""
        }
        
        ${
          data.qualitative_analysis?.pros?.length
            ? `
            <div class="mt-3">
                <h6><i class="fas fa-thumbs-up text-success"></i> Pros</h6>
                <ul class="list-group list-group-flush">
                    ${data.qualitative_analysis.pros
                      .map(
                        (pro) =>
                          `<li class="list-group-item border-0 px-0 py-1"><i class="fas fa-check text-success me-2"></i>${pro}</li>`
                      )
                      .join("")}
                </ul>
            </div>
        `
            : ""
        }
        
        ${
          data.qualitative_analysis?.cons?.length
            ? `
            <div class="mt-3">
                <h6><i class="fas fa-thumbs-down text-danger"></i> Cons</h6>
                <ul class="list-group list-group-flush">
                    ${data.qualitative_analysis.cons
                      .map(
                        (con) =>
                          `<li class="list-group-item border-0 px-0 py-1"><i class="fas fa-times text-danger me-2"></i>${con}</li>`
                      )
                      .join("")}
                </ul>
            </div>
        `
            : ""
        }
        
        <div class="mt-3 text-muted">
            <small><i class="fas fa-clock"></i> Last scraped: ${
              data.basic_info.last_scraped
                ? new Date(data.basic_info.last_scraped).toLocaleString()
                : "Never"
            }</small>
        </div>
    `;
}

// Add the missing showTaskOutput function
function showTaskOutput(taskId) {
  fetch(`/dashboard/task-status/${taskId}/`)
    .then((response) => response.json())
    .then((data) => {
      // Create and show modal with task output
      const modal = document.createElement("div");
      modal.className = "modal fade";
      modal.innerHTML = `
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Task Output - ID: ${taskId}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <strong>Status:</strong> 
                                <span class="badge ${getBadgeClass(
                                  data.status
                                )}">${data.status}</span>
                            </div>
                            ${
                              data.started_at
                                ? `<div class="mb-3"><strong>Started:</strong> ${new Date(
                                    data.started_at
                                  ).toLocaleString()}</div>`
                                : ""
                            }
                            ${
                              data.completed_at
                                ? `<div class="mb-3"><strong>Completed:</strong> ${new Date(
                                    data.completed_at
                                  ).toLocaleString()}</div>`
                                : ""
                            }
                            ${
                              data.output
                                ? `
                                <div class="mb-3">
                                    <strong>Output:</strong>
                                    <pre class="bg-light p-3 rounded" style="max-height: 400px; overflow-y: auto;">${data.output}</pre>
                                </div>
                            `
                                : ""
                            }
                            ${
                              data.error_log
                                ? `
                                <div class="mb-3">
                                    <strong>Errors:</strong>
                                    <pre class="bg-danger text-white p-3 rounded" style="max-height: 200px; overflow-y: auto;">${data.error_log}</pre>
                                </div>
                            `
                                : ""
                            }
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            `;

      document.body.appendChild(modal);
      const bsModal = new bootstrap.Modal(modal);
      bsModal.show();

      // Remove modal from DOM when hidden
      modal.addEventListener("hidden.bs.modal", () => {
        document.body.removeChild(modal);
      });
    })
    .catch((error) => {
      console.error("Error fetching task output:", error);
      alert("Error loading task output: " + error.message);
    });
}

// Utility functions
function formatNumber(value, decimals = 0) {
  if (value === null || value === undefined || isNaN(value)) {
    return "N/A";
  }
  return Number(value).toFixed(decimals);
}

function getColorClass(value, goodThreshold, okThreshold) {
  if (value === null || value === undefined || isNaN(value)) {
    return "text-muted";
  }

  if (value >= goodThreshold) {
    return "text-success";
  } else if (value >= okThreshold) {
    return "text-warning";
  } else {
    return "text-danger";
  }
}

function getScoreBadgeClass(score) {
  if (score === null || score === undefined || isNaN(score)) {
    return "bg-secondary";
  }

  if (score >= 75) {
    return "bg-success";
  } else if (score >= 50) {
    return "bg-warning";
  } else {
    return "bg-danger";
  }
}

// Portfolio chart functionality
function loadPortfolioChart() {
  fetch("/dashboard/api/portfolio-performance/")
    .then((response) => response.json())
    .then((data) => {
      if (data.dates && data.dates.length > 0) {
        renderPortfolioChart(data);
      }
    })
    .catch((error) => {
      console.error("Error loading portfolio chart:", error);
    });
}

function renderPortfolioChart(data) {
  const ctx = document.getElementById("portfolioChart");
  if (!ctx) return;

  new Chart(ctx, {
    type: "line",
    data: {
      labels: data.dates,
      datasets: [
        {
          label: "Portfolio Value",
          data: data.values,
          borderColor: "rgb(75, 192, 192)",
          backgroundColor: "rgba(75, 192, 192, 0.2)",
          tension: 0.1,
        },
        {
          label: "P&L",
          data: data.pnl,
          borderColor: "rgb(255, 99, 132)",
          backgroundColor: "rgba(255, 99, 132, 0.2)",
          tension: 0.1,
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        y: {
          beginAtZero: true,
        },
      },
    },
  });
}

// Error handling
window.addEventListener("error", function (e) {
  console.error("Global error:", e.error);
});

// Initialize charts if available
document.addEventListener("DOMContentLoaded", function () {
  if (typeof Chart !== "undefined") {
    loadPortfolioChart();
  }
});
