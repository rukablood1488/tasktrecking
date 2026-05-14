'use strict';

/* ════════════════════════════════════════════════════════════════
   TaskFlow — main.js
   Завантажується на кожній сторінці через base.html
   Модулі: Utils · Sidebar · Dropdown · Tabs · Flash ·
           StatusForms · ArchiveForms · Tooltips ·
           AutoResize · FilterSubmit · ProjectPreview · Animations
════════════════════════════════════════════════════════════════ */

// ──────────────────────────────────────────────────────────────
//  UTILS
// ──────────────────────────────────────────────────────────────

const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

// CSRF токен — Django вимагає його у кожному POST
function getCsrf() {
  return document.cookie
    .split('; ')
    .find(r => r.startsWith('csrftoken='))
    ?.split('=')[1] ?? '';
}

// Обгортка над fetch: завжди POST + CSRF + JSON у відповідь
async function apiFetch(url, data = {}) {
  const body = new URLSearchParams({ csrfmiddlewaretoken: getCsrf(), ...data });
  const res  = await fetch(url, {
    method:  'POST',
    headers: {
      'Content-Type':     'application/x-www-form-urlencoded',
      'X-Requested-With': 'XMLHttpRequest',
      'X-CSRFToken':      getCsrf(),
    },
    body,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// Spring-анімація через Web Animations API
// from/to — об'єкти з CSS-властивостями
function springIn(el, from, to, duration = 280) {
  return el.animate(
    [
      { ...from, easing: 'cubic-bezier(0.34, 1.56, 0.64, 1)' },
      to,
    ],
    { duration, fill: 'forwards' }
  );
}

// Stagger — запускає колбек для кожного елемента із затримкою
function stagger(els, cb, delay = 40) {
  els.forEach((el, i) => setTimeout(() => cb(el, i), i * delay));
}

// ──────────────────────────────────────────────────────────────
//  FLASH ПОВІДОМЛЕННЯ
// ──────────────────────────────────────────────────────────────

function showFlash(message, type = 'success') {
  let container = $('.messages-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'messages-container';
    $('.main-wrapper')?.prepend(container);
  }

  const alert = document.createElement('div');
  alert.className = `alert alert--${type}`;
  alert.innerHTML = `
    <span class="alert__text">${message}</span>
    <button class="alert__close" aria-label="Закрити">&#10005;</button>
  `;
  $('button', alert).onclick = () => dismissFlash(alert);
  container.prepend(alert);

  springIn(
    alert,
    { opacity: 0, transform: 'translateY(-14px) scale(0.95)' },
    { opacity: 1, transform: 'translateY(0) scale(1)' },
    320
  );

  setTimeout(() => dismissFlash(alert), 4000);
}

function dismissFlash(alert) {
  if (!alert.isConnected) return;
  const anim = alert.animate(
    [
      { opacity: 1, transform: 'translateY(0) scale(1)' },
      { opacity: 0, transform: 'translateY(-8px) scale(0.95)' },
    ],
    { duration: 200, easing: 'ease-in', fill: 'forwards' }
  );
  anim.onfinish = () => alert.remove();
}

// ──────────────────────────────────────────────────────────────
//  SIDEBAR — розгортання / згортання
// ──────────────────────────────────────────────────────────────

function initSidebar() {
  const sidebar = $('#sidebar');
  const toggle  = $('#sidebarToggle');
  const wrapper = $('.main-wrapper');
  if (!sidebar || !toggle) return;

  const KEY = 'tf_sidebar_collapsed';

  // Динамічні CSS-правила для collapsed-режиму
  const style = document.createElement('style');
  style.textContent = `
    .sidebar, .main-wrapper { transition: width 220ms cubic-bezier(.4,0,.2,1), margin-left 220ms cubic-bezier(.4,0,.2,1); }
    .sidebar--collapsed { width: 52px !important; overflow: hidden; }
    .sidebar--collapsed .sidebar__logo-text,
    .sidebar--collapsed .sidebar__workspace-title,
    .sidebar--collapsed .sidebar__nav-label,
    .sidebar--collapsed .sidebar__section-title,
    .sidebar--collapsed .sidebar__section-action,
    .sidebar--collapsed .sidebar__project-list,
    .sidebar--collapsed .sidebar__project-empty,
    .sidebar--collapsed .sidebar__user-info { display: none !important; }
    .sidebar--collapsed .sidebar__logo-link,
    .sidebar--collapsed .sidebar__nav-link,
    .sidebar--collapsed .sidebar__workspace-name,
    .sidebar--collapsed .sidebar__footer { justify-content: center; }
    .sidebar--collapsed .sidebar__nav-link { padding: 8px; }
    .main-wrapper--collapsed { margin-left: 52px !important; }
    #sidebarToggle { transition: transform 220ms ease; }
    .sidebar--collapsed #sidebarToggle { transform: rotate(180deg); }
  `;
  document.head.appendChild(style);

  function apply(collapsed) {
    sidebar.classList.toggle('sidebar--collapsed', collapsed);
    wrapper?.classList.toggle('main-wrapper--collapsed', collapsed);
    localStorage.setItem(KEY, collapsed);
  }

  apply(localStorage.getItem(KEY) === 'true');
  toggle.addEventListener('click', () => apply(!sidebar.classList.contains('sidebar--collapsed')));
}

// ──────────────────────────────────────────────────────────────
//  USER DROPDOWN (аватар у topbar)
// ──────────────────────────────────────────────────────────────

function initUserDropdown() {
  const btn      = $('#userMenuToggle');
  const dropdown = $('#userDropdown');
  if (!btn || !dropdown) return;

  function open() {
    dropdown.classList.add('is-open');
    btn.setAttribute('aria-expanded', 'true');
    springIn(
      dropdown,
      { opacity: 0, transform: 'translateY(-8px) scale(0.95)' },
      { opacity: 1, transform: 'translateY(0) scale(1)' },
      200
    );
  }

  function close() {
    if (!dropdown.classList.contains('is-open')) return;
    dropdown.animate(
      [
        { opacity: 1, transform: 'scale(1)' },
        { opacity: 0, transform: 'translateY(-6px) scale(0.95)' },
      ],
      { duration: 150, easing: 'ease-in', fill: 'forwards' }
    ).onfinish = () => {
      dropdown.classList.remove('is-open');
      btn.setAttribute('aria-expanded', 'false');
      dropdown.style.animation = '';
    };
  }

  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    dropdown.classList.contains('is-open') ? close() : open();
  });

  document.addEventListener('click', (e) => {
    if (!btn.contains(e.target)) close();
  });
}

// ──────────────────────────────────────────────────────────────
//  TABS (Workspace detail: Проекти / Учасники)
// ──────────────────────────────────────────────────────────────

function initTabs() {
  $$('.tabs').forEach(tabsEl => {
    const tabs   = $$('.tabs__tab', tabsEl);
    const panels = $$('.tab-panel');
    if (!tabs.length) return;

    function switchTab(activeTab) {
      tabs.forEach(t => t.classList.remove('tabs__tab--active'));
      activeTab.classList.add('tabs__tab--active');

      panels.forEach(panel => {
        if (panel.id === activeTab.dataset.target) {
          panel.style.display = 'block';
          panel.classList.add('tab-panel--active');
          // Stagger для дочірніх карток
          stagger(
            $$('.project-card, .workspace-card, .member-row', panel),
            (el) => springIn(
              el,
              { opacity: 0, transform: 'translateY(12px) scale(0.97)' },
              { opacity: 1, transform: 'translateY(0) scale(1)' },
              260
            )
          );
        } else {
          panel.style.display = 'none';
          panel.classList.remove('tab-panel--active');
        }
      });
    }

    tabs.forEach(tab => tab.addEventListener('click', () => switchTab(tab)));
  });
}

// ──────────────────────────────────────────────────────────────
//  VIEW TOGGLE (Дошка / Список на project-detail)
// ──────────────────────────────────────────────────────────────

function initViewToggle() {
  const btns     = $$('.view-toggle__btn');
  const board    = $('#kanbanBoard');
  const listView = $('#listView');
  if (!btns.length) return;

  const KEY   = 'tf_view_' + window.location.pathname;
  const saved = localStorage.getItem(KEY) || 'board';

  function switchView(view) {
    btns.forEach(b => b.classList.toggle('view-toggle__btn--active', b.dataset.view === view));
    localStorage.setItem(KEY, view);

    if (view === 'board') {
      listView && (listView.style.display = 'none');
      if (board) {
        board.style.display = 'flex';
        stagger($$('.kanban-col', board), (col) => {
          springIn(col, { opacity: 0, transform: 'translateY(20px)' }, { opacity: 1, transform: 'translateY(0)' }, 300);
        }, 55);
      }
    } else {
      board && (board.style.display = 'none');
      if (listView) {
        listView.style.display = 'block';
        stagger($$('.task-table__row', listView), (row) => {
          springIn(row, { opacity: 0, transform: 'translateX(-10px)' }, { opacity: 1, transform: 'translateX(0)' }, 220);
        }, 28);
      }
    }
  }

  btns.forEach(btn => btn.addEventListener('click', () => switchView(btn.dataset.view)));
  switchView(saved);
}

// ──────────────────────────────────────────────────────────────
//  AJAX — зміна статусу завдання (select на task-detail)
// ──────────────────────────────────────────────────────────────

function initStatusForms() {
  // Шукаємо всі форми зміни статусу (додай цей клас до своїх форм у шаблоні, якщо його немає)
  document.querySelectorAll('.js-status-form').forEach(form => {
    form.addEventListener('submit', async function(e) {
      e.preventDefault(); // ЦЕЙ РЯДОК ЗУПИНЯЄ "ЧОРНУ СТОРІНКУ"

      const url = this.action;
      const formData = new FormData(this);

      try {
        const response = await fetch(url, {
          method: 'POST',
          body: formData,
          headers: {
            'X-Requested-With': 'XMLHttpRequest', // Кажемо серверу, що це AJAX
            'X-CSRFToken': getCsrf()
          }
        });

        const data = await response.json();
        if (data.success) {
          // Тут можна оновити інтерфейс без перезавантаження
          // Наприклад, змінити колір бейджа або текст
          console.log('Статус оновлено:', data.status_display);
          
          // Або просто перезавантажити сторінку автоматично:
          // window.location.reload();
        }
      } catch (error) {
        console.error('Помилка:', error);
      }
    });
  });
}

// ──────────────────────────────────────────────────────────────
//  AJAX — архівація завдання
// ──────────────────────────────────────────────────────────────

function initArchiveForms() {
  $$('form[action*="/archive/"]').forEach(form => {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const btn     = $('button[type="submit"]', form);
      const restore = !!$('input[name="restore"]', form);
      const origTxt = btn.textContent.trim();

      btn.disabled    = true;
      btn.textContent = '...';

      try {
        const data = await apiFetch(form.action, restore ? { restore: '1' } : {});
        if (data.success) {
          showFlash(`Завдання ${data.is_archived ? 'архівовано' : 'розархівовано'}`);
          btn.textContent = data.is_archived ? 'Розархівувати' : 'Архівувати';
          // Оновлюємо hidden input
          let inp = $('input[name="restore"]', form);
          if (data.is_archived && !inp) {
            inp = Object.assign(document.createElement('input'), { type: 'hidden', name: 'restore', value: '1' });
            form.appendChild(inp);
          } else if (!data.is_archived && inp) {
            inp.remove();
          }
          btn.disabled = false;
        }
      } catch {
        btn.disabled    = false;
        btn.textContent = origTxt;
        showFlash('Помилка', 'error');
      }
    });
  });
}

