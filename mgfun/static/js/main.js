/* MG FUN — main.js */

// ── Navigation toggles ───────────────────────────────────────────
function toggleUserMenu() {
  document.getElementById('userDropdown').classList.toggle('open');
}
function toggleMobileNav() {
  document.getElementById('mobileNav').classList.toggle('open');
}
// Close dropdown on outside click
document.addEventListener('click', e => {
  const menu = document.getElementById('navUserMenu');
  if (menu && !menu.contains(e.target)) {
    const dd = document.getElementById('userDropdown');
    if (dd) dd.classList.remove('open');
  }
});

// ── Password toggle ──────────────────────────────────────────────
function togglePassword(inputId, btn) {
  const input = document.getElementById(inputId);
  if (!input) return;
  if (input.type === 'password') {
    input.type = 'text';
    btn.textContent = 'Hide';
  } else {
    input.type = 'password';
    btn.textContent = 'Show';
  }
}

// ── Search suggestions ───────────────────────────────────────────
(function initSearchSuggestions() {
  const input = document.getElementById('navSearchInput');
  const box   = document.getElementById('searchSuggestions');
  if (!input || !box) return;

  let timer;
  input.addEventListener('input', () => {
    clearTimeout(timer);
    const q = input.value.trim();
    if (q.length < 2) { box.style.display = 'none'; return; }
    timer = setTimeout(async () => {
      try {
        const r = await fetch(`/search/suggestions?q=${encodeURIComponent(q)}`);
        const data = await r.json();
        if (!data.length) { box.style.display = 'none'; return; }
        box.innerHTML = data.map(item =>
          `<div class="suggestion-item" onclick="window.location='/watch/${item.id}'">
             <span>${escapeHtml(item.title)}</span>
             <span style="margin-left:auto;font-size:11px;color:var(--text-dim)">${item.type}</span>
           </div>`
        ).join('');
        box.style.display = 'block';
      } catch {}
    }, 250);
  });

  document.addEventListener('click', e => {
    if (!input.contains(e.target) && !box.contains(e.target)) {
      box.style.display = 'none';
    }
  });
})();

// ── Flash auto-dismiss ───────────────────────────────────────────
setTimeout(() => {
  document.querySelectorAll('.flash').forEach(el => {
    el.style.transition = 'opacity .5s';
    el.style.opacity = '0';
    setTimeout(() => el.remove(), 500);
  });
}, 4000);

// ── Utility ─────────────────────────────────────────────────────
function escapeHtml(str) {
  return String(str)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;');
}
