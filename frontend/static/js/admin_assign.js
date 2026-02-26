(function () {
  const leadSelect = document.getElementById('lead-select');
  const pantrySelect = document.getElementById('pantry-select-admin');
  const tableBody = document.querySelector('#assign-table tbody');
  const assignBtn = document.getElementById('assign-btn');
  const clearBtn = document.getElementById('clear-lead-btn');
  const messageEl = document.getElementById('assign-message');

  const qs = window.location.search;
  function withUserQuery(path) {
    if (!qs || qs === '?') return path;
    const hasQuery = path.indexOf('?') !== -1;
    const qp = qs.replace(/^\?/, '');
    return path + (hasQuery ? '&' : '?') + qp;
  }

  async function api(path, options) {
    const res = await fetch(withUserQuery(path), {
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      ...(options || {}),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || res.statusText);
    }
    if (res.status === 204) return null;
    return res.json();
  }

  async function loadLeads() {
    const users = await api('/api/users?role=PANTRY_LEAD');
    if (!leadSelect) return;
    leadSelect.innerHTML = '';
    users.forEach(function (u) {
      const opt = document.createElement('option');
      opt.value = String(u.id);
      opt.textContent = u.email;
      leadSelect.appendChild(opt);
    });
  }

  async function loadPantries() {
    // For SUPER_ADMIN, /api/pantries returns all
    const pantries = await api('/api/pantries');
    if (!pantrySelect) return;
    pantrySelect.innerHTML = '';
    pantries.forEach(function (p) {
      const opt = document.createElement('option');
      opt.value = String(p.id);
      opt.textContent = p.name;
      pantrySelect.appendChild(opt);
    });
  }

  async function loadTable() {
    const pantries = await api('/api/pantries');
    const leads = await api('/api/users?role=PANTRY_LEAD');
    const leadById = {};
    leads.forEach(function (u) {
      leadById[u.id] = u;
    });
    if (!tableBody) return;
    tableBody.innerHTML = '';
    pantries.forEach(function (p) {
      const tr = document.createElement('tr');
      const tdName = document.createElement('td');
      const tdSlug = document.createElement('td');
      const tdLead = document.createElement('td');
      tdName.textContent = p.name;
      tdSlug.textContent = p.slug;
      const lead = p.lead_id != null ? leadById[p.lead_id] : null;
      tdLead.textContent = lead ? lead.email : '—';
      tr.appendChild(tdName);
      tr.appendChild(tdSlug);
      tr.appendChild(tdLead);
      tableBody.appendChild(tr);
    });
  }

  async function assignLead(clear) {
    if (!pantrySelect) return;
    const pantryId = pantrySelect.value ? parseInt(pantrySelect.value, 10) : null;
    const leadId = clear ? null : (leadSelect && leadSelect.value ? parseInt(leadSelect.value, 10) : null);
    if (!pantryId) {
      messageEl.textContent = 'Select a pantry.';
      return;
    }
    try {
      messageEl.textContent = 'Saving…';
      await api('/api/pantries/' + pantryId, {
        method: 'PATCH',
        body: JSON.stringify({ lead_id: leadId }),
      });
      messageEl.textContent = clear ? 'Lead cleared.' : 'Lead assigned.';
      await loadTable();
    } catch (e) {
      messageEl.textContent = 'Error: ' + (e && e.message ? e.message : 'Unable to assign');
    }
  }

  function attachEvents() {
    if (assignBtn) {
      assignBtn.addEventListener('click', function () {
        assignLead(false);
      });
    }
    if (clearBtn) {
      clearBtn.addEventListener('click', function () {
        assignLead(true);
      });
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    Promise.all([loadLeads(), loadPantries(), loadTable()]).catch(function (e) {
      if (messageEl) messageEl.textContent = 'Error loading data.';
      console.error(e);
    });
    attachEvents();
  });
})();
