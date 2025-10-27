// API Base URL - automatically detects current host
const API_BASE = window.location.origin;

// Tab Switching
function switchTab(tabName) {
    // Remove active class from all tabs and content
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    // Add active class to selected tab
    event.target.classList.add('active');
    document.getElementById(`${tabName}-tab`).classList.add('active');
}

// Utility Functions
function showLoading(resultId) {
    const resultBox = document.getElementById(resultId);
    resultBox.innerHTML = '<div class="loading">Processing your request</div>';
    resultBox.classList.add('active');
}

function showError(resultId, error) {
    const resultBox = document.getElementById(resultId);
    resultBox.innerHTML = `<div class="error">❌ Error: ${error}</div>`;
    resultBox.classList.add('active');
}

function showSuccess(resultId, title, content) {
    const resultBox = document.getElementById(resultId);
    resultBox.innerHTML = `<h3>${title}</h3>${content}`;
    resultBox.classList.add('active');
}

// Code Review Submission
async function submitReview() {
    const code = document.getElementById('review-code').value;
    const language = document.getElementById('review-language').value;
    const context = document.getElementById('review-context').value;
    const checkStyle = document.getElementById('review-style').checked;
    const checkSecurity = document.getElementById('review-security').checked;
    const checkPerformance = document.getElementById('review-performance').checked;
    
    if (!code.trim()) {
        alert('Please enter code to review');
        return;
    }
    
    showLoading('review-result');
    
    try {
        const response = await fetch(`${API_BASE}/api/review`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                code,
                language,
                context: context || null,
                check_style: checkStyle,
                check_security: checkSecurity,
                check_performance: checkPerformance
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            displayReviewResults(data);
        } else {
            showError('review-result', data.message || 'Analysis failed');
        }
    } catch (error) {
        showError('review-result', error.message);
    }
}

function displayReviewResults(data) {
    const result = data.data;
    let html = `
        <h3>✅ Code Review Results</h3>
        <p><strong>Summary:</strong> ${result.summary || 'Analysis complete'}</p>
        ${result.score !== null && result.score !== undefined ? `<p><strong>Quality Score:</strong> ${result.score}/100</p>` : ''}
        <p><strong>Model:</strong> ${data.model_info.model_name} (${data.model_info.provider})</p>
        <p><strong>Processing Time:</strong> ${(data.model_info.processing_time_ms / 1000).toFixed(2)}s</p>
    `;
    
    if (result.issues && result.issues.length > 0) {
        html += '<h4>Issues Found:</h4>';
        result.issues.forEach(issue => {
            html += `
                <div class="issue-card ${issue.severity}">
                    <div>
                        <span class="issue-type">${issue.type}</span>
                        <span class="severity-badge ${issue.severity}">${issue.severity.toUpperCase()}</span>
                    </div>
                    <p><strong>Issue:</strong> ${issue.description}</p>
                    <p><strong>Suggestion:</strong> ${issue.suggestion}</p>
                    ${issue.line ? `<p><strong>Line:</strong> ${issue.line}</p>` : ''}
                </div>
            `;
        });
    } else {
        html += '<p class="success">✅ No major issues found!</p>';
    }
    
    if (result.recommendations && result.recommendations.length > 0) {
        html += '<h4>Recommendations:</h4><ul>';
        result.recommendations.forEach(rec => {
            html += `<li>${rec}</li>`;
        });
        html += '</ul>';
    }
    
    showSuccess('review-result', '', html);
}

// Documentation Submission
async function submitDocumentation() {
    const code = document.getElementById('doc-code').value;
    const language = document.getElementById('doc-language').value;
    const format = document.getElementById('doc-format').value;
    const includeExamples = document.getElementById('doc-examples').checked;
    
    if (!code.trim()) {
        alert('Please enter code to document');
        return;
    }
    
    showLoading('doc-result');
    
    try {
        const response = await fetch(`${API_BASE}/api/document`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                code,
                language,
                include_examples: includeExamples,
                format
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            displayDocumentationResults(data);
        } else {
            showError('doc-result', data.message || 'Documentation generation failed');
        }
    } catch (error) {
        showError('doc-result', error.message);
    }
}

function displayDocumentationResults(data) {
    const result = data.data;
    const html = `
        <h3>📝 Generated Documentation</h3>
        <p><strong>Format:</strong> ${result.format}</p>
        <p><strong>Model:</strong> ${data.model_info.model_name} (${data.model_info.provider})</p>
        <p><strong>Processing Time:</strong> ${(data.model_info.processing_time_ms / 1000).toFixed(2)}s</p>
        <hr style="margin: 20px 0;">
        <pre>${escapeHtml(result.documentation)}</pre>
    `;
    showSuccess('doc-result', '', html);
}

