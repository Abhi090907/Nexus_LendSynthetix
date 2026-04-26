export function initWarRoom() {
    const refreshBtn = document.getElementById("wr-refresh-btn");
    
    // Setup tab switching globally
    window.switchWrTab = function(i) {
        document.querySelectorAll(".wr-tab-btn").forEach((b,j) => b.classList.toggle("active", j===i));
        document.querySelectorAll(".wr-tab-content").forEach((c,j) => c.classList.toggle("active", j===i));
    };

    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => loadData(true));
    }
    
    // Auto load on init (just the view, don't re-run the whole committee yet)
    loadData(false);
}

function downloadSignedPDF() {
    const collection = window.appState?.collectionName || "unknown";
    const apiBaseUrl = window.appState?.apiBaseUrl || "http://localhost:8000";
    const url = `${apiBaseUrl}/download-report?collection=${encodeURIComponent(collection)}`;
    window.location.href = url;
}

function attachDownloadHandlers() {
    const pdfBtn = document.getElementById("wr-download-signed-pdf-btn");
    if (!pdfBtn) return;
    pdfBtn.addEventListener("click", downloadSignedPDF);
}

function setStatus(type, text) {
    const dot = document.getElementById("wr-status-dot");
    if(!dot) return;
    
    dot.className = "w-2 h-2 rounded-full " + 
        (type === "loading" ? "bg-yellow-500 animate-pulse" : 
         type === "error" ? "bg-red-500" : "bg-green-500");
    document.getElementById("wr-status-text").textContent = text;
}

function getRiskColor(l) {
    return l === "LOW" ? { bar: "bg-emerald-500", text: "text-emerald-700 dark:text-emerald-400" } : 
           l === "HIGH" ? { bar: "bg-red-500", text: "text-red-700 dark:text-red-400" } : 
           { bar: "bg-amber-500", text: "text-amber-700 dark:text-amber-400" };
}

function getVerdictClass(r) {
    if(!r) return "verdict-conditional";
    const u = r.toUpperCase();
    return u === "APPROVE" ? "verdict-approve" : u === "REJECT" ? "verdict-reject" : "verdict-conditional";
}

function getVerdictLabel(r) {
    if(!r) return "Decision pending";
    const u = r.toUpperCase();
    return u === "APPROVE" ? "Approved" : u === "REJECT" ? "Rejected" : "Conditional Approval";
}

function badgeForRec(r) {
    if(!r) return "";
    const u = r.toUpperCase();
    return u === "APPROVE" ? `<span class="wr-badge wr-badge-approve">Approve</span>` : 
           u.includes("REJECT") ? `<span class="wr-badge wr-badge-reject">Reject</span>` : 
           `<span class="wr-badge wr-badge-warn">${r}</span>`;
}

function parseDriverScore(d){
    const m = d.match(/([+-]\d+)/);
    return m ? parseInt(m[1]) : 0;
}

function renderMemoBlock(memo) {
    if(!memo || !Object.keys(memo).length) return `<div class="p-4 text-center text-gray-500 text-sm">No memo available.</div>`;
    const skip = ["recommendation", "summary"];
    
    let html = `<div class="space-y-4">`;
    if(memo.recommendation) {
        html += `<div><span class="text-xs font-semibold text-gray-500 uppercase">Recommendation</span><div class="mt-1">${badgeForRec(memo.recommendation)}</div></div>`;
    }
    if(memo.summary) {
        html += `<div><span class="text-xs font-semibold text-gray-500 uppercase">Summary</span><p class="text-sm text-gray-800 dark:text-gray-200 mt-1">${memo.summary}</p></div>`;
    }
    
    Object.entries(memo).filter(([k]) => !skip.includes(k)).forEach(([k,v]) => {
        const label = k.replace(/_/g," ").toUpperCase();
        if(Array.isArray(v)) {
            let li = v.map(i => `<li class="text-sm text-gray-600 dark:text-gray-300 py-1 border-b dark:border-gray-700 last:border-0">• ${i}</li>`).join("");
            html += `<div><span class="text-xs font-semibold text-gray-500 uppercase">${label}</span><ul class="mt-1">${li}</ul></div>`;
        } else {
            html += `<div><span class="text-xs font-semibold text-gray-500 uppercase">${label}</span><p class="text-sm text-gray-800 dark:text-gray-200 mt-1">${v}</p></div>`;
        }
    });
    html += `</div>`;
    return html;
}

