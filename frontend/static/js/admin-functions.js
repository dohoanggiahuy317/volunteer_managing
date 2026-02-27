// Admin Functions - Pantry Management and Lead Assignment

/**
 * Get all pantries (admin sees all, leads see only assigned ones)
 */
async function getPantries() {
    try {
        const pantries = await apiGet('/api/pantries');
        return pantries;
    } catch (error) {
        console.error('Failed to get pantries:', error);
        throw error;
    }
}

/**
 * Get all pantries (public endpoint, no authorization required)
 */
async function getAllPantries() {
    try {
        const pantries = await apiGet('/api/all_pantries');
        return pantries;
    } catch (error) {
        console.error('Failed to get all pantries:', error);
        throw error;
    }
}

/**
 * Get specific pantry by ID
 */
async function getPantry(pantryId) {
    try {
        const pantry = await apiGet(`/api/pantries/${pantryId}`);
        return pantry;
    } catch (error) {
        console.error('Failed to get pantry:', error);
        throw error;
    }
}

/**
 * Create a new pantry (admin only)
 */
async function createPantry(pantryData) {
    try {
        const pantry = await apiPost('/api/pantries', pantryData);
        return pantry;
    } catch (error) {
        console.error('Failed to create pantry:', error);
        throw error;
    }
}

/**
 * Update pantry information
 */
async function updatePantry(pantryId, pantryData) {
    try {
        const pantry = await apiPatch(`/api/pantries/${pantryId}`, pantryData);
        return pantry;
    } catch (error) {
        console.error('Failed to update pantry:', error);
        throw error;
    }
}

/**
 * Delete a pantry
 */
async function deletePantry(pantryId) {
    try {
        await apiDelete(`/api/pantries/${pantryId}`);
    } catch (error) {
        console.error('Failed to delete pantry:', error);
        throw error;
    }
}

/**
 * Get leads for a pantry
 */
async function getPantryLeads(pantryId) {
    try {
        const pantry = await getPantry(pantryId);
        return pantry.leads || [];
    } catch (error) {
        console.error('Failed to get pantry leads:', error);
        throw error;
    }
}

/**
 * Add a lead to a pantry (admin only)
 */
async function addPantryLead(pantryId, userId) {
    try {
        const data = await apiPost(`/api/pantries/${pantryId}/leads`, { user_id: userId });
        return data;
    } catch (error) {
        console.error('Failed to add pantry lead:', error);
        throw error;
    }
}

/**
 * Remove a lead from a pantry (admin only)
 */
async function removePantryLead(pantryId, leadId) {
    try {
        await apiDelete(`/api/pantries/${pantryId}/leads/${leadId}`);
    } catch (error) {
        console.error('Failed to remove pantry lead:', error);
        throw error;
    }
}

/**
 * Get all roles
 */
async function getRoles() {
    try {
        const roles = await apiGet('/api/roles');
        return roles;
    } catch (error) {
        console.error('Failed to get roles:', error);
        throw error;
    }
}

/**
 * Populate a select element with users
 */
function populateUserSelect(selectElement, users, options = {}) {
    selectElement.innerHTML = '<option value="">Select User...</option>';
    
    users.forEach(user => {
        const option = document.createElement('option');
        option.value = user.user_id;
        option.textContent = user.full_name || user.email;
        
        if (options.selectedUserId && user.user_id == options.selectedUserId) {
            option.selected = true;
        }
        
        selectElement.appendChild(option);
    });
}

/**
 * Populate a select element with pantries
 */
function populatePantrySelect(selectElement, pantries, options = {}) {
    selectElement.innerHTML = '<option value="">Select Pantry...</option>';
    
    pantries.forEach(pantry => {
        const option = document.createElement('option');
        option.value = pantry.pantry_id;
        option.textContent = pantry.pantry_name;
        
        if (options.selectedPantryId && pantry.pantry_id == options.selectedPantryId) {
            option.selected = true;
        }
        
        selectElement.appendChild(option);
    });
}

/**
 * Populate a select element with roles
 */
function populateRoleSelect(selectElement, roles, options = {}) {
    selectElement.innerHTML = '<option value="">Select Role...</option>';
    
    roles.forEach(role => {
        const option = document.createElement('option');
        option.value = role.role_id;
        option.textContent = role.role_name;
        
        if (options.selectedRoleId && role.role_id == options.selectedRoleId) {
            option.selected = true;
        }
        
        selectElement.appendChild(option);
    });
}
