let shapChartInstance = null;
window.shapData = null; // Exposed globally so UI can trigger re-renders

export function initAnalysis() {
    const analysisForm = document.getElementById('analysis-form');
    const analyzeBtn = document.getElementById('analyze-btn');
    const jsonInput = document.getElementById('json-input');
    const analysisResults = document.getElementById('analysis-results');
    const analysisError = document.getElementById('analysis-error');
    
    if (!analysisForm) return;

    analysisForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        let payload;
        try {
            payload = JSON.parse(jsonInput.value);
            analysisError.classList.add('hidden');
        } catch(err) {
            analysisError.textContent = "Invalid JSON structure.";
            analysisError.classList.remove('hidden');
            return;
        }

        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i> Analyzing...';
        analysisResults.classList.add('hidden');

        try {
            const response = await fetch('http://localhost:8000/explain-loan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ applicant: payload })
            });
            const data = await response.json();
            
            if (response.ok) {
                document.getElementById('res-score').textContent = data.prediction || '—';
                
                const levelEl = document.getElementById('res-level');
                levelEl.textContent = data.risk_level || '—';
                levelEl.className = 'text-3xl font-bold ' + 
                    (data.risk_level === 'HIGH' ? 'text-red-600' : data.risk_level === 'LOW' ? 'text-green-600' : 'text-yellow-600');
                    
                document.getElementById('res-grade').textContent = data.predicted_grade || '—';
                
                window.shapData = data.shap_explanation;
                analysisResults.classList.remove('hidden');
            } else {
                throw new Error(data.detail || "Analysis failed.");
            }
        } catch (err) {
            analysisError.textContent = err.message;
            analysisError.classList.remove('hidden');
        } finally {
            analyzeBtn.disabled = false;
            analyzeBtn.innerHTML = 'Analyze Risk';
        }
    });

    const explainBtn = document.getElementById('view-explain-btn');
    if(explainBtn) {
        explainBtn.addEventListener('click', () => {
            document.querySelector('[data-target=explain]').click();
        });
    }

    // Attach render method globally
    window.renderChart = renderChart;
}

function renderChart() {
    if (!window.shapData) return;
    
    document.getElementById('explain-empty').classList.add('hidden');
    document.getElementById('explain-content').classList.remove('hidden');

    const labels = window.shapData.map(d => d.feature);
    const values = window.shapData.map(d => d.impact);
    
    const bgColors = window.shapData.map(d => d.direction === 'INCREASES_RISK' ? 'rgba(239, 68, 68, 0.8)' : 'rgba(16, 185, 129, 0.8)');
    const borderColors = window.shapData.map(d => d.direction === 'INCREASES_RISK' ? 'rgb(220, 38, 38)' : 'rgb(5, 150, 105)');

    const ctx = document.getElementById('shapChart').getContext('2d');
    if (shapChartInstance) shapChartInstance.destroy();
    
    shapChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'SHAP Value Impact',
                data: values,
                backgroundColor: bgColors,
                borderColor: borderColors,
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => {
                            const val = ctx.raw;
                            return val > 0 ? `+${val} (Increases Risk)` : `${val} (Reduces Risk)`;
                        }
                    }
                }
            },
            scales: {
                y: { grid: { color: document.documentElement.classList.contains('dark') ? '#374151' : '#f3f4f6' } },
                x: { grid: { display: false } }
            }
        }
    });

    const ul = document.getElementById('driver-list');
    ul.innerHTML = '';
    window.shapData.forEach(item => {
        const isRisk = item.direction === 'INCREASES_RISK';
        const li = document.createElement('li');
        li.className = "flex items-start p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700";
        li.innerHTML = `
            <div class="flex-shrink-0 mr-4 mt-1">
                <span class="inline-flex items-center justify-center h-8 w-8 rounded-full ${isRisk ? 'bg-red-100 text-red-600' : 'bg-green-100 text-green-600'}">
                    <i class="fa-solid ${isRisk ? 'fa-arrow-up' : 'fa-arrow-down'}"></i>
                </span>
            </div>
            <div>
                <span class="text-sm font-semibold text-gray-800 dark:text-gray-200 block mb-1">${item.feature}</span>
                <span class="text-sm text-gray-600 dark:text-gray-400">
                    ${isRisk 
                        ? `The property of this feature increased the risk profile by an impact magnitude of <strong>+${item.impact}</strong>.` 
                        : `The stability of this trait reduced the risk profile by a margin of <strong>${item.impact}</strong>.`
                    }
                </span>
            </div>
        `;
        ul.appendChild(li);
    });
}
