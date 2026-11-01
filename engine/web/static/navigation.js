// Public navigation: pointer hover, keyboard disclosure and mobile accordion.
(function () {
  "use strict";
  const header = document.querySelector(".explore-header");
  if (!header) return;
  const groups = [...header.querySelectorAll(".nav-disclosure")];
  const desktop = window.matchMedia("(min-width: 981px)");
  let active = null;
  let closeTimer;
  function show(group) {
    clearTimeout(closeTimer);
    active = group;
    groups.forEach(item => {
      const open = item === group;
      item.classList.toggle("is-open", open);
      item.querySelector(".nav-trigger").setAttribute("aria-expanded", String(open));
      item.querySelector(".nav-panel").inert = !open;
    });
    document.body.classList.toggle("nav-expanded", Boolean(group));
  }
  groups.forEach(group => {
    const trigger = group.querySelector(".nav-trigger");
    group.addEventListener("pointerenter", event => {
      if (desktop.matches && event.pointerType === "mouse") show(group);
    });
    trigger.addEventListener("click", event => {
      // A pointer click on a hover-opened item should keep its links available.
      if (desktop.matches && event.detail > 0 && active === group) return;
      show(active === group ? null : group);
    });
    trigger.addEventListener("keydown", event => {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        show(group);
        requestAnimationFrame(() => {
          if (active === group) group.querySelector(".nav-panel a").focus();
        });
      }
    });
  });
  header.addEventListener("pointerenter", () => clearTimeout(closeTimer));
  header.addEventListener("pointerleave", () => {
    if (desktop.matches) closeTimer = setTimeout(() => show(null), 160);
  });
  header.addEventListener("focusout", () => {
    setTimeout(() => { if (!header.contains(document.activeElement)) show(null); }, 0);
  });
  header.querySelectorAll("a").forEach(link => link.addEventListener("click", () => show(null)));
  document.addEventListener("click", event => { if (!header.contains(event.target)) show(null); });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && active) {
      const trigger = active.querySelector(".nav-trigger");
      show(null);
      if (desktop.matches) trigger.focus();
    }
  });
  const mobileMenu = header.querySelector(".menu-toggle");
  mobileMenu.addEventListener("click", () => show(null));
  desktop.addEventListener("change", () => show(null));
})();
