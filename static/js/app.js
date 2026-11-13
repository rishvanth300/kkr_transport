document.addEventListener("DOMContentLoaded", () => {
  const splash = document.getElementById("splash-screen");
  if (splash) {
    if (window.sessionStorage.getItem("kkr-splash-seen") === "1") {
      splash.classList.add("is-hidden");
    } else {
      window.setTimeout(() => {
        splash.classList.add("is-hidden");
        window.sessionStorage.setItem("kkr-splash-seen", "1");
      }, 250);
    }
  }

  const passwordInput = document.querySelector("[data-password-toggle]")
    ?.closest(".input-with-icon")
    ?.querySelector("input");
  const passwordToggle = document.querySelector("[data-password-toggle]");
  if (passwordInput && passwordToggle) {
    passwordToggle.addEventListener("click", () => {
      const isPassword = passwordInput.type === "password";
      passwordInput.type = isPassword ? "text" : "password";
      passwordToggle.textContent = isPassword ? "Hide" : "Show";
      passwordToggle.setAttribute("aria-label", isPassword ? "Hide password" : "Show password");
    });
  }

  const loginForm = document.querySelector("[data-login-form]");
  const loginButton = document.querySelector("[data-login-button]");
  if (loginForm && loginButton) {
    loginForm.addEventListener("submit", () => {
      loginButton.disabled = true;
      loginButton.classList.add("is-loading");
      loginButton.textContent = "Logging in...";
    });
  }

  const sidebar = document.getElementById("sidebar");
  const sidebarToggles = document.querySelectorAll("[data-sidebar-toggle]");
  const sidebarCloses = document.querySelectorAll("[data-sidebar-close]");
  const setSidebar = (open) => {
    if (!sidebar) return;
    // Treat as mobile/modal menu only on small screens where the hamburger is used.
    const isMobileMenu = window.innerWidth <= 767;
    const shouldOpen = !!open && isMobileMenu;
    sidebar.classList.toggle("is-open", shouldOpen);
    document.body.classList.toggle("sidebar-open", shouldOpen);
    sidebarToggles.forEach((btn) => btn.setAttribute("aria-expanded", shouldOpen ? "true" : "false"));
  };
  if (sidebar) {
    sidebarToggles.forEach((btn) => btn.addEventListener("click", () => setSidebar(!sidebar.classList.contains("is-open"))));
    sidebarCloses.forEach((btn) => btn.addEventListener("click", () => setSidebar(false)));
    sidebar.querySelectorAll(".nav-link").forEach((link) => {
      link.addEventListener("click", () => {
        if (window.innerWidth <= 767) setSidebar(false);
      });
    });
    window.addEventListener("resize", () => {
      if (window.innerWidth > 767) {
        sidebar.classList.remove("is-open");
        document.body.classList.remove("sidebar-open");
        sidebarToggles.forEach((btn) => btn.setAttribute("aria-expanded", "false"));
      } else if (!sidebar.classList.contains("is-open")) {
        document.body.classList.remove("sidebar-open");
      }
    });
  }

  // Smart Enter-key navigation for marked forms (e.g. Trip Sheet and related entry forms)
  document.querySelectorAll("form[data-enter-nav]").forEach((form) => {
    if (form.dataset.enterNavBound === "1") return;
    form.dataset.enterNavBound = "1";
    let allowSubmit = false;
    const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
    if (submitBtn) {
      submitBtn.addEventListener("click", () => { allowSubmit = true; });
    }
    form.addEventListener("submit", (e) => {
      if (!allowSubmit) {
        e.preventDefault();
      }
      allowSubmit = false;
    });

    const isFocusableField = (el) => {
      if (!el || el.disabled || el.readOnly) return false;
      if (el.type === "hidden" || el.type === "submit" || el.type === "button") return false;
      if (el.closest("[hidden]")) return false;
      const style = window.getComputedStyle(el);
      if (style.display === "none" || style.visibility === "hidden") return false;
      return ["INPUT", "SELECT", "TEXTAREA"].includes(el.tagName);
    };
    const focusableFields = () => Array.from(form.querySelectorAll("input, select, textarea")).filter(isFocusableField);
    const clearEnterError = (el) => {
      const wrap = el.closest(".field");
      if (!wrap) return;
      const old = wrap.querySelector(".field-error.enter-nav-error");
      if (old) old.remove();
      if (wrap.dataset.enterError === "1") {
        wrap.classList.remove("has-error");
        delete wrap.dataset.enterError;
      }
    };
    const showEnterError = (el, message) => {
      const wrap = el.closest(".field") || el.parentElement;
      if (!wrap) return;
      const old = wrap.querySelector(".field-error.enter-nav-error");
      if (old) old.remove();
      const p = document.createElement("p");
      p.className = "field-error enter-nav-error";
      p.textContent = message;
      wrap.appendChild(p);
      if (wrap.classList && wrap.classList.contains("field") && !wrap.classList.contains("has-error")) {
        wrap.dataset.enterError = "1";
        wrap.classList.add("has-error");
      }
    };
    const validateForEnter = (el) => {
      clearEnterError(el);
      if (el.tagName === "SELECT") {
        if (el.required && !el.value) {
          showEnterError(el, "Please select a value to continue.");
          try { el.focus(); } catch (err) {}
          return false;
        }
        return true;
      }
      const value = (el.value || "").trim();
      if (el.required && value === "") {
        showEnterError(el, "This field is required before moving to the next field.");
        try { el.focus(); } catch (err) {}
        return false;
      }
      if (value !== "" && typeof el.checkValidity === "function" && !el.checkValidity()) {
        showEnterError(el, el.validationMessage || "Please enter a valid value.");
        try { el.focus(); } catch (err) {}
        return false;
      }
      return true;
    };

    form.addEventListener("keydown", (e) => {
      if (e.key !== "Enter") return;
      const target = e.target;
      if (!target || !form.contains(target)) return;
      if (target.type === "submit" || target.type === "button") return;
      if (target.tagName === "TEXTAREA") return;
      if (target.tagName === "SELECT") {
        e.preventDefault();
        if (!validateForEnter(target)) return;
        const fields = focusableFields();
        const idx = fields.indexOf(target);
        if (idx >= 0 && idx < fields.length - 1) fields[idx + 1].focus();
        return;
      }
      e.preventDefault();
      if (!validateForEnter(target)) return;
      const fields = focusableFields();
      const idx = fields.indexOf(target);
      if (idx >= 0 && idx < fields.length - 1) {
        fields[idx + 1].focus();
      }
    });
    form.addEventListener("input", (e) => { if (e.target) clearEnterError(e.target); });
    form.addEventListener("change", (e) => { if (e.target) clearEnterError(e.target); });
  });
});
