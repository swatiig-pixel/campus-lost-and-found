// Campus Lost & Found — Main JS

document.addEventListener('DOMContentLoaded', function () {

  // ── Auto-dismiss alerts after 4s ─────────────────────────
  const alerts = document.querySelectorAll('.alert-dismissible');
  alerts.forEach(alert => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 4000);
  });

  // ── Active nav link highlight ──────────────────────────────
  const currentPath = window.location.pathname;
  document.querySelectorAll('.sidebar-nav .nav-link, .navbar-campus .nav-link').forEach(link => {
    if (link.getAttribute('href') === currentPath ||
        (link.getAttribute('href') !== '/' && currentPath.startsWith(link.getAttribute('href')))) {
      link.classList.add('active');
    }
  });

  // ── Image preview on file input ───────────────────────────
  const imageInput = document.getElementById('id_image');
  const previewEl  = document.getElementById('image-preview');
  if (imageInput && previewEl) {
    imageInput.addEventListener('change', function () {
      const file = this.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = e => {
          previewEl.src = e.target.result;
          previewEl.style.display = 'block';
        };
        reader.readAsDataURL(file);
      }
    });
  }

  // ── Confirm dangerous actions ──────────────────────────────
  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', function (e) {
      if (!confirm(this.dataset.confirm || 'Are you sure?')) {
        e.preventDefault();
      }
    });
  });

  // ── Scroll chat to bottom ──────────────────────────────────
  const chatMessages = document.querySelector('.chat-messages');
  if (chatMessages) {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  // ── Search form: prevent empty submit ─────────────────────
  const searchForm = document.querySelector('.search-form');
  if (searchForm) {
    searchForm.addEventListener('submit', function (e) {
      // Remove empty params from URL
      const inputs = this.querySelectorAll('input, select');
      inputs.forEach(input => {
        if (!input.value) input.disabled = true;
      });
    });
  }

  // ── Tooltips initialization ────────────────────────────────
  const tooltipEls = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltipEls.forEach(el => new bootstrap.Tooltip(el));

  // ── Notification count badge ───────────────────────────────
  const notifBadge = document.getElementById('notif-count');
  if (notifBadge) {
    // Live polling every 60 seconds
    setInterval(() => {
      fetch('/notifications/?format=json', { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(r => r.ok ? r.json() : null)
        .then(data => {
          if (data && data.unread_count !== undefined) {
            notifBadge.textContent = data.unread_count || '';
            notifBadge.style.display = data.unread_count > 0 ? 'flex' : 'none';
          }
        })
        .catch(() => {});
    }, 60000);
  }

});
