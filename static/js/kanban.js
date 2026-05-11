'use strict';

/* ════════════════════════════════════════════════════════════════
   TaskFlow — kanban.js
   Підключається лише на projects/detail.html через {% block extra_js %}
   Модулі: Drag&Drop · Auto Status · Column Create · Card Animate
════════════════════════════════════════════════════════════════ */

// ──────────────────────────────────────────────────────────────
//  Утіліти (дублюємо мінімальний набір, бо main.js вже завантажено)
// ──────────────────────────────────────────────────────────────

const $k  = (sel, ctx = document) => ctx.querySelector(sel);
const $$k = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

function getCsrfK() {
  return document.cookie.split('; ').find(r => r.startsWith('csrftoken='))?.split('=')[1] ?? '';
}

async function apiFetchK(url, data = {}) {
  const res = await fetch(url, {
    method:  'POST',
    headers: {
      'Content-Type':     'application/x-www-form-urlencoded',
      'X-Requested-With': 'XMLHttpRequest',
      'X-CSRFToken':      getCsrfK(),
    },
    body: new URLSearchParams({ csrfmiddlewaretoken: getCsrfK(), ...data }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// Spring-анімація
function kSpring(el, from, to, duration = 260) {
  return el.animate(
    [{ ...from, easing: 'cubic-bezier(0.34,1.56,0.64,1)' }, to],
    { duration, fill: 'forwards' }
  );
}

// ──────────────────────────────────────────────────────────────
//  ВІДПОВІДНІСТЬ: назва колонки → статус завдання
//  Якщо назва списку містить ключове слово — ставимо статус
// ──────────────────────────────────────────────────────────────

const LIST_STATUS_MAP = [
  { keywords: ['виконан', 'done', 'готов', 'завершен'],        status: 'done'        },
  { keywords: ['процес', 'progress', 'в роботі', 'активн'],    status: 'in_progress' },
  { keywords: ['перевір', 'review', 'тестуван', 'qa'],          status: 'in_review'   },
  { keywords: ['скасован', 'cancel', 'відхилен'],               status: 'cancelled'   },
  { keywords: ['todo', 'зробити', 'черга', 'backlog', 'нові'],  status: 'todo'        },
];

// Визначає статус за назвою колонки
function detectStatus(listName) {
  const name = listName.toLowerCase();
  for (const { keywords, status } of LIST_STATUS_MAP) {
    if (keywords.some(k => name.includes(k))) return status;
  }
  return null; // Не вдалося визначити — не змінюємо статус
}

// ──────────────────────────────────────────────────────────────
//  KANBAN DRAG & DROP
// ──────────────────────────────────────────────────────────────

function initKanban() {
  const board = $k('#kanbanBoard');
  if (!board) return;

  let dragged     = null;  // поточна перетягувана картка
  let placeholder = null;  // сірий placeholder на місці куди тягнемо

  // ── Стилі для placeholder та drag-over стану ──
  const style = document.createElement('style');
  style.textContent = `
    .kanban-placeholder {
      background: var(--accent-dim);
      border: 2px dashed var(--accent);
      border-radius: var(--radius-sm);
      transition: height 140ms ease;
      pointer-events: none;
    }
    .kanban-col--drag-over > .kanban-col__header {
      border-bottom-color: var(--accent);
    }
    .kanban-col--drag-over {
      border-color: var(--accent);
      background: linear-gradient(var(--accent-dim), transparent 120px);
    }
    .task-card.is-dragging {
      opacity: 0.35;
      transform: scale(0.97);
      cursor: grabbing;
    }
  `;
  document.head.appendChild(style);

  // ──────────────────────────────────────────────
  //  Знаходить елемент після якого вставити картку
  // ──────────────────────────────────────────────
  function getDropTarget(container, clientY) {
    const cards = $$k('.task-card:not(.is-dragging)', container);
    return cards.reduce((closest, card) => {
      const box    = card.getBoundingClientRect();
      const offset = clientY - box.top - box.height / 2;
      if (offset < 0 && offset > (closest.offset ?? -Infinity)) {
        return { offset, element: card };
      }
      return closest;
    }, {}).element ?? null;
  }

  // ──────────────────────────────────────────────
  //  DRAG START
  // ──────────────────────────────────────────────
  board.addEventListener('dragstart', (e) => {
    const card = e.target.closest('.task-card');
    if (!card) return;

    dragged = card;
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', card.dataset.taskId);

    // Затримка — щоб браузер встиг зробити "ghost" з оригіналу
    setTimeout(() => card.classList.add('is-dragging'), 0);

    // Placeholder з тією ж висотою що й картка
    placeholder = document.createElement('div');
    placeholder.className  = 'kanban-placeholder';
    placeholder.style.height = card.offsetHeight + 'px';
  });

  // ──────────────────────────────────────────────
  //  DRAG OVER — переміщаємо placeholder
  // ──────────────────────────────────────────────
  board.addEventListener('dragover', (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';

    const col = e.target.closest('.kanban-col__cards');
    if (!col || !dragged || !placeholder) return;

    const after = getDropTarget(col, e.clientY);
    placeholder.parentNode?.removeChild(placeholder);

    if (after) {
      col.insertBefore(placeholder, after);
    } else {
      col.appendChild(placeholder);
    }
  });

  // ──────────────────────────────────────────────
  //  DRAG ENTER / LEAVE — підсвітка колонки
  // ──────────────────────────────────────────────
  board.addEventListener('dragenter', (e) => {
    e.target.closest('.kanban-col')?.classList.add('kanban-col--drag-over');
  });

  board.addEventListener('dragleave', (e) => {
    const col = e.target.closest('.kanban-col');
    if (col && !col.contains(e.relatedTarget)) {
      col.classList.remove('kanban-col--drag-over');
    }
  });

  // ──────────────────────────────────────────────
  //  DROP — вставляємо картку та зберігаємо на сервері
  // ──────────────────────────────────────────────
  board.addEventListener('drop', async (e) => {
    e.preventDefault();

    const cardsContainer = e.target.closest('.kanban-col__cards');
    const col            = e.target.closest('.kanban-col');
    if (!cardsContainer || !dragged) return;

    // Вставляємо картку замість placeholder
    if (placeholder?.parentNode === cardsContainer) {
      cardsContainer.insertBefore(dragged, placeholder);
    } else {
      cardsContainer.appendChild(dragged);
    }
    placeholder?.remove();
    placeholder = null;

    // Прибираємо drag-стани
    dragged.classList.remove('is-dragging');
    $$k('.kanban-col--drag-over', board).forEach(c => c.classList.remove('kanban-col--drag-over'));

    // Spring-анімація "приземлення"
    kSpring(
      dragged,
      { transform: 'scale(0.95)' },
      { transform: 'scale(1)' },
      260
    );

    // Збираємо дані для сервера
    const taskId   = dragged.dataset.taskId;
    const listId   = cardsContainer.dataset.listId;
    const cards    = $$k('.task-card', cardsContainer);
    const position = cards.indexOf(dragged);

    // Визначаємо статус за назвою колонки
    const colName     = $k('.kanban-col__name', col)?.textContent?.trim() ?? '';
    const autoStatus  = detectStatus(colName);

    try {
      // 1. Зберігаємо нову позицію / колонку
      await apiFetchK(`/tasks/${taskId}/reorder/`, { list_pk: listId, position });

      // 2. Якщо статус визначено — змінюємо автоматично
      if (autoStatus) {
        const data = await apiFetchK(`/tasks/${taskId}/status/`, { status: autoStatus });

        if (data.success) {
          updateCardStatus(dragged, autoStatus);
          // Flash тільки якщо колонка має чіткий статус
          if (typeof showFlash === 'function') {
            showFlash(`Статус → «${data.status_display}»`);
          }
        }
      }

      // Оновлюємо лічильники карток у колонках
      updateColumnCounts();

    } catch {
      if (typeof showFlash === 'function') showFlash('Помилка збереження позиції', 'error');
    }

    dragged = null;
  });

  // ──────────────────────────────────────────────
  //  DRAG END — cleanup якщо drop відбувся поза board
  // ──────────────────────────────────────────────
  board.addEventListener('dragend', () => {
    dragged?.classList.remove('is-dragging');
    placeholder?.remove();
    $$k('.kanban-col--drag-over', board).forEach(c => c.classList.remove('kanban-col--drag-over'));
    dragged     = null;
    placeholder = null;
  });
}

// ──────────────────────────────────────────────────────────────
//  Оновлення вигляду картки після зміни статусу
// ──────────────────────────────────────────────────────────────

function updateCardStatus(card, status) {
  // Priority bar не чіпаємо — він залежить від priority, не status
  // Оновлюємо клас заголовку якщо завдання виконано
  const title = $k('.task-card__title', card);
  if (title) {
    title.classList.toggle('task-card__title--done', status === 'done');
  }

  // Пульсація картки щоб показати що статус змінився
  kSpring(
    card,
    { boxShadow: '0 0 0 2px var(--green)' },
    { boxShadow: '0 0 0 0px transparent' },
    500
  );
}

// ──────────────────────────────────────────────────────────────
//  Оновлення лічильників карток у заголовках колонок
// ──────────────────────────────────────────────────────────────

function updateColumnCounts() {
  $$k('.kanban-col').forEach(col => {
    const cards   = $$k('.task-card', col).length;
    const counter = $k('.kanban-col__count', col);
    if (counter) {
      const old = counter.textContent;
      counter.textContent = cards;
      // Анімуємо лічильник якщо він змінився
      if (old !== String(cards)) {
        kSpring(counter, { transform: 'scale(1.4)' }, { transform: 'scale(1)' }, 220);
      }
    }
  });
}

// ──────────────────────────────────────────────────────────────
//  ШВИДКЕ СТВОРЕННЯ КАРТКИ — inline форма у нижній частині колонки
// ──────────────────────────────────────────────────────────────

function initQuickAddCard() {
  $$k('.kanban-col__footer-btn').forEach(btn => {
    // Якщо кнопка є посиланням — залишаємо перехід, не перехоплюємо
    if (btn.tagName === 'A') return;

    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const col      = btn.closest('.kanban-col');
      const cardsEl  = $k('.kanban-col__cards', col);
      const listId   = cardsEl?.dataset.listId;
      if (!listId) return;

      // Переходимо на форму створення завдання
      window.location.href = `/tasks/create/${listId}/`;
    });
  });
}

// ──────────────────────────────────────────────────────────────
//  АНІМАЦІЯ KANBAN ПРИ ЗАВАНТАЖЕННІ
// ──────────────────────────────────────────────────────────────

function animateKanbanLoad() {
  const board = $k('#kanbanBoard');
  if (!board) return;

  // Колонки — stagger справа наліво (ефект розгортання дошки)
  const cols = $$k('.kanban-col', board);
  cols.forEach((col, i) => {
    col.style.opacity = '0';
    setTimeout(() => {
      kSpring(
        col,
        { opacity: 0, transform: 'translateY(22px) scale(0.97)' },
        { opacity: 1, transform: 'translateY(0) scale(1)' },
        320
      );
    }, i * 65);
  });

  // Картки всередині кожної колонки — stagger із затримкою відносно колонки
  cols.forEach((col, ci) => {
    const cards = $$k('.task-card', col);
    cards.forEach((card, ki) => {
      card.style.opacity = '0';
      setTimeout(() => {
        kSpring(
          card,
          { opacity: 0, transform: 'translateX(-10px)' },
          { opacity: 1, transform: 'translateX(0)' },
          220
        );
      }, ci * 65 + ki * 35 + 120);
    });
  });
}

// ──────────────────────────────────────────────────────────────
//  HOVER ЕФЕКТ НА КАРТКАХ — підсвітка приоритетної смужки
// ──────────────────────────────────────────────────────────────

function initCardHover() {
  $$k('.task-card').forEach(card => {
    const bar = $k('.task-card__priority-bar', card);
    if (!bar) return;

    card.addEventListener('mouseenter', () => {
      bar.animate(
        [{ width: '3px' }, { width: '5px' }],
        { duration: 180, fill: 'forwards', easing: 'ease-out' }
      );
    });

    card.addEventListener('mouseleave', () => {
      bar.animate(
        [{ width: '5px' }, { width: '3px' }],
        { duration: 180, fill: 'forwards', easing: 'ease-in' }
      );
    });
  });
}

// ──────────────────────────────────────────────────────────────
//  INIT
// ──────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  animateKanbanLoad();
  initKanban();
  initQuickAddCard();
  initCardHover();
});
