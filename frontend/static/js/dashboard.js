// Global state
let currentUser = null;
let currentPantryId = null;
let allPantries = [];
let allPublicPantries = []

// Wait for all scripts to load before initializing
window.addEventListener('load', async function () {
    try {
        // Verify functions are loaded
        if (typeof getCurrentUser === 'undefined') {
            throw new Error('Required functions not loaded. Please refresh the page.');
        }

        // Load current user
        currentUser = await getCurrentUser();
        document.getElementById('user-email').textContent = currentUser.email;

        // Display roles
        const roleNames = currentUser.roles.join(', ');
        document.getElementById('user-role').textContent = roleNames;

        // Setup UI based on role
        setupRoleBasedUI();

        // Load pantries
        await loadPantries();

        // Setup event listeners
        setupEventListeners();

        // Load initial tab content
        await loadCalendarShifts();

    } catch (error) {
        console.error('Failed to initialize:', error);
        showMessage('calendar', `Failed to load: ${error.message}`, 'error');
        // Display error on page
        document.getElementById('shifts-container').innerHTML = `
                    <div style="background: #fed7d7; border: 2px solid #f56565; padding: 2rem; border-radius: 12px; text-align: center;">
                        <h3 style="color: #742a2a; margin-bottom: 1rem;">⚠️ Failed to Load</h3>
                        <p style="color: #742a2a; margin-bottom: 1rem;"><strong>${error.message}</strong></p>
                        <p style="color: #742a2a; font-size: 0.875rem;">
                            Make sure you include <code>?user_id=X</code> in the URL<br>
                            Example: <code>http://127.0.0.1:5000/?user_id=4</code>
                        </p>
                        <button onclick="window.location.href='/?user_id=4'" class="btn btn-primary" style="margin-top: 1rem;">
                            Load as Admin
                        </button>
                    </div>
                `;
    }
});

// Setup UI based on role
function setupRoleBasedUI() {
    const isAdmin = currentUser.roles.includes('ADMIN');
    const isPantryLead = currentUser.roles.includes('PANTRY_LEAD');

    // Show/hide tabs based on role
    if (isAdmin) {
        // Admin sees everything
        document.getElementById('tab-shifts').classList.remove('hidden');
        document.getElementById('tab-admin').classList.remove('hidden');
    } else if (isPantryLead) {
        // Pantry lead can manage shifts
        document.getElementById('tab-shifts').classList.remove('hidden');
    } else {
        // Volunteer only sees calendar
        // (already default view)
    }
}

// Load pantries
async function loadPantries() {
    try {
        allPantries = await getPantries();
        allPublicPantries = await getAllPantries();
        const select = document.getElementById('pantry-select');
        const assignSelect = document.getElementById('assign-pantry');

        select.innerHTML = '';
        assignSelect.innerHTML = '<option value="">-- Select Pantry --</option>';

        if (allPantries.length === 0) {
            select.innerHTML = '<option value="">No pantries available</option>';
            return;
        }

        allPantries.forEach(pantry => {
            const opt = document.createElement('option');
            opt.value = pantry.pantry_id;
            opt.textContent = pantry.name;
            select.appendChild(opt);

            const assignOpt = opt.cloneNode(true);
            assignSelect.appendChild(assignOpt);
        });

        // Select first pantry by default
        if (allPantries.length > 0) {
            currentPantryId = allPantries[0].pantry_id;
            select.value = currentPantryId;
        }

        // Load pantry leads for admin
        if (currentUser.roles.includes('ADMIN')) {
            await loadPantryLeads();
        }
    } catch (error) {
        console.error('Failed to load pantries:', error);
        showMessage('calendar', `Failed to load pantries: ${error.message}`, 'error');
    }
}

// Load pantry leads (admin)
async function loadPantryLeads() {
    try {
        const leads = await getAllUsers('PANTRY_LEAD');
        const leadSelect = document.getElementById('assign-lead');
        leadSelect.innerHTML = '<option value="">-- Select Lead --</option>';

        leads.forEach(lead => {
            const opt = document.createElement('option');
            opt.value = lead.user_id;
            opt.textContent = `${lead.full_name} (${lead.email})`;
            leadSelect.appendChild(opt);
        });

        // Update pantries table
        await updatePantriesTable();
    } catch (error) {
        console.error('Failed to load leads:', error);
    }
}

