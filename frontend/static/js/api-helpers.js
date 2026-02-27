// API Helper Functions
// Preserves query parameters (especially ?user_id=X) across all API calls

/**
 * Core API call function that preserves query parameters
 */
async function apiCall(path, options = {}) {
    // Preserve query parameters from current URL
    const urlParams = new URLSearchParams(window.location.search);
    const separator = path.includes('?') ? '&' : '?';
    const fullPath = path + separator + urlParams.toString();
    
    const response = await fetch(fullPath, options);
    
    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API Error: ${response.status} - ${errorText}`);
    }
    
    return response.json();
}

/**
 * GET request
 */
async function apiGet(path) {
    return apiCall(path, { method: 'GET' });
}

/**
 * POST request
 */
async function apiPost(path, data) {
    return apiCall(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
}

/**
 * PATCH request
 */
async function apiPatch(path, data) {
    return apiCall(path, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
}

/**
 * DELETE request
 */
async function apiDelete(path) {
    return apiCall(path, { method: 'DELETE' });
}