// ──────────────────────────────────────────────────────────────
//  TOOLTIPS — власна реалізація замість нативного title
// ──────────────────────────────────────────────────────────────

function initTooltips() {
  let tip = null;

  document.addEventListener('mouseover', (e) => {
    const el = e.target.closest('[title]');
    if (!el?.title) return;

    el.dataset.tip = el.title;
    el.removeAttribute('title');

    tip = document.createElement('div');
    Object.assign(tip.style, {
      position: 'fixed', zIndex: '9999', pointerEvents: 'none',
      background: 'var(--surface-3)', color: 'var(--text-1)',
      border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)',
      padding: '4px 9px', fontSize: '0.72rem', fontFamily: "'Outfit',sans-serif",
      whiteSpace: 'nowrap', boxShadow: 'var(--shadow-md)',
    });
    tip.textContent = el.dataset.tip;
    document.body.appendChild(tip);

    const r = el.getBoundingClientRect();
    tip.style.left = r.left + r.width / 2 - tip.offsetWidth / 2 + 'px';
    tip.style.top  = r.bottom + 6 + 'px';

    springIn(tip, { opacity: 0, transform: 'translateY(5px) scale(0.92)' }, { opacity: 1, transform: 'translateY(0) scale(1)' }, 180);
  });

  document.addEventListener('mouseout', (e) => {
    const el = e.target.closest('[data-tip]');
    if (el) { el.setAttribute('title', el.dataset.tip); delete el.dataset.tip; }
    if (tip) {
      const t = tip; tip = null;
      t.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 120, fill: 'forwards' }).onfinish = () => t.remove();
    }
  });
}

