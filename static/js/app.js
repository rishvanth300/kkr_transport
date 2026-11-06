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
});
