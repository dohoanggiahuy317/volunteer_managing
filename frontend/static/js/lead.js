(function () {
  const pantrySelect = document.getElementById('pantry-select');
  const userEmailEl = document.querySelector('[data-user-email]');
  const weekGrid = document.getElementById('week-grid');
  const calendarTitle = document.getElementById('calendar-title');
  const prevWeekBtn = document.getElementById('prev-week-btn');
  const nextWeekBtn = document.getElementById('next-week-btn');
  const todayBtn = document.getElementById('today-btn');
  const openCreateBtn = document.getElementById('open-create-btn');
  const cancelCreateBtn = document.getElementById('cancel-create-btn');
  const createPanel = document.getElementById('create-panel');
  const createForm = document.getElementById('create-shift-form');
  const createMessage = document.getElementById('create-message');

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

  function getWeekStart(d) {
    const date = new Date(d);
    const day = date.getDay();
    const diff = date.getDate() - day + (day === 0 ? -6 : 1);
    date.setDate(diff);
    date.setHours(0, 0, 0, 0);
    return date;
  }

  function toDateString(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return y + '-' + m + '-' + day;
  }

  function isoToDateString(iso) {
    return toDateString(new Date(iso));
  }

  function formatDayHeader(d) {
    return d.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
    });
  }

  function formatTime(iso) {
    return new Date(iso).toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  }

  let currentWeekStart = getWeekStart(new Date());
  let currentPantryId = null;
  let currentPantries = [];

  async function loadUser() {
    try {
      const user = await api('/api/me');
      if (userEmailEl) userEmailEl.textContent = user.email || '—';
    } catch (e) {
      if (userEmailEl) userEmailEl.textContent = 'Unable to load user';
    }
  }

  async function loadPantries() {
    const pantries = await api('/api/pantries');
    currentPantries = pantries || [];
    if (!pantrySelect) return;
    pantrySelect.innerHTML = '';
    if (!currentPantries.length) {
      const opt = document.createElement('option');
      opt.value = '';
      opt.textContent = 'No pantries';
      pantrySelect.appendChild(opt);
      currentPantryId = null;
      renderWeek([]);
      return;
    }
    currentPantries.forEach(function (p) {
      const opt = document.createElement('option');
      opt.value = String(p.id);
      opt.textContent = p.name;
      pantrySelect.appendChild(opt);
    });
    if (!currentPantryId || !currentPantries.some(function (p) { return p.id === currentPantryId; })) {
      currentPantryId = currentPantries[0].id;
    }
    pantrySelect.value = String(currentPantryId);
    updateCalendarTitle();
    await loadShifts();
  }

  function updateCalendarTitle() {
    if (!calendarTitle) return;
    var pantry = currentPantries.find(function (p) { return p.id === currentPantryId; });
    const start = currentWeekStart;
    const end = new Date(start);
    end.setDate(end.getDate() + 6);
    const range =
      start.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) +
      ' – ' +
      end.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    calendarTitle.textContent = (pantry ? pantry.name + ' — ' : '') + 'Week of ' + range;
  }

  async function loadShifts() {
    if (!currentPantryId || !weekGrid) return;
    const shifts = await api('/api/pantries/' + currentPantryId + '/shifts');
    renderWeek(shifts || []);
  }

  function renderWeek(shifts) {
    if (!weekGrid) return;
    weekGrid.innerHTML = '';
    const days = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date(currentWeekStart);
      d.setDate(currentWeekStart.getDate() + i);
      days.push(d);
    }
    const byDay = {};
    days.forEach(function (d) {
      const key = toDateString(d);
      byDay[key] = [];
    });
    (shifts || []).forEach(function (s) {
      const key = isoToDateString(s.start_time);
      if (!byDay[key]) byDay[key] = [];
      byDay[key].push(s);
    });
    Object.keys(byDay).forEach(function (k) {
      byDay[k].sort(function (a, b) {
        return new Date(a.start_time) - new Date(b.start_time);
      });
    });
    days.forEach(function (d) {
      const key = toDateString(d);
      const col = document.createElement('div');
      col.className = 'day-column';
      const header = document.createElement('div');
      header.className = 'day-header';
      header.textContent = formatDayHeader(d);
      col.appendChild(header);
      const list = document.createElement('div');
      list.className = 'day-list';
      const dayShifts = byDay[key] || [];
      if (!dayShifts.length) {
        const p = document.createElement('p');
        p.className = 'day-empty';
        p.textContent = 'No shifts';
        list.appendChild(p);
      } else {
        dayShifts.forEach(function (s) {
          const card = document.createElement('div');
          card.className = 'shift-card';
          const role = document.createElement('div');
          role.className = 'shift-role';
          role.textContent = s.role_name;
          const time = document.createElement('div');
          time.className = 'shift-time';
          time.textContent = formatTime(s.start_time) + ' – ' + formatTime(s.end_time);
          const meta = document.createElement('div');
          meta.className = 'shift-meta';
          meta.textContent = s.filled_count + ' / ' + s.required_count + ' · ' + s.status;
          card.appendChild(role);
          card.appendChild(time);
          card.appendChild(meta);
          list.appendChild(card);
        });
      }
      col.appendChild(list);
      weekGrid.appendChild(col);
    });
  }

  function openCreatePanel() {
    if (createPanel) createPanel.hidden = false;
  }

  function closeCreatePanel() {
    if (createPanel) createPanel.hidden = true;
    if (createForm) createForm.reset();
    clearErrors();
    if (createMessage) createMessage.textContent = '';
  }

  function clearErrors() {
    document.querySelectorAll('.form-error[data-error-for]').forEach(function (el) {
      el.textContent = '';
    });
  }

  function setError(field, message) {
    const el = document.querySelector('.form-error[data-error-for="' + field + '"]');
    if (el) el.textContent = message || '';
  }

  function validateForm() {
    clearErrors();
    let ok = true;
    const role = document.getElementById('role-input');
    const start = document.getElementById('start-input');
    const end = document.getElementById('end-input');
    const req = document.getElementById('required-input');
    if (!currentPantryId) {
      ok = false;
      if (createMessage) createMessage.textContent = 'Select a pantry first.';
    }
    if (!role.value.trim()) {
      setError('role_name', 'Role / Title is required');
      ok = false;
    }
    if (!start.value) {
      setError('start_time', 'Start time is required');
      ok = false;
    }
    if (!end.value) {
      setError('end_time', 'End time is required');
      ok = false;
    }
    if (start.value && end.value && new Date(end.value) <= new Date(start.value)) {
      setError('end_time', 'End time must be after start time');
      ok = false;
    }
    const rc = parseInt(req.value, 10);
    if (!Number.isInteger(rc) || rc < 1) {
      setError('required_count', 'Required count must be a positive integer');
      ok = false;
    }
    return ok;
  }

  async function handleCreateSubmit(evt) {
    evt.preventDefault();
    if (!validateForm() || !currentPantryId) return;
    const role = document.getElementById('role-input');
    const start = document.getElementById('start-input');
    const end = document.getElementById('end-input');
    const req = document.getElementById('required-input');
    const body = {
      role_name: role.value.trim(),
      start_time: new Date(start.value).toISOString(),
      end_time: new Date(end.value).toISOString(),
      required_count: parseInt(req.value, 10),
    };
    try {
      if (createMessage) {
        createMessage.textContent = 'Creating…';
      }
      await api('/api/pantries/' + currentPantryId + '/shifts', {
        method: 'POST',
        body: JSON.stringify(body),
      });
      if (createMessage) {
        createMessage.textContent = 'Shift created. Reloading calendar…';
      }
      await loadShifts();
      setTimeout(closeCreatePanel, 800);
    } catch (e) {
      if (createMessage) {
        createMessage.textContent = 'Error: ' + (e && e.message ? e.message : 'Unable to create shift');
      }
    }
  }

  function attachEvents() {
    if (pantrySelect) {
      pantrySelect.addEventListener('change', function () {
        const val = pantrySelect.value;
        currentPantryId = val ? parseInt(val, 10) : null;
        updateCalendarTitle();
        loadShifts();
      });
    }
    if (prevWeekBtn) {
      prevWeekBtn.addEventListener('click', function () {
        currentWeekStart.setDate(currentWeekStart.getDate() - 7);
        updateCalendarTitle();
        loadShifts();
      });
    }
    if (nextWeekBtn) {
      nextWeekBtn.addEventListener('click', function () {
        currentWeekStart.setDate(currentWeekStart.getDate() + 7);
        updateCalendarTitle();
        loadShifts();
      });
    }
    if (todayBtn) {
      todayBtn.addEventListener('click', function () {
        currentWeekStart = getWeekStart(new Date());
        updateCalendarTitle();
        loadShifts();
      });
    }
    if (openCreateBtn) {
      openCreateBtn.addEventListener('click', openCreatePanel);
    }
    if (cancelCreateBtn) {
      cancelCreateBtn.addEventListener('click', closeCreatePanel);
    }
    if (createForm) {
      createForm.addEventListener('submit', handleCreateSubmit);
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadUser();
    loadPantries();
    attachEvents();
  });
})();
