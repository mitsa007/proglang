document.addEventListener('DOMContentLoaded', function () {

  /* ============================================================
     DARK MODE (persisted in localStorage)
  ============================================================ */
  const html = document.documentElement;
  if (localStorage.getItem('darkMode') === 'true') html.classList.add('dark');

  const darkBtn = document.getElementById('dark-mode-btn');
  darkBtn && darkBtn.addEventListener('click', function () {
    html.classList.toggle('dark');
    localStorage.setItem('darkMode', html.classList.contains('dark'));
  });

  /* ============================================================
     MOBILE SIDEBAR
  ============================================================ */
  const menuToggle = document.getElementById('menu-toggle');
  const sidebar    = document.getElementById('sidebar');
  const overlay    = document.getElementById('sidebar-overlay');

  function openSidebar()  { sidebar?.classList.add('open');    overlay?.classList.add('visible'); }
  function closeSidebar() { sidebar?.classList.remove('open'); overlay?.classList.remove('visible'); }

  menuToggle?.addEventListener('click', () =>
    sidebar?.classList.contains('open') ? closeSidebar() : openSidebar());
  overlay?.addEventListener('click', closeSidebar);

  /* ============================================================
     AVATAR DROPDOWN
  ============================================================ */
  const avatarBtn = document.getElementById('avatar-btn');
  const dropMenu  = document.getElementById('dropdown-menu');

  avatarBtn && dropMenu && avatarBtn.addEventListener('click', function (e) {
    e.stopPropagation();
    dropMenu.classList.toggle('open');
  });

  document.addEventListener('click', function () {
    dropMenu?.classList.remove('open');
  });

  dropMenu?.addEventListener('click', e => e.stopPropagation());

  /* ============================================================
     GOAL OPTION SELECTION (onboarding)
  ============================================================ */
  const goalOptions = document.querySelectorAll('.goal-option');
  const goalInput   = document.getElementById('goal');

  goalOptions.forEach(opt => {
    opt.addEventListener('click', function () {
      goalOptions.forEach(o => o.classList.remove('active'));
      this.classList.add('active');
      if (goalInput) goalInput.value = this.dataset.goal;
    });
  });

  /* ============================================================
     INTENSITY TOGGLE (workout form)
  ============================================================ */
  const intensityBtns = document.querySelectorAll('.intensity-btn');
  const intensityVal  = document.getElementById('intensity-val');

  intensityBtns.forEach(btn => {
    btn.addEventListener('click', function () {
      intensityBtns.forEach(b => b.classList.remove('active'));
      this.classList.add('active');
      if (intensityVal) intensityVal.value = this.dataset.val;
    });
  });

  /* ============================================================
     EDIT / DONE TOGGLE (workout list)
  ============================================================ */
  function setupEditToggle(btnId, listId) {
    const btn  = document.getElementById(btnId);
    const list = document.getElementById(listId);
    if (!btn || !list) return;

    btn.addEventListener('click', function () {
      const isEdit = list.classList.toggle('edit-mode');
      this.textContent = isEdit ? 'Done' : 'Edit';
    });
  }

  setupEditToggle('edit-workout-btn', 'workout-list');
  setupEditToggle('edit-meal-btn',    'meal-list');
  setupEditToggle('edit-weight-btn',  'weight-list');

  /* ============================================================
     CHART.JS — palette
  ============================================================ */
  const BROWN       = '#7c5238';
  const LIGHT_BROWN = '#b8956a';
  const TAN         = '#d9c8b4';
  const SAND        = '#f0e9df';
  const DARK_BROWN  = '#4a2f1a';
  const LABEL_COLOR = '#7a6652';
  const GRID_COLOR  = '#e0d3c0';

  if (window.Chart) {
    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.font.size   = 12;
    Chart.defaults.color       = LABEL_COLOR;
  }

  const tooltipDefaults = {
    backgroundColor: DARK_BROWN,
    titleColor: '#fff',
    bodyColor: TAN,
    padding: 10,
    cornerRadius: 8,
  };

  /* ---- Weekly Activity chart (overview) ---- */
  const weeklyCtx = document.getElementById('weeklyActivityChart');
  if (weeklyCtx) {
    const rawLabels = JSON.parse(weeklyCtx.dataset.labels   || '["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]');
    const rawCals   = JSON.parse(weeklyCtx.dataset.calories || '[0,0,0,0,0,0,0]');

    // Colour each bar proportionally: low cal → sand, high cal → dark brown
    const maxCal = Math.max(...rawCals, 1);
    const palette = [SAND, TAN, LIGHT_BROWN, BROWN, DARK_BROWN];
    const barColors = rawCals.map(v => {
      const idx = Math.min(Math.floor((v / maxCal) * (palette.length - 1)), palette.length - 1);
      return palette[idx];
    });

    new Chart(weeklyCtx, {
      type: 'bar',
      data: {
        labels: rawLabels,
        datasets: [{
          label: 'Calories Burned (kcal)',
          data: rawCals,
          backgroundColor: barColors,
          borderRadius: 6,
          borderSkipped: false,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            ...tooltipDefaults,
            callbacks: {
              label: ctx => ` ${ctx.parsed.y} kcal`,
            }
          }
        },
        scales: {
          x: { grid: { display: false }, ticks: { color: LABEL_COLOR } },
          y: {
            grid: { color: GRID_COLOR },
            ticks: { color: LABEL_COLOR },
            beginAtZero: true,
            title: { display: true, text: 'kcal', color: LABEL_COLOR, font: { size: 11 } },
          }
        }
      }
    });
  }

  /* ---- Weight Progress chart (progress page) ---- */
  const weightCtx = document.getElementById('weightChart');
  if (weightCtx) {
    const rawLabels  = JSON.parse(weightCtx.dataset.labels  || '[]');
    const rawWeights = JSON.parse(weightCtx.dataset.weights || '[]');

    new Chart(weightCtx, {
      type: 'line',
      data: {
        labels: rawLabels,
        datasets: [{
          label: 'Weight (kg)',
          data: rawWeights,
          borderColor: BROWN,
          backgroundColor(ctx) {
            const { chartArea, ctx: c } = ctx.chart;
            if (!chartArea) return 'transparent';
            const g = c.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
            g.addColorStop(0, 'rgba(124,82,56,.25)');
            g.addColorStop(1, 'rgba(124,82,56,0)');
            return g;
          },
          borderWidth: 2.5, fill: true, tension: 0.4,
          pointBackgroundColor: BROWN, pointBorderColor: '#fff',
          pointBorderWidth: 2, pointRadius: 5, pointHoverRadius: 7,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: tooltipDefaults },
        scales: {
          x: { grid: { display: false }, ticks: { color: LABEL_COLOR } },
          y: { grid: { color: GRID_COLOR }, ticks: { color: LABEL_COLOR } }
        }
      }
    });
  }

  /* ============================================================
     MICRO ANIMATION — button press feedback
  ============================================================ */
  document.querySelectorAll('.btn').forEach(btn => {
    btn.addEventListener('click', function () {
      this.style.transform = 'scale(0.97)';
      setTimeout(() => { this.style.transform = ''; }, 150);
    });
  });

});
