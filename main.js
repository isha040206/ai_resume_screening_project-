// ResumeAI — Main JavaScript

document.addEventListener('DOMContentLoaded', function () {

  // ── Sidebar Toggle ──
  const toggle = document.getElementById('sidebarToggle');
  const sidebar = document.getElementById('sidebar');
  const mainContent = document.querySelector('.main-content');

  if (toggle && sidebar) {
    toggle.addEventListener('click', function () {
      if (window.innerWidth <= 768) {
        sidebar.classList.toggle('open');
      } else {
        sidebar.classList.toggle('collapsed');
        if (sidebar.classList.contains('collapsed')) {
          mainContent.style.marginLeft = '0';
          sidebar.style.transform = 'translateX(-100%)';
        } else {
          mainContent.style.marginLeft = 'var(--sidebar-w)';
          sidebar.style.transform = 'translateX(0)';
        }
      }
    });
  }

  // ── Auto dismiss alerts after 4 seconds ──
  document.querySelectorAll('.alert').forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 4500);
  });

  // ── Animate score bars on page load ──
  document.querySelectorAll('.score-bar-fill').forEach(function (bar) {
    const targetWidth = bar.style.width;
    bar.style.width = '0%';
    setTimeout(function () {
      bar.style.width = targetWidth;
    }, 300);
  });

  // ── Confirm delete actions ──
  document.querySelectorAll('[data-confirm]').forEach(function (el) {
    el.addEventListener('click', function (e) {
      if (!confirm(this.dataset.confirm || 'Are you sure?')) {
        e.preventDefault();
      }
    });
  });

  // ── File input label update ──
  document.querySelectorAll('input[type="file"]').forEach(function (input) {
    input.addEventListener('change', function () {
      const label = this.closest('.mb-3')?.querySelector('.form-text');
      if (label && this.files.length > 0) {
        label.textContent = '✓ Selected: ' + this.files[0].name;
        label.style.color = '#16a34a';
      }
    });
  });

  // ── Animate stat counters ──
  document.querySelectorAll('.stat-value').forEach(function (el) {
    const target = parseFloat(el.textContent.replace(/[^\d.]/g, ''));
    if (!isNaN(target) && target > 0) {
      let start = 0;
      const duration = 800;
      const step = target / (duration / 16);
      const suffix = el.textContent.includes('%') ? '%' : '';
      const isDecimal = el.textContent.includes('.');

      const timer = setInterval(function () {
        start += step;
        if (start >= target) {
          start = target;
          clearInterval(timer);
        }
        el.textContent = (isDecimal ? start.toFixed(1) : Math.floor(start)) + suffix;
      }, 16);
    }
  });

});