// ──────────────────────────────────────────────────────────────
//  AUTO-RESIZE textarea
// ──────────────────────────────────────────────────────────────

function initAutoResize() {
  $$('textarea').forEach(ta => {
    const resize = () => { ta.style.height = 'auto'; ta.style.height = ta.scrollHeight + 'px'; };
    ta.addEventListener('input', resize);
    resize();
  });
}

// ──────────────────────────────────────────────────────────────
//  FILTER BAR — автосабміт при зміні select
// ──────────────────────────────────────────────────────────────

function initFilterAutoSubmit() {
  const form = $('.filter-bar');
  if (!form) return;
  $$('select', form).forEach(sel => sel.addEventListener('change', () => form.submit()));
}

// ──────────────────────────────────────────────────────────────
//  PROJECT FORM — live preview
// ──────────────────────────────────────────────────────────────

function initProjectPreview() {
  const previewCard = $('.project-preview__card');
  if (!previewCard) return;

  const nameInput   = $('input[name="name"]');
  const iconInput   = $('input[name="icon"]');
  const colorSelect = $('select[name="color"]');
  const previewName = $('#previewName');
  const previewIcon = $('#previewIcon');

  function update() {
    if (previewName && nameInput)
      previewName.textContent = nameInput.value.trim() || 'Назва проекту';
    if (previewIcon && iconInput)
      previewIcon.textContent = iconInput.value.trim() || '📁';
    if (colorSelect)
      previewCard.style.borderLeftColor = colorSelect.value;

    previewCard.animate(
      [{ transform: 'scale(1.04)' }, { transform: 'scale(1)' }],
      { duration: 200, easing: 'cubic-bezier(0.34,1.56,0.64,1)' }
    );
  }

  nameInput?.addEventListener('input', update);
  iconInput?.addEventListener('input', update);
  colorSelect?.addEventListener('change', update);
}