// Bug Prediction Submission
async function submitBugPrediction() {
    const code = document.getElementById('bugs-code').value;
    const language = document.getElementById('bugs-language').value;
    const context = document.getElementById('bugs-context').value;
    const severity = document.getElementById('bugs-severity').value;
    
    if (!code.trim()) {
        alert('Please enter code to analyze');
        return;
    }
    
    showLoading('bugs-result');
    
    try {
        const response = await fetch(`${API_BASE}/api/predict-bugs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                code,
                language,
                context: context || null,
                severity_threshold: severity
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            displayBugResults(data);
        } else {
            showError('bugs-result', data.message || 'Bug prediction failed');
        }
    } catch (error) {
        showError('bugs-result', error.message);
    }
}

function displayBugResults(data) {
    const result = data.data;
    let html = `
        <h3>🐛 Bug Prediction Results</h3>
        ${result.overall_assessment ? `<p><strong>Assessment:</strong> ${result.overall_assessment}</p>` : ''}
        ${result.risk_score !== null && result.risk_score !== undefined ? `<p><strong>Risk Score:</strong> ${result.risk_score}/100</p>` : ''}
        <p><strong>Model:</strong> ${data.model_info.model_name} (${data.model_info.provider})</p>
        <p><strong>Processing Time:</strong> ${(data.model_info.processing_time_ms / 1000).toFixed(2)}s</p>
    `;
    
    if (result.bugs && result.bugs.length > 0) {
        html += '<h4>Potential Bugs Found:</h4>';
        result.bugs.forEach(bug => {
            html += `
                <div class="bug-card ${bug.severity}">
                    <div>
                        <span class="issue-type">${bug.type}</span>
                        <span class="severity-badge ${bug.severity}">${bug.severity.toUpperCase()}</span>
                        ${bug.confidence ? `<span style="margin-left: 10px;">Confidence: ${(bug.confidence * 100).toFixed(0)}%</span>` : ''}
                    </div>
                    <p><strong>Description:</strong> ${bug.description}</p>
                    <p><strong>Scenario:</strong> ${bug.scenario}</p>
                    <p><strong>Fix:</strong> ${bug.fix}</p>
                    ${bug.line ? `<p><strong>Line:</strong> ${bug.line}</p>` : ''}
                </div>
            `;
        });
    } else {
        html += '<p class="success">✅ No significant bugs predicted!</p>';
    }
    
    showSuccess('bugs-result', '', html);
}

// Code Generation Submission
async function submitCodeGeneration() {
    const description = document.getElementById('gen-description').value;
    const language = document.getElementById('gen-language').value;
    const context = document.getElementById('gen-context').value;
    const includeTests = document.getElementById('gen-tests').checked;
    
    if (!description.trim()) {
        alert('Please enter a description');
        return;
    }
    
    showLoading('gen-result');
    
    try {
        const response = await fetch(`${API_BASE}/api/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                description,
                language,
                context: context || null,
                include_tests: includeTests
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            displayGenerationResults(data);
        } else {
            showError('gen-result', data.message || 'Code generation failed');
        }
    } catch (error) {
        showError('gen-result', error.message);
    }
}

function displayGenerationResults(data) {
    const result = data.data;
    const html = `
        <h3>⚡ Generated Code</h3>
        <p><strong>Language:</strong> ${result.language || 'N/A'}</p>
        <p><strong>Model:</strong> ${data.model_info.model_name} (${data.model_info.provider})</p>
        <p><strong>Processing Time:</strong> ${(data.model_info.processing_time_ms / 1000).toFixed(2)}s</p>
        ${result.explanation ? `<p><strong>Explanation:</strong> ${result.explanation}</p>` : ''}
        ${result.complexity ? `<p><strong>Complexity:</strong> ${result.complexity}</p>` : ''}
        <hr style="margin: 20px 0;">
        <h4>Generated Code:</h4>
        <pre>${escapeHtml(result.code)}</pre>
        ${result.usage_example ? `<h4>Usage Example:</h4><pre>${escapeHtml(result.usage_example)}</pre>` : ''}
        ${result.dependencies && result.dependencies.length > 0 ? `<p><strong>Dependencies:</strong> ${result.dependencies.join(', ')}</p>` : ''}
    `;
    showSuccess('gen-result', '', html);
}

// Utility: Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Load system info on page load
window.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch(`${API_BASE}/api/health`);
        const health = await response.json();
        console.log('System Health:', health);
    } catch (error) {
        console.error('Health check failed:', error);
    }
});