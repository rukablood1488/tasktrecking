'use strict';

/* ════════════════════════════════════════════════════════════════
   landing.js — анімації лише для landing page
════════════════════════════════════════════════════════════════ */

function springIn(el, from, to, duration = 300) {
  return el.animate(
    [{ ...from, easing: 'cubic-bezier(0.34,1.56,0.64,1)' }, to],
    { duration, fill: 'forwards' }
  );
}

function stagger(els, cb, delay = 60) {
  els.forEach((el, i) => setTimeout(() => cb(el, i), i * delay));
}

// Intersection Observer — анімуємо елементи при появі у viewport
function initScrollAnimations() {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        const el = entry.target;
        const delay = parseInt(el.dataset.delay || '0');
        setTimeout(() => {
          springIn(el, { opacity: 0, transform: 'translateY(24px) scale(0.97)' },
                       { opacity: 1, transform: 'translateY(0) scale(1)' }, 360);
        }, delay);
        observer.unobserve(el);
      });
    },
    { threshold: 0.12 }
  );

  document.querySelectorAll('.feature-card').forEach((card, i) => {
    card.style.opacity = '0';
    card.dataset.delay = i * 70;
    observer.observe(card);
  });
}

// Hero анімація при завантаженні
function animateHero() {
  const badge    = document.querySelector('.hero__badge');
  const title    = document.querySelector('.hero__title');
  const subtitle = document.querySelector('.hero__subtitle');
  const cta      = document.querySelector('.hero__cta');
  const preview  = document.querySelector('.hero__preview');

  const els = [badge, title, subtitle, cta].filter(Boolean);
  stagger(els, (el) => {
    springIn(el, { opacity: 0, transform: 'translateY(20px)' },
                 { opacity: 1, transform: 'translateY(0)' }, 340);
  }, 80);

  if (preview) {
    setTimeout(() => {
      springIn(preview,
        { opacity: 0, transform: 'translateX(30px) scale(0.96)' },
        { opacity: 1, transform: 'translateX(0) scale(1)' }, 420);
    }, 200);
  }
}

// Navbar — додаємо тінь при скролі
function initNavbarScroll() {
  const nav = document.querySelector('.landing-nav');
  if (!nav) return;
  window.addEventListener('scroll', () => {
    nav.style.boxShadow = window.scrollY > 10 ? '0 2px 20px rgba(0,0,0,.4)' : '';
  }, { passive: true });
}

document.addEventListener('DOMContentLoaded', () => {
  animateHero();
  initScrollAnimations();
  initNavbarScroll();
});
