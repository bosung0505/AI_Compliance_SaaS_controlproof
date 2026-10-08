// ControlProof workbench script: filters, copy and form submit only. Nothing here judges, counts or recomputes a
// status; filters hide rows by the status values the server copied into data attributes.
(function () {
  "use strict";

  var FILTERS = {
    runnable: function (row) { return row.dataset.readiness === "READY"; },
    failed: function (row) { return row.dataset.result === "FAIL"; },
    inconclusive: function (row) { return row.dataset.result === "INCONCLUSIVE"; }
  };

  function applyFilters() {
    var active = Array.prototype.filter.call(document.querySelectorAll("[data-filter]"), function (box) {
      return box.checked;
    }).map(function (box) { return FILTERS[box.dataset.filter]; });
    var rows = document.querySelectorAll("tr.scenario-row");
    Array.prototype.forEach.call(rows, function (row) {
      var keep = active.every(function (test) { return test(row); });
      row.classList.toggle("hidden", !keep);
    });
    Array.prototype.forEach.call(document.querySelectorAll("tr.group"), function (header) {
      var visible = document.querySelector("tr.scenario-row[data-group='" + header.dataset.group + "']:not(.hidden)");
      header.classList.toggle("hidden", !visible);
    });
  }

  Array.prototype.forEach.call(document.querySelectorAll("[data-filter]"), function (box) {
    box.addEventListener("change", applyFilters);
  });

  var form = document.querySelector("form[data-testid=preflight-form]");
  if (form) {
    form.addEventListener("submit", function () {
      var parts = form.querySelector("[data-preflight-choice]").value.split("|");
      form.querySelector("input[name=scenario_id]").value = parts[0];
      form.querySelector("input[name=execution_profile]").value = parts[1];
      var button = form.querySelector("button[type=submit]");
      button.disabled = true;
      button.textContent = "확인 중…";
    });
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-copy]");
    if (!button) { return; }
    var source = document.getElementById(button.dataset.copy);
    var done = function () { button.textContent = "복사됨"; };
    var fail = function () { button.textContent = "직접 선택해 복사"; };
    if (navigator.clipboard && source) {
      navigator.clipboard.writeText(source.dataset.command || source.textContent.trim()).then(done, fail);
    } else {
      fail();
    }
  });

  var failOnly = document.querySelector("[data-testid=fail-only]");
  if (failOnly) {
    failOnly.addEventListener("change", function () {
      Array.prototype.forEach.call(document.querySelectorAll("tr.assertion-row"), function (row) {
        row.classList.toggle("hidden", failOnly.checked && row.dataset.status === "PASS");
      });
    });
  }

  applyFilters();
}());