// ──────────────────────────────────────────────────────────────
//  QUICK CREATE BUTTON (topbar)
// ──────────────────────────────────────────────────────────────

function initQuickCreate() {
  const btn = $('#quickCreateBtn');
  if (!btn) return;
  btn.addEventListener('click', () => {
    const addBtn = $('.kanban-col__footer-btn');
    if (!addBtn) return;
    addBtn.scrollIntoView({ behavior: 'smooth', block: 'center' });
    addBtn.animate(
      [
        { background: 'var(--accent-dim)', color: 'var(--accent)' },
        { background: 'var(--accent-dim)', color: 'var(--accent)' },
        { background: '',                  color: ''               },
      ],
      { duration: 1100, easing: 'ease-out' }
    );
  });
}

// ──────────────────────────────────────────────────────────────
//  PAGE ANIMATIONS — запускаємо після завантаження
// ──────────────────────────────────────────────────────────────

function animatePage() {
  // Загальна поява контенту
  const content = $('.page-content');
  if (content) springIn(content, { opacity: 0, transform: 'translateY(10px)' }, { opacity: 1, transform: 'translateY(0)' }, 260);

  // Sidebar проекти
  stagger($$('.sidebar__project-item'), el =>
    springIn(el, { opacity: 0, transform: 'translateX(-8px)' }, { opacity: 1, transform: 'translateX(0)' }, 210), 40);

  // Workspace / Project / Tag grid картки
  stagger($$('.workspace-card, .project-card, .tag-card'), el =>
    springIn(el, { opacity: 0, transform: 'translateY(16px) scale(0.97)' }, { opacity: 1, transform: 'translateY(0) scale(1)' }, 280), 50);

  // Таблиці
  stagger($$('.task-table__row, .members-table__row'), el =>
    springIn(el, { opacity: 0, transform: 'translateX(-8px)' }, { opacity: 1, transform: 'translateX(0)' }, 200), 25);

  // Task detail layout
  const detailMain    = $('.task-detail-main');
  const detailSidebar = $('.task-detail-sidebar');
  if (detailMain)
    springIn(detailMain, { opacity: 0, transform: 'translateY(14px)' }, { opacity: 1, transform: 'translateY(0)' }, 300);
  if (detailSidebar)
    setTimeout(() =>
      springIn(detailSidebar, { opacity: 0, transform: 'translateX(20px)' }, { opacity: 1, transform: 'translateX(0)' }, 300), 80);

  // Коментарі
  stagger($$('.comment'), el =>
    springIn(el, { opacity: 0, transform: 'translateY(10px)' }, { opacity: 1, transform: 'translateY(0)' }, 220), 55);

  // Activity items — простий fade
  stagger($$('.activity-item'), el =>
    el.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 180, fill: 'forwards' }), 25);

  // Stat chips — spring з scale
  stagger($$('.stat-chip'), el =>
    springIn(el, { opacity: 0, transform: 'scale(0.8) translateY(10px)' }, { opacity: 1, transform: 'scale(1) translateY(0)' }, 270), 60);

  // Form card
  const formCard = $('.form-card');
  if (formCard)
    springIn(formCard, { opacity: 0, transform: 'translateY(22px) scale(0.97)' }, { opacity: 1, transform: 'translateY(0) scale(1)' }, 340);

  // Auth card
  const authCard = $('.auth-card');
  if (authCard)
    springIn(authCard, { opacity: 0, transform: 'translateY(32px) scale(0.94)' }, { opacity: 1, transform: 'translateY(0) scale(1)' }, 400);
}

