/**
 * Accounts, the monthly plan, payments and examiner checks.
 *
 * Account.refreshMe()     – load the signed-in user (GET /api/me) and update the header
 * Account.login()         – sign-in window (email code or Google); resolves true when signed in
 * Account.paywall(test)   – explain a locked test and offer the plan
 * Account.buy(kind, ...)  – create an order and pay (Payme, Click or card transfer)
 * Pages: pricing, account, examiners, check, examiner dashboard, admin.
 */
(function () {
  "use strict";

  const esc = (v) => U.escapeHtml(v);
  const state = { me: { user: null }, billing: null, config: {} };

  const money = (n) => `${String(Math.round(Number(n) || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, " ")} so'm`;
  const longDate = (iso) => {
    const d = new Date(iso);
    return isNaN(d) ? "" : d.toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" });
  };
  const initials = (name) => String(name || "?").trim().split(/\s+/).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
  const stars = (value) => {
    const v = Math.round(Number(value) || 0);
    return `<span class="stars" aria-label="${v} out of 5 stars">${"★".repeat(v)}<span class="stars-off">${"★".repeat(5 - v)}</span></span>`;
  };
  const STATUS = {
    waiting: ["Waiting for the examiner", "badge-waiting"],
    in_progress: ["Being marked", "badge-progress-check"],
    completed: ["Marked", "badge-done"],
    cancelled: ["Cancelled", "badge-cancelled"],
    pending: ["Not paid", "badge-cancelled"],
    awaiting_confirmation: ["Payment being checked", "badge-waiting"],
    paid: ["Paid", "badge-done"],
    refunded: ["Refunded", "badge-cancelled"],
  };
  const statusBadge = (s) => `<span class="status-badge ${(STATUS[s] || ["", ""])[1]}">${esc((STATUS[s] || [s])[0])}</span>`;

  function user() {
    return state.me && state.me.user;
  }
  function planActive() {
    return Boolean(state.me && state.me.plan && state.me.plan.active);
  }
  function role() {
    return (user() && user().role) || "guest";
  }

  async function refreshMe() {
    try {
      state.me = await U.api("/api/me");
    } catch (e) {
      state.me = { user: null };
    }
    renderAccountSlot();
    // Admins and examiners see new payments and checks in the menu without reloading.
    if (!state.poll && ["admin", "examiner"].includes(role())) {
      state.poll = setInterval(() => { if (!document.hidden) refreshMe(); }, 120000);
    }
    return state.me;
  }

  async function billing() {
    if (!state.billing) state.billing = await U.api("/api/billing");
    return state.billing;
  }

  function renderAccountSlot() {
    const slot = document.getElementById("account-slot");
    if (!slot) return;
    const u = user();
    if (!u) {
      slot.innerHTML = `<button type="button" class="nav-signin" data-action="signin">Sign in</button>`;
      return;
    }
    const todo = state.me.todo || {};
    const count = (n, what) => (n ? ` <span class="nav-count" title="${n} ${what}">${n > 99 ? "99+" : n}</span>` : "");
    slot.innerHTML = `
      ${u.role === "examiner" || u.role === "admin" ? `<a href="#/examiner" class="nav-extra" data-nav="examiner">Examiner${count(todo.checks, "checks to mark")}</a>` : ""}
      ${u.role === "admin" ? `<a href="#/admin" class="nav-extra" data-nav="admin">Admin${count(todo.payments, "payments to confirm")}</a>` : ""}
      <a href="#/account" class="nav-account" data-nav="account" title="${esc(u.email)}">
        <span class="avatar" aria-hidden="true">${esc(initials(u.name || u.email))}</span>
        <span class="nav-account-name">${esc(u.name || u.email.split("@")[0])}</span>
      </a>`;
  }

  /* ================================================================ sign-in */
  function overlay(title, bodyHTML, extraClass = "") {
    const el = document.createElement("div");
    el.className = "modal-overlay";
    el.innerHTML = `
      <div class="modal-box ${extraClass}" role="dialog" aria-modal="true" aria-labelledby="ov-title">
        <div class="modal-header"><span id="ov-title">${esc(title)}</span>
          <button type="button" class="modal-close" aria-label="Close">&times;</button></div>
        <div class="modal-body">${bodyHTML}</div>
      </div>`;
    document.body.appendChild(el);
    return el;
  }

  function login(reason) {
    if (user()) return Promise.resolve(true);
    return new Promise((resolve) => {
      const google = state.config.auth && state.config.auth.google;
      const el = overlay("Sign in", `
        <div class="auth-step" data-step="email">
          <p class="auth-lead">${esc(reason || "Sign in to save your progress on every device, unlock all tests with the plan and order examiner checks.")}</p>
          ${google ? `<button type="button" class="btn-google" data-google>
              <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="#4285F4" d="M21.6 12.23c0-.7-.06-1.37-.18-2.02H12v3.83h5.38a4.6 4.6 0 0 1-2 3.02v2.5h3.24c1.9-1.75 2.98-4.32 2.98-7.33z"/><path fill="#34A853" d="M12 22c2.7 0 4.96-.9 6.62-2.43l-3.24-2.5c-.9.6-2.04.95-3.38.95-2.6 0-4.8-1.75-5.59-4.1H3.07v2.58A10 10 0 0 0 12 22z"/><path fill="#FBBC05" d="M6.41 13.92a6 6 0 0 1 0-3.84V7.5H3.07a10 10 0 0 0 0 9z"/><path fill="#EA4335" d="M12 5.98c1.47 0 2.79.5 3.83 1.5l2.87-2.87A9.6 9.6 0 0 0 12 2a10 10 0 0 0-8.93 5.5l3.34 2.58C7.2 7.73 9.4 5.98 12 5.98z"/></svg>
              Continue with Google</button>
            <div class="auth-or"><span>or use your email</span></div>` : ""}
          <form class="auth-form" data-form="email" novalidate>
            <label for="auth-email">Email address</label>
            <input id="auth-email" type="email" autocomplete="email" inputmode="email" required maxlength="254" placeholder="you@example.com" />
            <p class="form-error" role="alert" hidden></p>
            <button type="submit" class="btn-primary btn-lg">Send me a code</button>
          </form>
        </div>
        <div class="auth-step" data-step="code" hidden>
          <p class="auth-lead">We sent a 6-digit code to <strong data-email></strong>. It can take a minute to arrive,
            and it may be in your spam folder. You can also click the link in the email.</p>
          <p class="dev-hint" hidden></p>
          <form class="auth-form" data-form="code" novalidate>
            <label for="auth-code">Code</label>
            <input id="auth-code" class="code-input" inputmode="numeric" autocomplete="one-time-code" maxlength="6" pattern="[0-9]{6}" required />
            <p class="form-error" role="alert" hidden></p>
            <button type="submit" class="btn-primary btn-lg">Sign in</button>
          </form>
          <div class="auth-links">
            <button type="button" class="btn-link" data-back>Use a different email</button>
            <button type="button" class="btn-link" data-resend>Send a new code</button>
          </div>
        </div>`, "auth-box");

      let email = "";
      let done = false;
      const close = (ok) => {
        if (done) return;
        done = true;
        el.remove();
        document.removeEventListener("keydown", onKey);
        resolve(ok);
      };
      const onKey = (e) => { if (e.key === "Escape") close(false); };
      document.addEventListener("keydown", onKey);
      el.querySelector(".modal-close").addEventListener("click", () => close(false));
      const step = (name) => el.querySelectorAll(".auth-step").forEach((s) => { s.hidden = s.dataset.step !== name; });
      const showError = (form, msg) => {
        const p = el.querySelector(`[data-form="${form}"] .form-error`);
        p.textContent = msg || "";
        p.hidden = !msg;
      };
      const busy = (form, on) => {
        const b = el.querySelector(`[data-form="${form}"] button[type=submit]`);
        b.disabled = on;
        b.classList.toggle("is-busy", on);
      };

      const sendCode = async () => {
        showError("email", "");
        busy("email", true);
        try {
          const res = await U.api("/api/auth/code", { method: "POST", body: JSON.stringify({ email }) });
          el.querySelector("[data-email]").textContent = res.email;
          const hint = el.querySelector(".dev-hint");
          hint.hidden = !res.devCode;
          if (res.devCode) hint.textContent = `Development mode: your code is ${res.devCode}`;
          step("code");
          el.querySelector("#auth-code").value = "";
          el.querySelector("#auth-code").focus();
          return true;
        } catch (err) {
          showError("email", err.message);
          step("email");
          return false;
        } finally {
          busy("email", false);
        }
      };

      el.querySelector('[data-form="email"]').addEventListener("submit", (e) => {
        e.preventDefault();
        email = el.querySelector("#auth-email").value.trim();
        if (!email) return showError("email", "Please enter your email address.");
        sendCode();
      });
      el.querySelector('[data-form="code"]').addEventListener("submit", async (e) => {
        e.preventDefault();
        const code = el.querySelector("#auth-code").value.replace(/\s+/g, "");
        if (!/^\d{6}$/.test(code)) return showError("code", "Enter the 6-digit code from the email.");
        showError("code", "");
        busy("code", true);
        try {
          state.me = await U.api("/api/auth/verify", {
            method: "POST", body: JSON.stringify({ email, code, clientId: U.clientId() }),
          });
          renderAccountSlot();
          U.toast("You are signed in.");
          close(true);
        } catch (err) {
          showError("code", err.message);
        } finally {
          busy("code", false);
        }
      });
      el.querySelector("#auth-code").addEventListener("input", (e) => {
        const v = e.target.value.replace(/\D/g, "").slice(0, 6);
        e.target.value = v;
        if (v.length === 6) el.querySelector('[data-form="code"]').requestSubmit();
      });
      el.querySelector("[data-back]").addEventListener("click", () => { step("email"); el.querySelector("#auth-email").focus(); });
      const resend = el.querySelector("[data-resend]");
      resend.addEventListener("click", async () => {
        resend.disabled = true;
        if (await sendCode()) U.toast("A new code is on its way.");
        setTimeout(() => { resend.disabled = false; }, 30000);
      });
      const g = el.querySelector("[data-google]");
      if (g) {
        g.addEventListener("click", () => {
          try { sessionStorage.setItem("mockexam:afterLogin", location.hash || "#/"); } catch (e) { /* ignore */ }
          location.href = "/api/auth/google";
        });
      }
      el.querySelector("#auth-email").focus();
    });
  }

  async function logout() {
    await U.api("/api/auth/logout", { method: "POST", body: "{}" }).catch(() => {});
    state.me = { user: null };
    renderAccountSlot();
    U.toast("You are signed out.");
    location.hash = "#/";
  }

  /* ================================================================ plan, paywall, checkout */
  async function paywall(test) {
    const b = await billing().catch(() => null);
    const price = b ? money(b.prices.plan) : "";
    const signedIn = Boolean(user());
    const ok = await U.modal({
      title: "This test is part of the monthly plan",
      bodyHTML: `
        <p><strong>${esc(test ? test.title : "This test")}</strong> is included in the monthly plan${price ? ` (${esc(price)} a month)` : ""}.
          Test 1 of each module is free.</p>
        <ul class="plan-points">
          <li>Every Listening, Reading, Writing and Speaking test, with new tests added regularly</li>
          <li>Full results, answer explanations and listening transcripts</li>
          <li>Your first payment gives you <strong>two months</strong>: one paid, one free</li>
        </ul>
        ${signedIn ? "" : `<p class="muted-text">Already have the plan? Sign in to continue.</p>`}`,
      buttons: [
        ...(signedIn ? [] : [{ label: "Sign in", className: "btn-secondary", value: "signin" }]),
        { label: "See the plan", className: "btn-primary", value: "pricing" },
      ],
    });
    if (ok === "signin") return login();
    if (ok === "pricing") location.hash = "#/pricing";
    return false;
  }

  function chooseMethod(order, b) {
    const labels = {
      payme: ["Payme", "Pay with the Payme app or any Uzcard / Humo card"],
      click: ["Click", "Pay with the Click app or any Uzcard / Humo card"],
      manual: ["Bank card transfer", "Transfer to our card, then press “I have paid”. We confirm within a few hours."],
    };
    if (!b.providers.length) {
      const contact = state.config.contactEmail;
      U.modal({
        title: "Payments are being set up",
        bodyHTML: `<p>Online payment is not switched on yet. ${contact ? `Please write to <a href="mailto:${esc(contact)}">${esc(contact)}</a> and we will activate your order <strong>#MX${order.id}</strong>.` : "Please try again soon."}</p>`,
      });
      return Promise.resolve(null);
    }
    return U.modal({
      title: `Pay ${money(order.amount)}`,
      bodyHTML: `<p class="muted-text">${esc(order.title)} · order #MX${order.id}</p>
        <div class="pay-methods">${b.providers.map((p) => `
          <button type="button" class="pay-method" data-method="${p}">
            <span class="pay-method-name">${esc(labels[p][0])}</span><span class="pay-method-note">${esc(labels[p][1])}</span>
          </button>`).join("")}</div>`,
      buttons: [{ label: "Cancel", className: "btn-secondary", value: null }],
      onOpen: (root, close) => root.querySelectorAll("[data-method]").forEach((btn) =>
        btn.addEventListener("click", () => close(btn.dataset.method))),
    });
  }

  async function manualTransfer(order, info) {
    const ok = await U.modal({
      title: "Pay by card transfer",
      bodyHTML: `
        <ol class="transfer-steps">
          <li>Open your bank app and transfer exactly <strong>${esc(money(info.amount))}</strong> to this card:
            <div class="card-number"><span>${esc(info.cardNumber)}</span>
              <button type="button" class="btn-link" data-copy="${esc(info.cardNumber.replace(/\s+/g, ""))}">Copy</button></div>
            ${info.cardHolder ? `<div class="muted-text">Card holder: ${esc(info.cardHolder)}</div>` : ""}</li>
          <li>In the payment comment write <strong>${esc(info.reference)}</strong> so we can find your payment.</li>
          <li>Press <strong>I have paid</strong>. We check payments several times a day and activate your order.</li>
        </ol>`,
      buttons: [
        { label: "Later", className: "btn-secondary", value: false },
        { label: "I have paid", className: "btn-primary", value: true },
      ],
      onOpen: (root) => root.querySelectorAll("[data-copy]").forEach((b) => b.addEventListener("click", () => {
        navigator.clipboard && navigator.clipboard.writeText(b.dataset.copy).then(() => U.toast("Card number copied."));
      })),
    });
    if (!ok) return;
    await U.api(`/api/orders/${order.id}/manual-paid`, { method: "POST", body: "{}" });
    U.toast("Thank you! We will confirm your payment soon.");
    location.hash = "#/account";
  }

  async function buy(kind, extra = {}) {
    if (!(await login(kind === "plan" ? "Sign in to get the plan. Your plan works on every device where you sign in." : "Sign in to order an examiner check."))) return;
    try {
      const b = await billing();
      const { order } = await U.api("/api/orders", { method: "POST", body: JSON.stringify({ kind, ...extra }) });
      const method = await chooseMethod(order, b);
      if (!method) return;
      const res = await U.api(`/api/orders/${order.id}/pay`, { method: "POST", body: JSON.stringify({ method }) });
      if (res.redirect) {
        U.loadingOverlay("Opening the payment page…", "You will come back here after paying.");
        location.href = res.redirect;
      } else if (res.manual) {
        await manualTransfer(order, res.manual);
      }
    } catch (err) {
      U.modal({ title: "Could not start the payment", bodyHTML: `<p>${esc(err.message)}</p>` });
    }
  }

  /* ================================================================ pricing */
  async function renderPricing(main) {
    document.title = `Prices – ${state.config.siteName || "MockExam"}`;
    main.innerHTML = `<section class="page"><p class="muted-text">Loading…</p></section>`;
    const b = await billing().catch(() => ({ prices: {}, providers: [] }));
    const plan = state.me.plan;
    main.innerHTML = `
      <section class="page pricing-page">
        <div class="hero">
          <h1>Simple prices</h1>
          <p>Start free. Get the plan when you want every test, and pay an examiner only when you want personal feedback.</p>
        </div>
        <div class="price-grid">
          <article class="price-card">
            <div class="price-kicker">Free trial</div>
            <div class="price-amount">0 <span>so'm</span></div>
            <ul class="plan-points">
              <li>Test 1 of Listening, Reading, Writing and Speaking</li>
              <li>Instant scores, explanations and transcripts</li>
              <li>Record your Speaking answers and listen back</li>
            </ul>
            <a class="btn-secondary btn-lg" href="#/">Start a free test</a>
          </article>
          <article class="price-card is-featured">
            <div class="price-flag">First month + 1 month free</div>
            <div class="price-kicker">Monthly plan</div>
            <div class="price-amount">${esc(money(b.prices.plan).replace(" so'm", ""))} <span>so'm / month</span></div>
            <ul class="plan-points">
              <li><strong>All</strong> Listening, Reading, Writing and Speaking tests</li>
              <li>New tests added regularly</li>
              <li>Your results and progress on every device</li>
              <li>Your first payment gives you <strong>2 months</strong></li>
              <li>No automatic charges: renew when you want</li>
            </ul>
            ${plan && plan.active
              ? `<p class="plan-active">Your plan is active until <strong>${esc(longDate(plan.endsAt))}</strong>.</p>
                 <button type="button" class="btn-secondary btn-lg" data-action="buy-plan">Add another month</button>`
              : `<button type="button" class="btn-primary btn-lg" data-action="buy-plan">Get the plan</button>`}
          </article>
          <article class="price-card">
            <div class="price-kicker">Examiner checks</div>
            <div class="price-lines">
              <div><span>Writing check</span><strong>${esc(money(b.prices.writing_check))}</strong></div>
              <div><span>Speaking check</span><strong>${esc(money(b.prices.speaking_check))}</strong></div>
            </div>
            <ul class="plan-points">
              <li>You choose your examiner by rating and reviews</li>
              <li>Band scores on the four official criteria</li>
              <li>Personal feedback and corrections</li>
              <li>Rate your examiner after every check</li>
            </ul>
            <a class="btn-secondary btn-lg" href="#/examiners">Meet the examiners</a>
          </article>
        </div>
        <p class="pay-note">Pay with ${esc(["Payme", "Click", "a bank card transfer"].filter((_, i) =>
          b.providers.includes(["payme", "click", "manual"][i])).join(", ") || "Payme or Click")}. Prices include all fees.</p>
        <div class="faq">
          <h2 class="section-title">Questions</h2>
          <details><summary>Does the plan renew automatically?</summary>
            <p>No. Nothing is charged automatically. When your month ends, you can pay for another month. Your very first payment gives you two months.</p></details>
          <details><summary>How does an examiner check work?</summary>
            <p>Finish a Writing or Speaking test while signed in. On your results page, choose an examiner and pay. The examiner reads
              your essays or listens to your recorded answers, usually within 48 hours, and you see the bands and feedback in your account.
              You can rate the examiner once for each check.</p></details>
          <details><summary>Do I need the plan to order an examiner check?</summary>
            <p>No. You can order a check for any test you have taken, including the free tests.</p></details>
          <details><summary>Can I get a refund?</summary>
            <p>If an examiner has not started your check yet, we can refund it. Contact us with your order number.</p></details>
        </div>
      </section>`;
  }

  /* ================================================================ account */
  async function renderAccount(main) {
    document.title = `My account – ${state.config.siteName || "MockExam"}`;
    await refreshMe();
    if (!user()) {
      main.innerHTML = `<section class="page"><h1>My account</h1><p class="lead-text">Sign in to see your plan, your examiner checks and your results.</p>
        <button type="button" class="btn-primary btn-lg" data-action="signin">Sign in</button></section>`;
      return;
    }
    const u = user();
    const plan = state.me.plan;
    main.innerHTML = `<section class="page account-page"><p class="muted-text">Loading…</p></section>`;
    const [ordersRes, checksRes, progressRes] = await Promise.all([
      U.api("/api/orders").catch(() => ({ orders: [] })),
      U.api("/api/checks").catch(() => ({ checks: [] })),
      U.api("/api/progress").catch(() => ({ points: [] })),
    ]);
    const orders = ordersRes.orders || [];
    const waiting = orders.filter((o) => o.status === "awaiting_confirmation");
    main.innerHTML = `
      <section class="page account-page">
        <div class="account-head">
          <div class="avatar big" aria-hidden="true">${esc(initials(u.name || u.email))}</div>
          <div>
            <h1>${esc(u.name || "My account")}</h1>
            <p class="muted-text">${esc(u.email)}${u.role !== "student" ? ` · ${esc(u.role)}` : ""}</p>
          </div>
          <button type="button" class="btn-secondary" data-action="signout">Sign out</button>
        </div>
        ${waiting.length ? `<div class="notice notice-info"><strong>We are checking your payment.</strong>
          <span>${waiting.map((o) => `Order #MX${o.id} (${esc(money(o.amount))})`).join(", ")} will be activated as soon as we see the transfer.</span></div>` : ""}

        <div class="account-grid">
          <div class="account-card">
            <h2>Your plan</h2>
            ${plan && plan.active
              ? `<p class="plan-active">Active until <strong>${esc(longDate(plan.endsAt))}</strong></p>
                 <p class="muted-text">All tests are open to you.</p>
                 <button type="button" class="btn-secondary" data-action="buy-plan">Add another month</button>`
              : `<p>You are using the free tests.</p>
                 <p class="muted-text">${plan && plan.hadPaidPlan ? "Your plan has ended." : "Your first payment gives you two months."}</p>
                 <button type="button" class="btn-primary" data-action="buy-plan">Get the plan</button>`}
          </div>
          <div class="account-card">
            <h2>Your name</h2>
            <form id="name-form" class="inline-form">
              <label class="sr-only" for="acc-name">Name</label>
              <input id="acc-name" maxlength="80" value="${esc(u.name || "")}" placeholder="Your name" />
              <button type="submit" class="btn-secondary">Save</button>
            </form>
            <p class="muted-text small-text">Examiners see this name on your checks.</p>
          </div>
        </div>

        <section class="progress-section" id="progress-section"></section>

        <h2 class="section-title">Examiner checks</h2>
        ${(checksRes.checks || []).length ? `
          <div class="table-scroll"><table class="history-table">
            <thead><tr><th scope="col">Date</th><th scope="col">Check</th><th scope="col">Examiner</th><th scope="col">Status</th><th scope="col"></th></tr></thead>
            <tbody>${checksRes.checks.map((c) => `
              <tr><td>${esc(U.formatDate(c.createdAt))}</td><td>${c.kind === "writing" ? "Writing" : "Speaking"}</td>
                <td>${esc(c.examinerName || "")}</td>
                <td>${statusBadge(c.status)}${c.overallBand != null ? ` <strong>Band ${IeltsScoring.formatBand(c.overallBand)}</strong>` : ""}</td>
                <td><a href="#/check/${c.id}">Open</a></td></tr>`).join("")}</tbody>
          </table></div>`
          : `<p class="empty-inline">No checks yet. Finish a Writing or Speaking test while signed in, then choose an examiner on your results page.</p>`}

        <section id="history-section" hidden></section>

        <h2 class="section-title">Payments</h2>
        ${orders.length ? `
          <div class="table-scroll"><table class="history-table">
            <thead><tr><th scope="col">Date</th><th scope="col">Order</th><th scope="col">Item</th><th scope="col">Amount</th><th scope="col">Status</th></tr></thead>
            <tbody>${orders.map((o) => `
              <tr><td>${esc(U.formatDate(o.createdAt))}</td><td>#MX${o.id}</td><td>${esc(o.title)}</td>
                <td>${esc(money(o.amount))}</td><td>${statusBadge(o.status)}</td></tr>`).join("")}</tbody>
          </table></div>` : `<p class="empty-inline">No payments yet.</p>`}
      </section>`;
    main.querySelector("#name-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      state.me = await U.api("/api/me", { method: "POST", body: JSON.stringify({ name: main.querySelector("#acc-name").value }) });
      renderAccountSlot();
      U.toast("Saved.");
    });
    Progress.render(main.querySelector("#progress-section"), progressRes.points || []);
    if (window.app) window.app.loadHistory();
  }

  /* ================================================================ examiners */
  function examinerCard(e, ctx) {
    return `
      <article class="examiner-card">
        <div class="examiner-top">
          <span class="avatar big" aria-hidden="true">${esc(initials(e.name))}</span>
          <div>
            <h3>${esc(e.name)}</h3>
            ${e.headline ? `<p class="examiner-headline">${esc(e.headline)}</p>` : ""}
            <p class="examiner-rating">${e.rating != null ? `${stars(e.rating)} <strong>${e.rating.toFixed(1)}</strong> <span class="muted-text">(${e.reviews} review${e.reviews === 1 ? "" : "s"})</span>` : `<span class="muted-text">New examiner – no reviews yet</span>`}</p>
          </div>
        </div>
        <div class="examiner-tags">
          ${e.doesWriting ? `<span class="tag">Writing</span>` : ""}${e.doesSpeaking ? `<span class="tag">Speaking</span>` : ""}
          <span class="tag tag-muted">${e.checksDone} check${e.checksDone === 1 ? "" : "s"} done</span>
          ${e.queue ? `<span class="tag tag-muted">${e.queue} in queue</span>` : ""}
        </div>
        ${e.bio ? `<p class="examiner-bio">${esc(e.bio)}</p>` : ""}
        <div class="examiner-actions">
          <button type="button" class="btn-link" data-action="examiner-reviews" data-id="${esc(e.id)}">Reviews</button>
          <button type="button" class="btn-primary" data-action="choose-examiner" data-id="${esc(e.id)}" data-kind="${ctx.kind}"
            ${ctx && ctx.submission ? `data-submission="${Number(ctx.submission)}"` : ""}>Choose</button>
        </div>
      </article>`;
  }

  async function renderExaminers(main, params) {
    document.title = `Examiners – ${state.config.siteName || "MockExam"}`;
    const submission = Number(params.get("submission")) || null;
    const kind = params.get("kind") === "speaking" ? "speaking" : "writing";
    main.innerHTML = `<section class="page"><p class="muted-text">Loading…</p></section>`;
    const [{ examiners }, b] = await Promise.all([U.api(`/api/examiners?kind=${kind}`), billing()]);
    const skill = kind === "speaking" ? "Speaking" : "Writing";
    main.innerHTML = `
      <section class="page examiners-page">
        <h1>Choose your examiner</h1>
        ${submission ? "" : `<div class="review-tabs admin-tabs">
          <a class="review-tab-btn ${kind === "writing" ? "active" : ""}" href="#/examiners?kind=writing">Writing</a>
          <a class="review-tab-btn ${kind === "speaking" ? "active" : ""}" href="#/examiners?kind=speaking">Speaking</a></div>`}
        <p class="lead-text">${kind === "speaking"
          ? "Our examiners listen to your recorded answers, give a band for each of the four official Speaking criteria and tell you how to improve."
          : "Our examiners mark your writing on the four official criteria and give you personal feedback."}
          A ${skill} check costs <strong>${esc(money(b.prices[`${kind}_check`]))}</strong>.
          ${submission ? "Choose an examiner for the test you just finished." : `Choose an examiner, then pick which of your ${skill} tests to send.`}</p>
        ${examiners.length
          ? `<div class="examiner-grid">${examiners.map((e) => examinerCard(e, { submission, kind })).join("")}</div>`
          : `<div class="notice notice-info"><strong>${skill} examiners are joining soon.</strong><span>Check back in a few days.</span></div>`}
      </section>`;
  }

  async function showReviews(examinerId) {
    const { examiner, reviews } = await U.api(`/api/examiners/${encodeURIComponent(examinerId)}`);
    U.modal({
      title: examiner.name,
      bodyHTML: `
        ${examiner.headline ? `<p><strong>${esc(examiner.headline)}</strong></p>` : ""}
        ${examiner.bio ? `<p>${esc(examiner.bio)}</p>` : ""}
        <h4 class="reviews-title">Reviews</h4>
        ${reviews.length ? `<ul class="review-items">${reviews.map((r) => `
          <li>${stars(r.rating)} <span class="muted-text">${esc(U.formatDate(r.date))}</span>${r.review ? `<p>${esc(r.review)}</p>` : ""}</li>`).join("")}</ul>`
          : `<p class="muted-text">No reviews yet.</p>`}`,
    });
  }

  async function chooseExaminer(examinerId, submissionId, kind = "writing") {
    if (!(await login("Sign in to order an examiner check."))) return;
    const skill = kind === "speaking" ? "Speaking" : "Writing";
    let submission = submissionId;
    if (!submission) {
      const { items } = await U.api(`/api/history?clientId=${encodeURIComponent(U.clientId())}`);
      const done = (items || []).filter((i) => i.module === kind && (kind !== "speaking" || (i.answered && !i.checkId)));
      if (!done.length) {
        U.modal({
          title: `Take a ${skill} test first`,
          bodyHTML: `<p>Finish a ${skill} test while you are signed in. Then choose an examiner on your results page.</p>`,
          buttons: [{ label: "OK", className: "btn-primary", value: true }],
        });
        return;
      }
      const titleOf = (id) => ((window.app && window.app.tests) || []).find((t) => t.id === id);
      submission = await U.modal({
        title: `Which ${skill.toLowerCase()} test should be marked?`,
        bodyHTML: `<div class="pick-list">${done.map((w) => {
          const t = titleOf(w.testId);
          return `<button type="button" class="pick-item" data-pick="${Number(w.id)}">
            <strong>${esc(t ? t.shortTitle : w.testId)}</strong>
            <span class="muted-text">${esc(U.formatDate(w.createdAt))} · ${kind === "speaking" ? `${w.answered} answers` : `${w.task1Words} + ${w.task2Words} words`}</span></button>`;
        }).join("")}</div>`,
        buttons: [{ label: "Cancel", className: "btn-secondary", value: null }],
        onOpen: (root, close) => root.querySelectorAll("[data-pick]").forEach((b) =>
          b.addEventListener("click", () => close(Number(b.dataset.pick)))),
      });
      if (!submission) return;
    }
    await buy(`${kind}_check`, { examinerId, submissionId: submission });
  }

  /* ================================================================ one check */
  const CRIT = {
    writing: ["task", "coherence_cohesion", "lexical_resource", "grammar"],
  };
  const CRIT_LABELS = {
    1: { task: "Task Achievement", coherence_cohesion: "Coherence and Cohesion", lexical_resource: "Lexical Resource", grammar: "Grammatical Range and Accuracy" },
    2: { task: "Task Response", coherence_cohesion: "Coherence and Cohesion", lexical_resource: "Lexical Resource", grammar: "Grammatical Range and Accuracy" },
  };
  const roundHalf = (v) => {
    const w = Math.floor(v);
    const f = v - w;
    return f < 0.25 ? w : f < 0.75 ? w + 0.5 : w + 1;
  };

  function submissionHTML(sub, open, examiner) {
    if (sub && sub.parts) return Speaking.submissionHTML(sub, { open, examiner });
    if (!sub || !sub.tasks) return "";
    return sub.tasks.map((t) => `
      <details class="fold" ${open ? "open" : ""}><summary>Task ${t.taskNumber}: ${esc(t.title)} · ${t.words} words (minimum ${t.minWords || "–"})</summary>
        <div class="check-task">
          <div class="task-prompt">${U.paragraphs(t.prompt)}</div>${TaskCharts.render(t.visual)}
          <h4>Candidate's answer</h4>
          <div class="essay-text">${t.response ? U.paragraphs(t.response) : "<p><em>No answer.</em></p>"}</div>
        </div>
      </details>`).join("");
  }

  function resultHTML(result) {
    const P = Results.parts;
    return `
      ${result.comment ? `<div class="examiner-comment"><h3>Message from your examiner</h3><p>${esc(result.comment)}</p></div>` : ""}
      ${["1", "2"].map((n) => {
        const t = result.tasks[n];
        return `
          <section class="task-result">
            <div class="task-result-head"><h2 class="section-title">Task ${n}</h2><span class="task-band">Band ${IeltsScoring.formatBand(t.band)}</span></div>
            ${t.summary ? `<p class="lead-text">${esc(t.summary)}</p>` : ""}
            ${P.criteriaHTML(t)}
            <div class="feedback-columns">${P.listBlock("What you did well", t.strengths, "good")}${P.listBlock("How to improve", t.improvements, "improve")}</div>
            ${P.correctionsHTML(t.corrections)}
          </section>`;
      }).join("")}`;
  }

  async function renderCheck(main, id) {
    document.title = `Examiner check – ${state.config.siteName || "MockExam"}`;
    if (!(await refreshMe()).user) {
      main.innerHTML = `<section class="page"><p class="lead-text">Sign in to see this check.</p>
        <button type="button" class="btn-primary" data-action="signin">Sign in</button></section>`;
      return;
    }
    let check;
    try {
      ({ check } = await U.api(`/api/checks/${encodeURIComponent(id)}`));
    } catch (err) {
      main.innerHTML = `<section class="page"><h1>Check not found</h1><p>${esc(err.message)}</p></section>`;
      return;
    }
    if (check.viewerRole === "examiner" && check.status === "waiting") {
      await U.api(`/api/examiner/checks/${check.id}/start`, { method: "POST", body: "{}" }).catch(() => {});
      check.status = "in_progress";
    }
    const sub = check.submission || {};
    const head = `
      <div class="results-head">
        <div>
          <div class="eyebrow">${check.kind === "writing" ? "Writing" : "Speaking"} check #${check.id}</div>
          <h1>${esc(sub.title || "")}</h1>
          <p class="muted-text">${check.viewerRole === "student" ? `Examiner: ${esc(check.examinerName || "")}` : `Candidate: ${esc(sub.candidateName || "")}`}
            · ordered ${esc(U.formatDate(check.createdAt))}</p>
        </div>
        <div>${statusBadge(check.status)}</div>
      </div>`;

    const speaking = check.kind === "speaking";
    const work = check.viewerRole === "student" ? (speaking ? "Your answers" : "Your writing")
      : (speaking ? "The candidate's answers" : "The candidate's writing");
    if (check.viewerRole !== "student" && check.status !== "completed" && check.status !== "cancelled") {
      main.innerHTML = `<section class="results-page check-page">${head}
        <div class="check-layout">
          <div class="check-work">${submissionHTML(sub, true, true)}</div>
          <form class="mark-form" id="mark-form" novalidate></form>
        </div></section>`;
      if (speaking) Speaking.markForm(main.querySelector("#mark-form"), check, { roundHalf });
      else renderMarkForm(main.querySelector("#mark-form"), check);
      return;
    }

    if (check.status !== "completed") {
      main.innerHTML = `<section class="results-page check-page">${head}
        <div class="notice notice-info"><strong>${check.status === "cancelled" ? "This check was cancelled." : "Your examiner is working on it."}</strong>
          <span>${check.status === "cancelled" ? "If you paid, the money has been or will be refunded." : "Most checks are finished within 48 hours. We will show the result here and in your account."}</span></div>
        <h2 class="section-title">${work}</h2>${submissionHTML(sub, false)}</section>`;
      return;
    }

    const r = check.result;
    const canRate = check.viewerRole === "student" && !check.rating;
    main.innerHTML = `
      <section class="results-page check-page">${head}
        <div class="score-banner-card">
          ${Results.parts.bandCircle(r.overallBand, "Examiner band")}
          <div class="score-details-grid">
            ${speaking
              ? Object.values(r.criteria).map((c) => `<div class="score-stat-box"><div class="score-stat-val">${c.band}</div><div class="score-stat-lbl">${esc(c.label)}</div></div>`).join("")
              : `<div class="score-stat-box"><div class="score-stat-val">${IeltsScoring.formatBand(r.tasks["1"].band)}</div><div class="score-stat-lbl">Task 1</div></div>
                 <div class="score-stat-box"><div class="score-stat-val">${IeltsScoring.formatBand(r.tasks["2"].band)}</div><div class="score-stat-lbl">Task 2 (counts double)</div></div>`}
            <div class="score-stat-box"><div class="score-stat-val">${esc(check.examinerName || "")}</div><div class="score-stat-lbl">Examiner</div></div>
          </div>
        </div>
        <p class="score-note">A practice band from an experienced examiner, using the four public ${speaking ? "Speaking" : "Writing"} criteria. It is not an official IELTS result.</p>
        ${canRate ? `
          <form class="rate-box" id="rate-form">
            <h2>How helpful was your examiner?</h2>
            <div class="star-input" role="radiogroup" aria-label="Rating">
              ${[5, 4, 3, 2, 1].map((v) => `<label><input type="radio" name="rating" value="${v}" /><span aria-hidden="true">★</span><span class="sr-only">${v} star${v === 1 ? "" : "s"}</span></label>`).join("")}
            </div>
            <label class="sr-only" for="rate-text">Review</label>
            <textarea id="rate-text" maxlength="1000" placeholder="Optional: what was useful? What could be better?"></textarea>
            <p class="muted-text small-text">You can review each check once. Other students see your stars and comment, but not your name.</p>
            <button type="submit" class="btn-primary">Send review</button>
          </form>`
          : check.rating ? `<div class="rate-box done"><strong>Your review:</strong> ${stars(check.rating)} ${check.review ? `<p>${esc(check.review)}</p>` : ""}</div>` : ""}
        ${speaking ? Speaking.resultHTML(r) : resultHTML(r)}
        <h2 class="section-title">${work}</h2>
        ${submissionHTML(sub, false, check.viewerRole !== "student")}
      </section>`;
    const form = main.querySelector("#rate-form");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const picked = form.querySelector("input[name=rating]:checked");
        if (!picked) return U.toast("Choose from 1 to 5 stars.", "warn");
        try {
          await U.api(`/api/checks/${check.id}/rate`, {
            method: "POST", body: JSON.stringify({ rating: Number(picked.value), review: form.querySelector("#rate-text").value }),
          });
          U.toast("Thank you for your review.");
          renderCheck(main, check.id);
        } catch (err) {
          U.toast(err.message, "warn");
        }
      });
    }
  }

  function renderMarkForm(form, check) {
    const draftKey = `mockexam:mark:${check.id}`;
    const draft = U.store.get(draftKey, null);
    const bandOptions = (sel) => `<option value="">–</option>${[9, 8, 7, 6, 5, 4, 3, 2, 1, 0].map((b) =>
      `<option value="${b}" ${String(sel) === String(b) ? "selected" : ""}>${b}</option>`).join("")}`;
    const d = (n, path, fallback = "") => {
      try { return path.reduce((o, k) => o[k], draft.tasks[n]) ?? fallback; } catch (e) { return fallback; }
    };
    form.innerHTML = `
      <h2>Your marks</h2>
      <p class="muted-text small-text">Give each criterion a whole band. Task bands and the overall band are calculated for you
        (Task 2 counts double). Your draft is saved in this browser.</p>
      ${[1, 2].map((n) => `
        <fieldset class="mark-task" data-task="${n}">
          <legend>Task ${n} <span class="mark-band" data-band="${n}">–</span></legend>
          ${CRIT.writing.map((k) => `
            <div class="mark-crit">
              <label for="b-${n}-${k}">${esc(CRIT_LABELS[n][k])}</label>
              <select id="b-${n}-${k}" data-band-of="${n}:${k}">${bandOptions(d(n, ["criteria", k, "band"]))}</select>
              <textarea data-feedback-of="${n}:${k}" rows="2" maxlength="1500" placeholder="Feedback on this criterion">${esc(d(n, ["criteria", k, "feedback"]))}</textarea>
            </div>`).join("")}
          <label>Summary <textarea data-field="${n}:summary" rows="2" maxlength="1500">${esc(d(n, ["summary"]))}</textarea></label>
          <label>What the candidate did well <span class="muted-text">(one point per line)</span>
            <textarea data-field="${n}:strengths" rows="3">${esc([].concat(d(n, ["strengths"], [])).join("\n"))}</textarea></label>
          <label>How to improve <span class="muted-text">(one point per line)</span>
            <textarea data-field="${n}:improvements" rows="3">${esc([].concat(d(n, ["improvements"], [])).join("\n"))}</textarea></label>
          <div class="corrections" data-corrections="${n}">
            <div class="corrections-head"><span>Corrections</span>
              <button type="button" class="btn-link" data-add-correction="${n}">+ Add a correction</button></div>
          </div>
        </fieldset>`).join("")}
      <label>Message to the candidate <textarea id="mark-comment" rows="3" maxlength="4000">${esc((draft && draft.comment) || "")}</textarea></label>
      <div class="mark-total">Overall writing band: <strong id="mark-overall">–</strong></div>
      <p class="form-error" role="alert" hidden></p>
      <button type="submit" class="btn-primary btn-lg">Send marks to the candidate</button>`;

    const addCorrection = (n, c = {}) => {
      const row = document.createElement("div");
      row.className = "correction-row";
      row.innerHTML = `
        <input data-c="original" maxlength="300" placeholder="Candidate wrote" value="${esc(c.original || "")}" />
        <input data-c="corrected" maxlength="300" placeholder="Better" value="${esc(c.corrected || "")}" />
        <input data-c="explanation" maxlength="400" placeholder="Why" value="${esc(c.explanation || "")}" />
        <button type="button" class="btn-link" data-remove aria-label="Remove correction">Remove</button>`;
      row.querySelector("[data-remove]").addEventListener("click", () => { row.remove(); save(); });
      form.querySelector(`[data-corrections="${n}"]`).appendChild(row);
    };
    [1, 2].forEach((n) => (d(n, ["corrections"], []) || []).forEach((c) => addCorrection(n, c)));

    const collect = () => {
      const tasks = {};
      [1, 2].forEach((n) => {
        const criteria = {};
        CRIT.writing.forEach((k) => {
          criteria[k] = {
            band: form.querySelector(`[data-band-of="${n}:${k}"]`).value,
            feedback: form.querySelector(`[data-feedback-of="${n}:${k}"]`).value,
          };
        });
        const lines = (f) => form.querySelector(`[data-field="${n}:${f}"]`).value.split("\n").map((s) => s.trim()).filter(Boolean);
        tasks[n] = {
          criteria,
          summary: form.querySelector(`[data-field="${n}:summary"]`).value,
          strengths: lines("strengths"),
          improvements: lines("improvements"),
          corrections: [...form.querySelectorAll(`[data-corrections="${n}"] .correction-row`)].map((r) => ({
            original: r.querySelector('[data-c="original"]').value,
            corrected: r.querySelector('[data-c="corrected"]').value,
            explanation: r.querySelector('[data-c="explanation"]').value,
          })).filter((c) => c.original.trim() && c.corrected.trim()),
        };
      });
      return { tasks, comment: form.querySelector("#mark-comment").value };
    };
    const updateBands = () => {
      const r = collect();
      const bands = [1, 2].map((n) => {
        const vals = CRIT.writing.map((k) => r.tasks[n].criteria[k].band).filter((v) => v !== "").map(Number);
        const band = vals.length === 4 ? roundHalf(vals.reduce((a, b) => a + b, 0) / 4) : null;
        form.querySelector(`[data-band="${n}"]`).textContent = band === null ? "–" : `Band ${IeltsScoring.formatBand(band)}`;
        return band;
      });
      form.querySelector("#mark-overall").textContent = bands.every((b) => b !== null)
        ? IeltsScoring.formatBand(roundHalf((bands[0] + 2 * bands[1]) / 3)) : "–";
    };
    let saveTimer = null;
    const save = () => {
      clearTimeout(saveTimer);
      saveTimer = setTimeout(() => U.store.set(draftKey, collect()), 300);
      updateBands();
    };
    form.addEventListener("input", save);
    form.addEventListener("change", save);
    form.querySelectorAll("[data-add-correction]").forEach((b) =>
      b.addEventListener("click", () => { addCorrection(b.dataset.addCorrection); save(); }));
    updateBands();

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const result = collect();
      const missing = [1, 2].some((n) => CRIT.writing.some((k) => result.tasks[n].criteria[k].band === ""));
      const err = form.querySelector(".form-error");
      if (missing) {
        err.textContent = "Give a band for every criterion in both tasks.";
        err.hidden = false;
        return;
      }
      err.hidden = true;
      const ok = await U.modal({
        title: "Send the marks?",
        bodyHTML: `<p>The candidate will see your bands and feedback straight away. You cannot change them afterwards.</p>`,
        buttons: [{ label: "Keep editing", className: "btn-secondary", value: false }, { label: "Send", className: "btn-primary", value: true }],
      });
      if (!ok) return;
      try {
        await U.api(`/api/examiner/checks/${check.id}/result`, { method: "POST", body: JSON.stringify({ result }) });
        U.store.remove(draftKey);
        U.toast("Marks sent. Thank you!");
        location.hash = "#/examiner";
      } catch (e2) {
        err.textContent = e2.message;
        err.hidden = false;
      }
    });
  }

  /* ================================================================ examiner dashboard */
  async function renderExaminerDashboard(main) {
    document.title = `Examiner – ${state.config.siteName || "MockExam"}`;
    await refreshMe();
    if (!["examiner", "admin"].includes(role())) {
      main.innerHTML = `<section class="page"><h1>Examiners only</h1><p>This page is for examiners. Want to mark for us? Contact the site owner.</p></section>`;
      return;
    }
    let data;
    try {
      data = await U.api("/api/examiner/me");
    } catch (err) {
      main.innerHTML = `<section class="page"><p>${esc(err.message)}</p></section>`;
      return;
    }
    const e = data.examiner;
    const open = data.checks.filter((c) => c.status !== "completed");
    const done = data.checks.filter((c) => c.status === "completed").reverse();
    const row = (c) => `<tr><td>#${c.id}</td><td>${c.kind === "writing" ? "Writing" : "Speaking"}</td>
      <td>${esc(U.formatDate(c.createdAt))}</td><td>${statusBadge(c.status)}${c.overallBand != null ? ` Band ${IeltsScoring.formatBand(c.overallBand)}` : ""}</td>
      <td>${c.rating ? stars(c.rating) : ""}</td><td><a href="#/check/${c.id}">${c.status === "completed" ? "View" : "Mark"}</a></td></tr>`;
    main.innerHTML = `
      <section class="page examiner-page">
        <h1>Examiner dashboard</h1>
        ${!e ? `<div class="notice notice-info"><strong>Create your examiner profile.</strong><span>Students see it when they choose an examiner. The site owner approves new profiles.</span></div>`
          : !e.approved ? `<div class="notice notice-warn"><strong>Your profile is waiting for approval.</strong><span>Students will see you once the site owner approves it.</span></div>` : ""}
        ${e ? `<div class="stat-row">
          <div><strong>${e.rating != null ? e.rating.toFixed(1) : "–"}</strong><span>rating (${e.reviews} reviews)</span></div>
          <div><strong>${e.checksDone}</strong><span>checks done</span></div>
          <div><strong>${open.length}</strong><span>waiting for you</span></div>
        </div>` : ""}
        <h2 class="section-title">Checks to mark</h2>
        ${open.length ? `<div class="table-scroll"><table class="history-table"><thead><tr><th>Check</th><th>Type</th><th>Ordered</th><th>Status</th><th></th><th></th></tr></thead>
          <tbody>${open.map(row).join("")}</tbody></table></div>` : `<p class="empty-inline">Nothing to mark right now.</p>`}
        <h2 class="section-title">Your profile</h2>
        <form id="examiner-form" class="examiner-form">
          <label>Name students see <input name="displayName" maxlength="80" required value="${esc(e ? e.name : "")}" /></label>
          <label>Headline <input name="headline" maxlength="80" placeholder="e.g. IELTS 8.5 · 6 years teaching" value="${esc(e ? e.headline : "")}" /></label>
          <label>About you <textarea name="bio" rows="4" maxlength="1200" placeholder="Your experience and how you give feedback">${esc(e ? e.bio : "")}</textarea></label>
          <div class="check-inline">
            <label><input type="checkbox" name="doesWriting" ${!e || e.doesWriting ? "checked" : ""} /> I mark Writing</label>
            <label><input type="checkbox" name="doesSpeaking" ${!e || e.doesSpeaking ? "checked" : ""} /> I mark Speaking</label>
            <label><input type="checkbox" name="accepting" ${!e || e.accepting ? "checked" : ""} /> I am taking new checks</label>
          </div>
          <button type="submit" class="btn-primary">Save profile</button>
        </form>
        ${done.length ? `<h2 class="section-title">Finished checks</h2>
          <div class="table-scroll"><table class="history-table"><thead><tr><th>Check</th><th>Type</th><th>Ordered</th><th>Result</th><th>Review</th><th></th></tr></thead>
          <tbody>${done.slice(0, 50).map(row).join("")}</tbody></table></div>` : ""}
      </section>`;
    main.querySelector("#examiner-form").addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const f = ev.target;
      try {
        await U.api("/api/examiner/me", {
          method: "POST",
          body: JSON.stringify({
            displayName: f.displayName.value, headline: f.headline.value, bio: f.bio.value,
            doesWriting: f.doesWriting.checked, doesSpeaking: f.doesSpeaking.checked, accepting: f.accepting.checked,
          }),
        });
        U.toast("Profile saved.");
        renderExaminerDashboard(main);
      } catch (err) {
        U.toast(err.message, "warn");
      }
    });
  }

  /* ================================================================ admin */
  async function renderAdmin(main, params) {
    document.title = `Admin – ${state.config.siteName || "MockExam"}`;
    await refreshMe();
    if (role() !== "admin") {
      main.innerHTML = `<section class="page"><h1>Admin only</h1><p>Sign in with an admin email to see this page.</p></section>`;
      return;
    }
    const tab = params.get("tab") || "payments";
    const waiting = (state.me.todo || {}).payments || 0;
    const tabs = [["payments", `Payments to confirm${waiting ? ` (${waiting})` : ""}`], ["orders", "All orders"], ["examiners", "Examiners"], ["users", "Users"]];
    main.innerHTML = `
      <section class="page admin-page">
        <h1>Admin</h1>
        <div class="review-tabs admin-tabs">${tabs.map(([k, l]) => `<a class="review-tab-btn ${k === tab ? "active" : ""}" href="#/admin?tab=${k}">${l}</a>`).join("")}</div>
        <div id="admin-body"><p class="muted-text">Loading…</p></div>
      </section>`;
    const body = main.querySelector("#admin-body");
    const act = async (path, label) => {
      try {
        await U.api(path, { method: "POST", body: "{}" });
        U.toast(label);
        await refreshMe();
        renderAdmin(main, params);
      } catch (err) {
        U.toast(err.message, "warn");
      }
    };

    if (tab === "payments" || tab === "orders") {
      const status = tab === "payments" ? "awaiting_confirmation" : params.get("status") || "";
      const { orders } = await U.api(`/api/admin/orders${status ? `?status=${status}` : ""}`);
      body.innerHTML = `
        ${tab === "orders" ? `<div class="admin-filter">Show:
          ${["", "pending", "awaiting_confirmation", "paid", "refunded", "cancelled"].map((s) =>
            `<a href="#/admin?tab=orders${s ? `&status=${s}` : ""}" class="${s === status ? "is-on" : ""}">${s ? esc((STATUS[s] || [s])[0]) : "All"}</a>`).join(" · ")}</div>` : ""}
        ${orders.length ? `<div class="table-scroll"><table class="history-table">
          <thead><tr><th>Date</th><th>Order</th><th>Customer</th><th>Item</th><th>Amount</th><th>Status</th><th></th></tr></thead>
          <tbody>${orders.map((o) => `<tr>
            <td>${esc(U.formatDate(o.createdAt))}</td><td>#MX${o.id}</td><td>${esc(o.userEmail || "")}</td>
            <td>${esc(o.title)}${o.examinerEmail ? `<br><span class="muted-text">${esc(o.examinerEmail)}</span>` : ""}</td>
            <td>${esc(money(o.amount))}</td><td>${statusBadge(o.status)}${o.provider ? ` <span class="muted-text">${esc(o.provider)}</span>` : ""}</td>
            <td class="row-actions">
              ${["pending", "awaiting_confirmation"].includes(o.status) ? `<button type="button" class="btn-primary btn-sm" data-confirm="${o.id}">Confirm payment</button>
                <button type="button" class="btn-secondary btn-sm" data-cancel="${o.id}">Cancel</button>` : ""}
              ${o.status === "paid" ? `<button type="button" class="btn-secondary btn-sm" data-refund="${o.id}">Refund</button>` : ""}
            </td></tr>`).join("")}</tbody></table></div>`
          : `<p class="empty-inline">${tab === "payments" ? "No payments are waiting for confirmation." : "No orders."}</p>`}
        ${tab === "payments" ? `<p class="muted-text small-text">Confirm a card transfer only after you see the money arrive, with the order number (MX…) in the comment.</p>` : ""}`;
      body.querySelectorAll("[data-confirm]").forEach((b) => b.addEventListener("click", () => act(`/api/admin/orders/${b.dataset.confirm}/confirm`, "Payment confirmed.")));
      body.querySelectorAll("[data-cancel]").forEach((b) => b.addEventListener("click", () => act(`/api/admin/orders/${b.dataset.cancel}/cancel`, "Order cancelled.")));
      body.querySelectorAll("[data-refund]").forEach((b) => b.addEventListener("click", async () => {
        const ok = await U.modal({ title: "Refund this order?", bodyHTML: "<p>The plan time or the examiner check is removed. Return the money to the customer yourself (Payme/Click cabinet or bank).</p>",
          buttons: [{ label: "No", className: "btn-secondary", value: false }, { label: "Refund", className: "btn-danger", value: true }] });
        if (ok) act(`/api/admin/orders/${b.dataset.refund}/refund`, "Order refunded.");
      }));
    } else if (tab === "examiners") {
      const { examiners } = await U.api("/api/admin/examiners");
      body.innerHTML = `
        ${examiners.length ? `<div class="table-scroll"><table class="history-table">
          <thead><tr><th>Examiner</th><th>Email</th><th>Rating</th><th>Done</th><th>Queue</th><th>Status</th><th></th></tr></thead>
          <tbody>${examiners.map((e) => `<tr>
            <td><strong>${esc(e.name)}</strong><br><span class="muted-text">${esc(e.headline)}</span></td><td>${esc(e.email || "")}</td>
            <td>${e.rating != null ? `${e.rating.toFixed(1)} (${e.reviews})` : "–"}</td><td>${e.checksDone}</td><td>${e.queue}</td>
            <td>${e.approved ? statusBadge("paid").replace("Paid", "Approved") : statusBadge("awaiting_confirmation").replace("Payment being checked", "Waiting for approval")}
              ${e.accepting ? "" : ` <span class="muted-text">paused</span>`}</td>
            <td><button type="button" class="btn-secondary btn-sm" data-approve="${esc(e.email || "")}" data-on="${e.approved ? 0 : 1}">${e.approved ? "Hide" : "Approve"}</button></td></tr>`).join("")}</tbody></table></div>`
          : `<p class="empty-inline">No examiners yet.</p>`}
        <h2 class="section-title">Add an examiner</h2>
        <p class="muted-text">The examiner must sign in to the site once with this email. Then add them here.</p>
        <form id="add-examiner" class="examiner-form">
          <label>Email <input name="email" type="email" required /></label>
          <label>Name students see <input name="displayName" maxlength="80" /></label>
          <label>Headline <input name="headline" maxlength="80" placeholder="e.g. IELTS 8.5 · 6 years teaching" /></label>
          <label class="check-inline"><input type="checkbox" name="approved" checked /> Approve now</label>
          <button type="submit" class="btn-primary">Add examiner</button>
        </form>`;
      body.querySelectorAll("[data-approve]").forEach((b) => b.addEventListener("click", async () => {
        try {
          await U.api("/api/admin/examiners", { method: "POST", body: JSON.stringify({ email: b.dataset.approve, approved: b.dataset.on === "1" }) });
          renderAdmin(main, params);
        } catch (err) { U.toast(err.message, "warn"); }
      }));
      body.querySelector("#add-examiner").addEventListener("submit", async (ev) => {
        ev.preventDefault();
        const f = ev.target;
        const payload = { email: f.email.value, approved: f.approved.checked };
        if (f.displayName.value.trim()) payload.displayName = f.displayName.value;
        if (f.headline.value.trim()) payload.headline = f.headline.value;
        try {
          await U.api("/api/admin/examiners", { method: "POST", body: JSON.stringify(payload) });
          U.toast("Examiner saved.");
          renderAdmin(main, params);
        } catch (err) { U.toast(err.message, "warn"); }
      });
    } else {
      const q = params.get("q") || "";
      const { users } = await U.api(`/api/admin/users${q ? `?q=${encodeURIComponent(q)}` : ""}`);
      body.innerHTML = `
        <form id="user-search" class="inline-form"><input name="q" placeholder="Search by email" value="${esc(q)}" /><button class="btn-secondary">Search</button></form>
        ${users.length ? `<div class="table-scroll"><table class="history-table">
          <thead><tr><th>Email</th><th>Name</th><th>Role</th><th>Joined</th><th>Plan</th><th>Give plan days</th></tr></thead>
          <tbody>${users.map((u) => `<tr><td>${esc(u.email)}</td><td>${esc(u.name)}</td><td>${esc(u.role)}</td>
            <td>${esc(U.formatDate(u.createdAt))}</td><td>${u.plan.active ? `until ${esc(longDate(u.plan.endsAt))}` : "–"}</td>
            <td><form class="inline-form grant-form" data-email="${esc(u.email)}"><input name="days" type="number" min="1" max="400" value="30" aria-label="Days" />
              <button class="btn-secondary btn-sm">Give</button></form></td></tr>`).join("")}</tbody></table></div>`
          : `<p class="empty-inline">No users found.</p>`}`;
      body.querySelector("#user-search").addEventListener("submit", (ev) => {
        ev.preventDefault();
        location.hash = `#/admin?tab=users&q=${encodeURIComponent(ev.target.q.value.trim())}`;
      });
      body.querySelectorAll(".grant-form").forEach((f) => f.addEventListener("submit", async (ev) => {
        ev.preventDefault();
        try {
          await U.api("/api/admin/plan", { method: "POST", body: JSON.stringify({ email: f.dataset.email, days: Number(f.days.value) }) });
          U.toast("Plan days added.");
          renderAdmin(main, params);
        } catch (err) { U.toast(err.message, "warn"); }
      }));
    }
  }

  /* ================================================================ click handling */
  function onClick(e) {
    const el = e.target.closest("[data-action]");
    if (!el) return false;
    const a = el.dataset.action;
    if (a === "signin") { login().then((ok) => ok && window.app && window.app.route()); return true; }
    if (a === "signout") { logout(); return true; }
    if (a === "buy-plan") { buy("plan"); return true; }
    if (a === "examiner-reviews") { showReviews(el.dataset.id); return true; }
    if (a === "choose-examiner") {
      chooseExaminer(el.dataset.id, Number(el.dataset.submission) || null, el.dataset.kind === "speaking" ? "speaking" : "writing");
      return true;
    }
    if (a === "order-writing-check") { location.hash = `#/examiners?submission=${Number(el.dataset.submission)}`; return true; }
    return false;
  }

  window.Account = {
    state, refreshMe, user, planActive, role, login, logout, paywall, buy, billing, money, onClick,
    renderAccountSlot, renderPricing, renderAccount, renderExaminers, renderCheck, renderExaminerDashboard, renderAdmin,
    setConfig(config) { state.config = config || {}; },
  };
})();