function render(data) {
    const fd = data.final_decision || {};
    const rs = data.risk_score || {};
    const fa = (data.financial_analysis || {}).metrics || data.financial_analysis || {};
    const stress = data.stress_test_results || {};
    const rec = fd.final_recommendation || "";

    const questionElem = document.getElementById("wr-question-text");
    if (questionElem) {
        questionElem.textContent = data.question || "Commercial loan evaluation";
    }

    const score = rs.risk_score || 0;
    const level = rs.risk_level || "MEDIUM";
    const drivers = rs.key_drivers || [];
    const conditions = fd.conditions || [];

    const metricCards = [
        {label:"Risk score", value:score, sub:level},
        {label:"DSCR", value:fa.dscr||"—", sub:"debt service"},
        {label:"Revenue growth", value:fa.revenue_growth||"—", sub:"year on year"},
        {label:"Loan amount", value:fa.loan_amnt?"$"+Number(fa.loan_amnt).toLocaleString():"—", sub:"requested"},
        {label:"Interest rate", value:fa.loan_int_rate?fa.loan_int_rate+"%":"—", sub:"annual"},
        {label:"Debt trend", value:fa.debt_trend||"—", sub:"trajectory"}
    ].map(m => `
        <div class="stat-card">
            <div class="text-xs text-gray-500 dark:text-gray-400 mb-1">${m.label}</div>
            <div class="text-2xl font-semibold text-gray-800 dark:text-white">${m.value}</div>
            <div class="text-xs text-gray-400 mt-1">${m.sub}</div>
        </div>
    `).join("");

    const agents = [
        {initials:"RM", bg:"bg-blue-100", color:"text-blue-700", name:"Relationship Manager", role:"Sales Agent", memo:data.sales_memo},
        {initials:"CU", bg:"bg-green-100", color:"text-green-700", name:"Credit Underwriter", role:"Risk Agent", memo:data.risk_memo},
        {initials:"CO", bg:"bg-yellow-100", color:"text-yellow-700", name:"Compliance Officer", role:"Compliance Agent", memo:data.compliance_memo},
    ].map(a => `
        <div class="panel p-5">
            <div class="flex items-center gap-3 mb-3">
                <div class="w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm ${a.bg} ${a.color}">${a.initials}</div>
                <div><div class="text-sm font-semibold dark:text-white">${a.name}</div><div class="text-xs text-gray-500">${a.role}</div></div>
            </div>
            <div class="text-sm text-gray-600 dark:text-gray-300 line-clamp-3 mb-2">${(a.memo||{}).summary||"No memo available."}</div>
            ${badgeForRec((a.memo||{}).recommendation)}
        </div>
    `).join("");

    const driverRows = drivers.map(d => {
        const sc = parseDriverScore(d);
        const cls = sc > 0 ? "text-green-600" : sc < 0 ? "text-red-600" : "text-gray-500";
        return `<div class="flex justify-between items-center py-2 border-b dark:border-gray-700 last:border-0 text-sm">
            <span class="text-gray-600 dark:text-gray-300">${d.replace(/\([+-]?\d+\)/,"").trim()}</span>
            <span class="font-medium ${cls}">${sc!==0?(sc>0?"+":"")+sc:"—"}</span>
        </div>`;
    }).join("");

    const condRows = conditions.map((c,i) => `
        <li class="flex gap-2 py-2 border-b dark:border-gray-700 last:border-0 text-sm text-gray-600 dark:text-gray-300">
            <span class="font-semibold text-yellow-600 shrink-0">${i+1}.</span>
            <span>${c}</span>
        </li>
    `).join("");

    const stressRows = Object.entries(stress).map(([name,result]) => {
        const sc = result.risk_score || 0;
        const lv = result.risk_level || "MEDIUM";
        const c = getRiskColor(lv);
        return `<tr>
            <td class="text-gray-800 dark:text-gray-200">${name}</td>
            <td>
                <div class="flex items-center gap-2">
                    <div class="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                        <div class="h-full rounded-full ${c.bar}" style="width:${sc}%;"></div>
                    </div>
                    <span class="text-xs font-semibold w-6 ${c.text}">${sc}</span>
                </div>
            </td>
            <td class="font-medium text-xs ${c.text}">${lv}</td>
        </tr>`;
    }).join("");

    const memoLabels = ["Sales memo", "Risk memo", "Compliance memo", "Sales rebuttal"];
    const memoData = [data.sales_memo, data.risk_memo, data.compliance_memo, data.sales_rebuttal];
    const memoTabs = memoLabels.map((l,i) => `<button class="wr-tab-btn ${i===0?"active":""}" onclick="switchWrTab(${i})">${l}</button>`).join("");
    const memoContents = memoData.map((m,i) => `<div class="wr-tab-content ${i===0?"active":""}" id="wr-tab-${i}"><div class="panel p-5">${renderMemoBlock(m)}</div></div>`).join("");

    const mi = data.market_intelligence;
    let miHtml = '';
    if (!mi || !Object.keys(mi).length || mi.market_intelligence_summary === "Market intelligence unavailable") {
        miHtml = `<div class="panel p-5 text-gray-500 text-sm text-center">Market intelligence not available</div>`;
    } else {
        const summary = mi.market_intelligence_summary || "No summary available.";
        const signals = mi.investment_signals || {};
        const geo = mi.geopolitical_risk || {};
        const macro = mi.macro_context || {};
        
        const investScore = signals.overall_investment_score !== undefined ? signals.overall_investment_score : '—';
        const verdict = signals.investment_verdict || 'Unknown';
        
        const geoScore = geo.geopolitical_risk_score !== undefined ? geo.geopolitical_risk_score : '—';
        const geoFlags = (geo.geopolitical_flags || []).map(f => `<li class="text-xs text-red-600 dark:text-red-400 py-1 border-b border-gray-100 dark:border-gray-700 last:border-0">• ${f}</li>`).join('');
        
        const macroFlags = (macro.macro_flags || []).map(f => `<li class="text-xs text-red-600 dark:text-red-400 py-1 border-b border-gray-100 dark:border-gray-700 last:border-0">• ${f}</li>`).join('');
        
        const investReasons = (signals.key_reasons_to_invest || []).map(r => `<li class="text-xs text-green-600 dark:text-green-400 py-1 border-b border-gray-100 dark:border-gray-700 last:border-0">• ${r}</li>`).join('');
        const avoidReasons = (signals.key_reasons_to_avoid || []).map(r => `<li class="text-xs text-red-600 dark:text-red-400 py-1 border-b border-gray-100 dark:border-gray-700 last:border-0">• ${r}</li>`).join('');
        
        miHtml = `
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div class="panel p-5 lg:col-span-4 bg-blue-50/50 dark:bg-blue-900/10 border-blue-100 dark:border-blue-900/50">
                    <h5 class="text-sm font-semibold mb-2 dark:text-white text-blue-900 dark:text-blue-300">Market Summary</h5>
                    <p class="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">${summary}</p>
                </div>
                
                <div class="panel p-5">
                    <h5 class="text-sm font-semibold mb-2 dark:text-white">Investment Signals</h5>
                    <div class="flex items-baseline gap-2 mb-1">
                        <div class="text-3xl font-bold ${investScore >= 50 ? 'text-green-600' : 'text-red-600'}">${investScore}</div>
                        <div class="text-xs text-gray-400">/ 100</div>
                    </div>
                    <div class="text-xs font-medium text-gray-600 dark:text-gray-400 mb-4 line-clamp-2" title="${verdict}">${verdict}</div>
                    
                    ${investReasons ? `<div class="mt-3"><span class="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Key Positives</span><ul class="mt-1">${investReasons}</ul></div>` : ''}
                    ${avoidReasons ? `<div class="mt-3"><span class="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Key Risks</span><ul class="mt-1">${avoidReasons}</ul></div>` : ''}
                </div>
                
                <div class="panel p-5">
                    <h5 class="text-sm font-semibold mb-2 dark:text-white">Geopolitical Risk</h5>
                    <div class="flex items-baseline gap-2 mb-1">
                        <div class="text-3xl font-bold ${geoScore >= 50 ? 'text-red-600' : 'text-green-600'}">${geoScore}</div>
                        <div class="text-xs text-gray-400">/ 100</div>
                    </div>
                    
                    <div class="mt-4">
                        <span class="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Active Flags</span>
                        ${geoFlags ? `<ul class="mt-1">${geoFlags}</ul>` : '<div class="text-xs text-green-600 mt-1"><i class="fa-solid fa-check-circle mr-1"></i>No major geopolitical flags</div>'}
                    </div>
                </div>
                
                <div class="panel p-5 lg:col-span-2">
                    <h5 class="text-sm font-semibold mb-4 dark:text-white">Macro Environment</h5>
                    <span class="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Macro Risk Flags</span>
                    ${macroFlags ? `<ul class="mt-2 bg-red-50 dark:bg-red-900/10 rounded-lg p-3 border border-red-100 dark:border-red-900/30">${macroFlags}</ul>` : '<div class="text-xs text-green-600 mt-2 bg-green-50 dark:bg-green-900/10 rounded-lg p-3 border border-green-100 dark:border-green-900/30"><i class="fa-solid fa-check-circle mr-1"></i>Favorable macro environment detected</div>'}
                </div>
            </div>
        `;
    }

    const wrRoot = document.getElementById("wr-root");
    if (wrRoot) {
        window.appState = window.appState || {};
        window.appState.collectionName = data.collection_name || "unknown";
        window.appState.apiBaseUrl = "http://localhost:8000";

        wrRoot.innerHTML = `
            <div class="flex justify-end mb-4">
                <button id="wr-download-signed-pdf-btn" class="bg-slate-900 border border-blue-500 hover:bg-slate-800 text-white px-4 py-2 rounded-lg text-sm transition-colors">
                    🔐 Download Signed PDF Report
                </button>
            </div>
            <div class="text-right text-xs text-gray-500 dark:text-gray-400 mb-4">
                SHA-256 signed • Tamper-evident • Court-admissible
            </div>
            <div class="verdict-banner ${getVerdictClass(rec)}">
                <div class="text-xs font-bold uppercase tracking-wider mb-1 ${getVerdictClass(rec).replace('verdict-', 'text-').replace('-approve', '-green-700').replace('-reject', '-red-700').replace('-conditional', '-yellow-700')}">Final decision</div>
                <div class="text-2xl font-semibold mb-2 ${getVerdictClass(rec).replace('verdict-', 'text-').replace('-approve', '-green-700').replace('-reject', '-red-700').replace('-conditional', '-yellow-700')}">${getVerdictLabel(rec)}</div>
                <div class="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">${fd.reasoning||"No reasoning provided."}</div>
            </div>
            
            <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">${metricCards}</div>
            
            <div class="mb-6">
                <h4 class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">Market Intelligence</h4>
                ${miHtml}
            </div>
            
            <div class="mb-6">
                <h4 class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">Agent Summaries</h4>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">${agents}</div>
            </div>

            <div class="mb-6">
                <h4 class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">Full Agent Memos</h4>
                <div class="flex gap-2 mb-4 overflow-x-auto pb-2">${memoTabs}</div>
                <div>${memoContents}</div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                <div class="panel p-5">
                    <h4 class="text-sm font-semibold dark:text-white mb-3">Risk score drivers</h4>
                    <div>${driverRows||"<p class='text-sm text-gray-500'>No drivers available.</p>"}</div>
                </div>
                ${conditions.length>0 ? `
                <div class="panel p-5">
                    <h4 class="text-sm font-semibold dark:text-white mb-3">Approval conditions</h4>
                    <ul>${condRows}</ul>
                </div>` : ""}
            </div>

            <div class="mb-6">
                <h4 class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">Stress test scenarios</h4>
                <div class="panel overflow-hidden">
                    <table class="stress-table">
                        <thead><tr><th>Scenario</th><th>Risk score</th><th>Level</th></tr></thead>
                        <tbody>${stressRows||"<tr><td colspan='3' class='text-center py-4 text-gray-500'>No results.</td></tr>"}</tbody>
                    </table>
                </div>
            </div>
        `;
    }
    attachDownloadHandlers();

    const dashMiRoot = document.getElementById("dashboard-mi-root");
    if (dashMiRoot) {
        dashMiRoot.innerHTML = miHtml;
    }
}

async function loadData(runCommittee = false) {
    const btn = document.getElementById("wr-refresh-btn");
    if (!btn) return;
    
    btn.disabled = true; 
    
    if (runCommittee) {
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i> Analyzing...';
        setStatus("loading", "Running AI Committee debate (approx 1-2 mins)...");
        
        try {
            const runResp = await fetch("http://localhost:8000/run-war-room", { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (!runResp.ok) {
                const errorData = await runResp.json();
                throw new Error(errorData.detail || "AI Committee failed to complete.");
            }
            setStatus("loading", "Committee finished. Loading results...");
        } catch (err) {
            setStatus("error", "Committee Error: " + err.message);
            btn.disabled = false;
            btn.innerHTML = 'Refresh Data';
            return;
        }
    } else {
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i> Loading';
        setStatus("loading", "Fetching latest results...");
    }
    
    try {
        const response = await fetch("war_room_output.json?t=" + Date.now());
        if(!response.ok) {
            const r2 = await fetch("/dashboard/war_room_output.json?t=" + Date.now());
            if(!r2.ok) throw new Error("war_room_output.json not found.");
            render(await r2.json());
        } else {
            render(await response.json());
        }
        setStatus("ok", "Last updated: " + new Date().toLocaleTimeString());
    } catch (err) {
        setStatus("error", err.message);
        const wrRoot = document.getElementById("wr-root");
        if (wrRoot) {
            wrRoot.innerHTML = `
                <div class="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-6 text-red-700 dark:text-red-400 text-sm">
                    <strong>Could not load war_room_output.json</strong><br><br>
                    1. Click 'Refresh Data' to run the committee.<br>
                    2. Ensure the FastAPI backend is running on port 8000.
                </div>`;
        }
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Refresh Data';
    }
}
