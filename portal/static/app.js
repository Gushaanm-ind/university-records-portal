// University Portal — interface behaviour.
// Loaded from /static so it works under the Content-Security-Policy.
(function () {
  "use strict";

  function $(selector, root) {
    return (root || document).querySelector(selector);
  }

  function $all(selector, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(selector));
  }

  /* ---------------------------------------------------------------- nav -- */

  function setupSidebar() {
    var sidebar = $("#sidebar");
    var toggle = $("[data-sidebar-toggle]");
    var backdrop = $("[data-sidebar-close]");
    if (!sidebar || !toggle) return;

    function setOpen(open) {
      sidebar.classList.toggle("is-open", open);
      document.body.classList.toggle("nav-open", open);
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    }

    toggle.addEventListener("click", function () {
      setOpen(!sidebar.classList.contains("is-open"));
    });
    if (backdrop) backdrop.addEventListener("click", function () { setOpen(false); });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") setOpen(false);
    });
  }

  /* ----------------------------------------------------------- confirms -- */

  function setupConfirms() {
    $all("[data-confirm]").forEach(function (el) {
      var message = el.getAttribute("data-confirm") || "Are you sure?";
      if (el.tagName === "FORM") {
        el.addEventListener("submit", function (event) {
          if (!window.confirm(message)) event.preventDefault();
        });
      } else {
        el.addEventListener("click", function (event) {
          if (!window.confirm(message)) event.preventDefault();
        });
      }
    });
  }

  /* ------------------------------------------------------------- alerts -- */

  function setupAlerts() {
    $all(".alert").forEach(function (alert) {
      var close = document.createElement("button");
      close.type = "button";
      close.className = "alert-close";
      close.setAttribute("aria-label", "Dismiss message");
      close.innerHTML = "&times;";
      close.addEventListener("click", function () { alert.remove(); });
      alert.appendChild(close);

      if (!alert.classList.contains("alert-error")) {
        window.setTimeout(function () {
          alert.classList.add("is-leaving");
          window.setTimeout(function () { alert.remove(); }, 250);
        }, 7000);
      }
    });
  }

  /* -------------------------------------------------------- copy button -- */

  function setupCopy() {
    $all("[data-copy]").forEach(function (button) {
      button.addEventListener("click", function () {
        var value = button.getAttribute("data-copy");
        var done = function () {
          var original = button.getAttribute("data-original") || button.textContent;
          button.setAttribute("data-original", original);
          button.textContent = "Copied";
          window.setTimeout(function () {
            button.textContent = button.getAttribute("data-original");
          }, 1600);
        };

        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(value).then(done, function () {});
          return;
        }
        var field = document.createElement("textarea");
        field.value = value;
        document.body.appendChild(field);
        field.select();
        try { document.execCommand("copy"); done(); } catch (err) { /* ignore */ }
        field.remove();
      });
    });
  }

  /* ------------------------------------------------- password visibility -- */

  function setupPasswordToggles() {
    $all("[data-toggle-password]").forEach(function (button) {
      button.addEventListener("click", function () {
        var input = document.getElementById(button.getAttribute("data-toggle-password"));
        if (!input) return;
        var reveal = input.type === "password";
        input.type = reveal ? "text" : "password";
        button.classList.toggle("is-on", reveal);
        button.setAttribute("aria-label", reveal ? "Hide password" : "Show password");
      });
    });
  }

  /* ------------------------------------------------- live table filter --- */

  function setupLiveFilter() {
    $all("[data-filter-target]").forEach(function (input) {
      var table = document.getElementById(input.getAttribute("data-filter-target"));
      if (!table) return;
      var rows = $all("tbody tr", table);
      var empty = document.getElementById(input.getAttribute("data-filter-empty"));

      input.addEventListener("input", function () {
        var needle = input.value.trim().toLowerCase();
        var shown = 0;
        rows.forEach(function (row) {
          var match = !needle || row.textContent.toLowerCase().indexOf(needle) !== -1;
          row.hidden = !match;
          if (match) shown += 1;
        });
        if (empty) empty.hidden = shown > 0;
      });
    });
  }

  /* ------------------------------------------- create-user form dynamics -- */

  function setupCreateUserForm() {
    var form = $("#create-user-form");
    if (!form) return;

    var roleSelect = $("#role", form);
    var usernameInput = $("#username", form);
    var usernameLabel = $("#username-label", form);
    var usernameHint = $("#username-hint", form);
    var nameInput = $("#full_name", form);
    var emailInput = $("#email", form);

    var roleCopy = {
      student: {
        label: "Roll number (used to sign in)",
        hint: "Numeric roll number, e.g. 151.",
        placeholder: "151"
      },
      teacher: {
        label: "Staff code (used to sign in)",
        hint: "Staff code, e.g. T007.",
        placeholder: "T007"
      },
      hod: {
        label: "Username (used to sign in)",
        hint: "Short login name, e.g. hod_cse.",
        placeholder: "hod_cse"
      },
      admin: {
        label: "Username (used to sign in)",
        hint: "Short login name, e.g. registrar.",
        placeholder: "registrar"
      }
    };

    function sync() {
      var role = roleSelect ? roleSelect.value : "";
      var copy = roleCopy[role];

      $all("[data-role-field]", form).forEach(function (field) {
        var roles = (field.getAttribute("data-role-field") || "").split(/\s+/);
        var visible = !roles[0] || roles.indexOf(role) !== -1;
        field.hidden = !visible;
        $all("input, select", field).forEach(function (control) {
          var required = control.getAttribute("data-required-for") || "";
          if (required.split(/\s+/).indexOf(role) !== -1) {
            control.required = true;
          } else if (required) {
            control.required = false;
          }
        });
      });

      if (copy && usernameLabel) usernameLabel.textContent = copy.label;
      if (copy && usernameHint) usernameHint.textContent = copy.hint;
      if (copy && usernameInput) usernameInput.placeholder = copy.placeholder;
    }

    if (roleSelect) roleSelect.addEventListener("change", sync);
    sync();

    // Suggest an email from the full name when the email field is still empty.
    if (nameInput && emailInput) {
      nameInput.addEventListener("blur", function () {
        if (emailInput.value.trim() || !nameInput.value.trim()) return;
        var role = roleSelect ? roleSelect.value : "";
        var slug = nameInput.value.trim().toLowerCase().replace(/[^a-z0-9]+/g, ".");
        slug = slug.replace(/^\.+|\.+$/g, "");
        if (!slug) return;
        var domain = role === "student" ? "@student.univ.edu"
                   : role === "hod" ? "@univ.edu"
                   : "@cse.univ.edu";
        emailInput.value = slug + domain;
      });
    }

    // Generate a strong password without any external library.
    var generate = $("#generate-password", form);
    var passwordInput = $("#password", form);
    if (generate && passwordInput) {
      generate.addEventListener("click", function () {
        var alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%&*";
        var values = new Uint32Array(16);
        window.crypto.getRandomValues(values);
        var password = "";
        for (var i = 0; i < values.length; i += 1) {
          password += alphabet.charAt(values[i] % alphabet.length);
        }
        passwordInput.value = password;
        passwordInput.type = "text";
        var hint = $("#generated-hint", form);
        if (hint) hint.hidden = false;
      });
    }
  }

  /* ---------------------------------------------------------------- date -- */

  function setupToday() {
    $all("[data-today]").forEach(function (el) {
      try {
        el.textContent = new Date().toLocaleDateString(undefined, {
          weekday: "short", day: "numeric", month: "short", year: "numeric"
        });
      } catch (err) { /* ignore */ }
    });
  }

  /* --------------------------------------------------------- submits ----- */

  function setupSubmitState() {
    $all("form[data-busy]").forEach(function (form) {
      form.addEventListener("submit", function () {
        $all("button[type=submit]", form).forEach(function (button) {
          button.classList.add("is-busy");
          button.setAttribute("aria-busy", "true");
        });
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.documentElement.classList.add("has-js");
    setupSidebar();
    setupConfirms();
    setupAlerts();
    setupCopy();
    setupPasswordToggles();
    setupLiveFilter();
    setupCreateUserForm();
    setupToday();
    setupSubmitState();
  });
})();