// Update pantries table
async function updatePantriesTable() {
    const tbody = document.getElementById('pantries-table-body');
    tbody.innerHTML = '';

    if (allPantries.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: #718096;">No pantries yet</td></tr>';
        return;
    }

    allPantries.forEach(pantry => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
                    <td>${pantry.name}</td>
                    <td>${pantry.location_address || '—'}</td>
                    <td>${pantry.leads && pantry.leads.length > 0
                ? pantry.leads.map(l => `<span style="background: #e2e8f0; padding: 0.25rem 0.5rem; border-radius: 4px; margin-right: 0.5rem; display: inline-block; margin-bottom: 0.25rem;">${l.full_name}</span>`).join('')
                : '<span style="color: #718096;">No leads assigned</span>'}</td>
                `;
        tbody.appendChild(tr);
    });
}

// Load calendar shifts from ALL pantries
async function loadCalendarShifts() {
    try {
        document.getElementById('shifts-container').innerHTML = '<div class="loading"><div class="spinner"></div><p>Loading shifts from all pantries...</p></div>';

        // Load shifts from all pantries and group by pantry
        const allShifts = {};

        if (!allPublicPantries || allPublicPantries.length === 0) {
            document.getElementById('shifts-container').innerHTML = '<p style="text-align: center; color: #718096; padding: 2rem;">No pantries available</p>';
            return;
        }

        for (const pantry of allPublicPantries) {
            try {
                const shifts = await getShifts(pantry.pantry_id);

                if (shifts && shifts.length > 0) {
                    for (const shift of shifts) {
                        allShifts[pantry.pantry_id] = {
                            name: pantry.name,
                            location: pantry.location_address,
                            shifts: shifts && shifts.length > 0 ? shifts : []
                        };
                    }
                }

            } catch (err) {
                console.warn(`Failed to load shifts for pantry ${pantry.pantry_id}:`, err);
            }
        }

        displayAllShiftsGroupedByPantry(allShifts);
    } catch (error) {
        console.error('Failed to load shifts:', error);
        document.getElementById('shifts-container').innerHTML = `<p style="text-align: center; color: #f56565;">Error: ${error.message}</p>`;
    }
}

// Display all shifts grouped by pantry
function displayAllShiftsGroupedByPantry(allShifts) {
    console.log('All shifts grouped by pantry:', allShifts);
    const container = document.getElementById('shifts-container');

    const pantryIds = Object.keys(allShifts);
    if (pantryIds.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #718096; padding: 2rem;">No pantries available</p>';
        return;
    }

    container.innerHTML = '';

    // Create sections for each pantry
    pantryIds.forEach(pantryId => {
        const pantryData = allShifts[pantryId];

        // Pantry section header
        const section = document.createElement('div');
        section.style.marginBottom = '2rem';

        const header = document.createElement('div');
        header.style.cssText = 'background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;';
        header.innerHTML = `
                    <h3 style="margin: 0; font-size: 1.25rem;">${pantryData.name}</h3>
                    <p style="margin: 0.25rem 0 0 0; opacity: 0.9; font-size: 0.875rem;">${pantryData.location || 'No location listed'}</p>
                `;
        section.appendChild(header);

        // Shifts grid for this pantry
        const grid = document.createElement('div');
        grid.className = 'shifts-grid';

        if (pantryData.shifts && pantryData.shifts.length > 0) {
            pantryData.shifts.forEach(shift => {
                displayShiftCard(grid, shift);
            });
        } else {
            const noShifts = document.createElement('p');
            noShifts.style.cssText = 'text-align: center; color: #718096; padding: 2rem;';
            noShifts.textContent = 'No shifts scheduled yet';
            grid.appendChild(noShifts);
        }

        section.appendChild(grid);
        container.appendChild(section);
    });
}

// Display shifts as cards
function displayShiftsCards(shifts) {
    const container = document.getElementById('shifts-container');

    if (!shifts || shifts.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #718096; padding: 2rem;">No shifts available yet</p>';
        return;
    }

    container.innerHTML = '';
    const grid = document.createElement('div');
    grid.className = 'shifts-grid';

    shifts.forEach(shift => {
        displayShiftCard(grid, shift);
    });

    container.appendChild(grid);
}

// Display a single shift card
function displayShiftCard(grid, shift) {
    const card = document.createElement('div');
    card.className = 'shift-card';

    const startDate = new Date(shift.start_time);
    const endDate = new Date(shift.end_time);

    let rolesHTML = '';
    // API returns roles in 'roles' field, not 'shift_roles'
    const shiftRoles = shift.roles || shift.shift_roles || [];

    if (shiftRoles && shiftRoles.length > 0) {
        rolesHTML = shiftRoles.map(role => {
            const filled = role.filled_count || 0;
            const required = role.required_count || 1;
            const percentage = (filled / required) * 100;
            const isFull = filled >= required;
            const capacityClass = isFull ? 'capacity-full' : 'capacity-available';

            return `
                        <div class="role-item">
                            <div>
                                <div class="role-name">${role.role_title}</div>
                                <div class="role-capacity ${capacityClass}">${filled}/${required} filled</div>
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width: ${percentage}%"></div>
                                </div>
                            </div>
                            <div>
                                ${isFull
                    ? '<button class="btn btn-secondary" disabled>Full</button>'
                    : `<button class="btn btn-success" onclick="signupForRole(${role.shift_role_id})">Sign Up</button>`
                }
                            </div>
                        </div>
                    `;
        }).join('');
    } else {
        rolesHTML = '<p style="color: #718096; font-style: italic;">No positions available</p>';
    }

    card.innerHTML = `
                <div class="shift-header">
                    <div>
                        <div class="shift-title">${shift.shift_name}</div>
                        <div class="shift-date">📅 ${startDate.toLocaleDateString()} | ${startDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - ${endDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
                    </div>
                </div>
                <div class="shift-roles">
                    ${rolesHTML}
                </div>
            `;

    grid.appendChild(card);
}

// Signup for role
async function signupForRole(roleId) {
    try {
        await signupForShift(roleId);
        showMessage('calendar', 'Successfully signed up!', 'success');
        await loadCalendarShifts(); // Reload to show updated counts
    } catch (error) {
        showMessage('calendar', `Signup failed: ${error.message}`, 'error');
    }
}

// Load shifts table (admin)
async function loadShiftsTable() {
    if (!currentPantryId) return;

    try {
        const shifts = await getShifts(currentPantryId);
        const tbody = document.getElementById('shifts-table-body');
        tbody.innerHTML = '';

        if (shifts.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #718096;">No shifts created yet</td></tr>';
            return;
        }

        shifts.forEach(shift => {
            console.log('Shift data for table:', shift);
            const startDate = new Date(shift.start_time);
            const rolesText = shift.roles && shift.roles.length > 0
                ? shift.roles.map(r => `${r.role_title} (${r.filled_count || 0}/${r.required_count})`).join(', ')
                : 'No roles';

            const tr = document.createElement('tr');
            tr.innerHTML = `
                        <td><strong>${shift.shift_name}</strong></td>
                        <td>${startDate.toLocaleString()}</td>
                        <td>${rolesText}</td>
                        <td>
                            <button class="btn btn-danger" onclick="deleteShiftConfirm(${shift.shift_id})" style="padding: 0.5rem 1rem; font-size: 0.875rem;">Delete</button>
                        </td>
                    `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.error('Failed to load shifts table:', error);
    }
}

// Delete shift with confirmation
async function deleteShiftConfirm(shiftId) {
    if (!confirm('Delete this shift? This will also delete all roles and signups.')) return;

    try {
        await deleteShift(shiftId);
        showMessage('shifts', 'Shift deleted successfully!', 'success');
        await loadShiftsTable();
        await loadCalendarShifts(); // Update calendar view too
    } catch (error) {
        showMessage('shifts', `Delete failed: ${error.message}`, 'error');
    }
}

// Setup event listeners
function setupEventListeners() {
    // Tab navigation
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', async () => {
            const targetTab = tab.dataset.tab;

            // Update active tab style
            document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // Show target content
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(`content-${targetTab}`).classList.add('active');

            // Show/hide pantry selector based on tab
            const pantrySelector = document.getElementById('pantry-selector');
            if (targetTab === 'calendar') {
                pantrySelector.style.display = 'none';
            } else {
                pantrySelector.style.display = 'block';
            }

            // Load tab-specific data
            if (targetTab === 'shifts') {
                await loadShiftsTable();
            }
        });
    });

    // Pantry selection
    document.getElementById('pantry-select').addEventListener('change', async (e) => {
        currentPantryId = parseInt(e.target.value);
        await loadCalendarShifts();
        if (currentUser.roles.includes('ADMIN') || currentUser.roles.includes('PANTRY_LEAD')) {
            await loadShiftsTable();
        }
    });

    // Create pantry form
    document.getElementById('create-pantry-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = {
            name: formData.get('name'),
            location_address: formData.get('location_address')
        };

        try {
            await createPantry(data);
            showMessage('pantry', 'Pantry created successfully!', 'success');
            e.target.reset();
            await loadPantries();
        } catch (error) {
            showMessage('pantry', `Error: ${error.message}`, 'error');
        }
    });

    // Assign lead
    document.getElementById('assign-lead-btn').addEventListener('click', async () => {
        const pantryId = parseInt(document.getElementById('assign-pantry').value);
        const leadId = parseInt(document.getElementById('assign-lead').value);

        if (!pantryId || !leadId) {
            showMessage('assign', 'Please select both pantry and lead', 'error');
            return;
        }

        try {
            await addPantryLead(pantryId, leadId);
            showMessage('assign', 'Lead assigned successfully!', 'success');
            await loadPantries();
        } catch (error) {
            showMessage('assign', `Error: ${error.message}`, 'error');
        }
    });

    // Remove lead
    document.getElementById('remove-lead-btn').addEventListener('click', async () => {
        const pantryId = parseInt(document.getElementById('assign-pantry').value);
        const leadId = parseInt(document.getElementById('assign-lead').value);

        if (!pantryId || !leadId) {
            showMessage('assign', 'Please select both pantry and lead', 'error');
            return;
        }

        if (!confirm('Remove this lead from the pantry?')) return;

        try {
            await removePantryLead(pantryId, leadId);
            showMessage('assign', 'Lead removed successfully!', 'success');
            await loadPantries();
        } catch (error) {
            showMessage('assign', `Error: ${error.message}`, 'error');
        }
    });

    // Add role button
    document.getElementById('add-role-btn').addEventListener('click', () => {
        const container = document.getElementById('roles-container');
        const roleGroup = document.createElement('div');
        roleGroup.className = 'role-input-group';
        roleGroup.style.marginTop = '1rem';
        roleGroup.innerHTML = `
                    <div class="form-grid">
                        <div class="form-group">
                            <label>Role Title *</label>
                            <input type="text" class="role-title" placeholder="e.g., Food Sorter" required>
                        </div>
                        <div class="form-group">
                            <label>Required Count *</label>
                            <input type="number" class="role-count" min="1" value="1" required>
                        </div>
                        <div class="form-group" style="display: flex; align-items: flex-end;">
                            <button type="button" class="btn btn-danger" onclick="this.closest('.role-input-group').remove()" style="width: 100%;">Remove</button>
                        </div>
                    </div>
                `;
        container.appendChild(roleGroup);
    });

    // Create shift form
    document.getElementById('create-shift-form').addEventListener('submit', async (e) => {
        e.preventDefault();

        if (!currentPantryId) {
            showMessage('shifts', 'Please select a pantry first', 'error');
            return;
        }

        const formData = new FormData(e.target);
        const shiftData = {
            shift_name: formData.get('shift_name'),
            start_time: new Date(formData.get('start_time')).toISOString(),
            end_time: new Date(formData.get('end_time')).toISOString()
        };

        // Collect roles
        const roleTitles = document.querySelectorAll('.role-title');
        const roleCounts = document.querySelectorAll('.role-count');
        const roles = [];

        for (let i = 0; i < roleTitles.length; i++) {
            const title = roleTitles[i].value.trim();
            const count = parseInt(roleCounts[i].value);
            if (title && count > 0) {
                roles.push({ role_title: title, required_count: count });
            }
        }

        if (roles.length === 0) {
            showMessage('shifts', 'Please add at least one role', 'error');
            return;
        }

        try {
            // Create shift
            const shift = await createShift(currentPantryId, shiftData);

            // Create roles
            for (const role of roles) {
                await createShiftRole(shift.shift_id, role);
            }

            showMessage('shifts', 'Shift created successfully with all roles!', 'success');
            e.target.reset();

            // Reset roles container to single role
            document.getElementById('roles-container').innerHTML = `
                        <div class="role-input-group">
                            <div class="form-grid">
                                <div class="form-group">
                                    <label>Role Title *</label>
                                    <input type="text" class="role-title" placeholder="e.g., Greeter" required>
                                </div>
                                <div class="form-group">
                                    <label>Required Count *</label>
                                    <input type="number" class="role-count" min="1" value="1" required>
                                </div>
                            </div>
                        </div>
                    `;

            await loadShiftsTable();
            await loadCalendarShifts();
        } catch (error) {
            showMessage('shifts', `Error: ${error.message}`, 'error');
        }
    });
}

// Show message helper
function showMessage(target, text, type = 'info') {
    const messageEl = document.getElementById(`message-${target}`);
    if (!messageEl) return;

    messageEl.className = `message message-${type} show`;
    messageEl.textContent = text;

    setTimeout(() => {
        messageEl.classList.remove('show');
    }, 5000);
}

// Make functions globally available
window.signupForRole = signupForRole;
window.deleteShiftConfirm = deleteShiftConfirm;