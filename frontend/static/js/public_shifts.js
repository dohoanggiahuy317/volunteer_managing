(function () {
  const listEl = document.getElementById('public-shifts-list');
  if (!listEl) return;
  const slug = listEl.getAttribute('data-slug');
  const qs = window.location.search;
  function withUserQuery(path) {
    if (!qs || qs === '?') return path;
    const hasQuery = path.indexOf('?') !== -1;
    const qp = qs.replace(/^\?/, '');
    return path + (hasQuery ? '&' : '?') + qp;
  }

  async function api(path) {
    const res = await fetch(withUserQuery(path), { credentials: 'same-origin' });
    if (!res.ok) {
      throw new Error(await res.text());
    }
    return res.json();
  }

  function formatRange(startIso, endIso) {
    const start = new Date(startIso);
    const end = new Date(endIso);
    const datePart = start.toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
    });
    const startTime = start.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
    const endTime = end.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
    return datePart + ' ' + startTime + ' – ' + endTime;
  }

  async function loadShifts() {
    if (!slug) return;
    try {
      const shifts = await api('/api/public/pantries/' + encodeURIComponent(slug) + '/shifts');
      listEl.innerHTML = '';
      if (!shifts.length) {
        const li = document.createElement('li');
        li.textContent = 'No shifts available.';
        listEl.appendChild(li);
        return;
      }
      shifts.forEach(function (s) {
        const li = document.createElement('li');
        li.className = 'shift-item';
        const role = document.createElement('div');
        role.className = 'shift-role';
        role.textContent = s.role_name;
        const time = document.createElement('div');
        time.className = 'shift-time';
        time.textContent = formatRange(s.start_time, s.end_time);
        const meta = document.createElement('div');
        meta.className = 'shift-meta';
        meta.textContent = s.filled_count + ' / ' + s.required_count + ' volunteers · ' + s.status;
        li.appendChild(role);
        li.appendChild(time);
        li.appendChild(meta);
        listEl.appendChild(li);
      });
    } catch (e) {
      listEl.innerHTML = '';
      const li = document.createElement('li');
      li.textContent = 'Error loading shifts.';
      listEl.appendChild(li);
    }
  }

  document.addEventListener('DOMContentLoaded', loadShifts);
})();
