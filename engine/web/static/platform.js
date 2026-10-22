// Local presentation only: navigation, workflow tabs and a browser-only guide download.
(function () {
  "use strict";
  const menu = document.querySelector(".menu-toggle");
  const nav = menu && document.getElementById(menu.getAttribute("aria-controls"));
  function setMenu(open, restoreFocus) {
    if (!menu || !nav) return;
    menu.setAttribute("aria-expanded", String(open));
    menu.setAttribute("aria-label", open ? "메뉴 닫기" : "메뉴 열기");
    nav.classList.toggle("open", open);
    if (restoreFocus) menu.focus();
  }
  if (menu && nav) {
    menu.addEventListener("click", () => setMenu(menu.getAttribute("aria-expanded") !== "true"));
    nav.querySelectorAll("a").forEach(link => link.addEventListener("click", () => setMenu(false)));
    document.addEventListener("keydown", event => {
      if (event.key === "Escape" && menu.getAttribute("aria-expanded") === "true") setMenu(false, true);
    });
    document.addEventListener("click", event => {
      if (!nav.contains(event.target) && !menu.contains(event.target)) setMenu(false);
    });
    window.addEventListener("resize", () => { if (window.innerWidth > 980) setMenu(false); });
  }
  const tabs = [...document.querySelectorAll("[data-step]")];
  function showStep(index, focus) {
    tabs.forEach((tab, i) => {
      tab.setAttribute("aria-selected", String(i === index));
      tab.tabIndex = i === index ? 0 : -1;
      const panel = document.getElementById(tab.getAttribute("aria-controls"));
      if (panel) panel.hidden = i !== index;
    });
    if (focus) tabs[index].focus();
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => showStep(index, false));
    tab.addEventListener("keydown", event => {
      let next;
      if (["ArrowRight", "ArrowDown"].includes(event.key)) next = (index + 1) % tabs.length;
      else if (["ArrowLeft", "ArrowUp"].includes(event.key)) next = (index + tabs.length - 1) % tabs.length;
      else if (event.key === "Home") next = 0;
      else if (event.key === "End") next = tabs.length - 1;
      if (next !== undefined) { event.preventDefault(); showStep(next, true); }
    });
  });
  let reportPrintState;
  function expandReportForPrint() {
    if (!document.querySelector(".service-report") || reportPrintState) return;
    reportPrintState = [...document.querySelectorAll(".service-report details")].map(section => [section, section.open]);
    reportPrintState.forEach(([section]) => { section.open = true; });
  }
  window.addEventListener("beforeprint", expandReportForPrint);
  window.addEventListener("afterprint", () => {
    (reportPrintState || []).forEach(([section, open]) => { section.open = open; });
    reportPrintState = undefined;
  });
  const reportPrint = document.querySelector("[data-print-report]");
  if (reportPrint) reportPrint.addEventListener("click", () => { expandReportForPrint(); window.print(); });
  const checks = [...document.querySelectorAll(".guide-checks input")];
  document.querySelectorAll("[data-run-picker]").forEach(picker => picker.addEventListener("change", () => {
    if (picker.value) window.location.assign(picker.value);
  }));
  function revealHashSection() {
    const target = document.getElementById(window.location.hash.slice(1));
    if (target && target.tagName === "DETAILS") target.open = true;
  }
  window.addEventListener("hashchange", revealHashSection);
  revealHashSection();
  const resultForm = document.querySelector(".result-filters");
  if (resultForm) resultForm.addEventListener("submit", event => {
    event.preventDefault();
    const fields = new FormData(resultForm);
    const query = new URLSearchParams();
    ["q", "control", "status", "treatment"].forEach(key => {
      const raw = String(fields.get(key) || "");
      const value = key === "q" ? raw.trim() : raw;
      if (value && !(value === "ALL" && ["status", "treatment"].includes(key))) query.set(key, value);
    });
    const search = query.toString();
    window.location.assign(resultForm.getAttribute("action") + (search ? "?" + search : ""));
  });
  const progress = document.getElementById("guide-progress");
  function updateProgress() {
    if (progress) progress.textContent = `준비 항목 ${checks.filter(box => box.checked).length} / ${checks.length}개 확인`;
  }
  checks.forEach(box => box.addEventListener("change", updateProgress));
  updateProgress();
  const download = document.getElementById("download-guide");
  if (download) download.addEventListener("click", () => {
    const text = "ControlProof 도입 준비 체크리스트\n\n" + checks.map(box =>
      (box.checked ? "[✓] " : "[ ] ") + box.parentElement.textContent.trim()
    ).join("\n") + "\n\n안내용 체크리스트입니다. 서비스 신청·READY 확인·실제 테스트 실행 승인을 의미하지 않습니다.\n";
    const url = URL.createObjectURL(new Blob(["\ufeff", text], {type: "text/plain;charset=utf-8"}));
    const link = document.createElement("a");
    link.href = url; link.download = "ControlProof_도입준비.txt";
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
}());