// ──────────────────────────────────────────────────────────────
//  INIT
// ──────────────────────────────────────────────────────────────

// ──────────────────────────────────────────────────────────────
//  NOTIFICATION DROPDOWN
// ──────────────────────────────────────────────────────────────

function initNotifDropdown() {
  const toggle   = document.getElementById('notifToggle');
  const dropdown = document.getElementById('notifDropdown');
  const menu     = document.getElementById('notifMenu');
  if (!toggle || !dropdown || !menu) return;

  function openDropdown() {
    dropdown.style.display = 'block';
    toggle.setAttribute('aria-expanded', 'true');
    springIn(
      dropdown,
      { opacity: 0, transform: 'translateY(-8px) scale(0.96)' },
      { opacity: 1, transform: 'translateY(0) scale(1)' },
      180
    );
  }

  function closeDropdown() {
    dropdown.style.display = 'none';
    toggle.setAttribute('aria-expanded', 'false');
  }

  toggle.addEventListener('click', function (e) {
    e.stopPropagation();
    dropdown.style.display === 'none' ? openDropdown() : closeDropdown();
  });

  document.addEventListener('click', function (e) {
    if (!menu.contains(e.target)) closeDropdown();
  });

  // "Позначити всі" через fetch без перезавантаження
  const markAllForm = document.getElementById('markAllForm');
  if (markAllForm) {
    markAllForm.addEventListener('submit', function (e) {
      e.preventDefault();
      fetch(markAllForm.action, {
        method: 'POST',
        headers: {
          'X-CSRFToken': markAllForm.querySelector('[name=csrfmiddlewaretoken]').value,
          'X-Requested-With': 'XMLHttpRequest',
        },
      }).then(() => {
        const badge = document.querySelector('.notif-badge');
        if (badge) badge.remove();
        document.querySelectorAll('.notif-item--unread').forEach(el => {
          el.classList.remove('notif-item--unread');
        });
        markAllForm.remove();
      });
    });
  }
}

// ──────────────────────────────────────────────────────────────
//  INIT
// ──────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  initSidebar();
  initUserDropdown();
  initTabs();
  initViewToggle();
  initTooltips();
  initAutoResize();
  initFilterAutoSubmit();
  initProjectPreview();
  initStatusForms();
  initArchiveForms();
  initQuickCreate();
  initNotifDropdown();
  animatePage();
});