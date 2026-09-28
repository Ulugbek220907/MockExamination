/**
 * Landing page after Google sign-in or an emailed sign-in link. Supabase puts
 * an access token in the URL fragment; the server checks it and starts our own
 * session, then we return to where the user was.
 */
(function () {
  "use strict";

  const hash = new URLSearchParams(location.hash.slice(1));
  const query = new URLSearchParams(location.search);
  const token = hash.get("access_token");
  const error = hash.get("error_description") || query.get("error_description");
  const title = document.getElementById("cb-title");
  const message = document.getElementById("cb-message");
  const back = document.getElementById("cb-back");

  // Never leave the token in the address bar or the browser history.
  history.replaceState(null, "", location.pathname);

  let next = "#/account";
  try {
    next = sessionStorage.getItem("mockexam:afterLogin") || next;
    sessionStorage.removeItem("mockexam:afterLogin");
  } catch (e) { /* storage blocked */ }
  if (!/^#\/[\w\-/?=&.]*$/.test(next)) next = "#/account";

  let clientId = null;
  try { clientId = JSON.parse(localStorage.getItem("mockexam:clientId")); } catch (e) { /* ignore */ }

  function fail(text) {
    title.textContent = "Sign-in did not work";
    message.textContent = text;
    back.hidden = false;
  }

  if (error) return fail(error.replace(/\+/g, " ") + ". Please try again.");
  if (!token) return fail("This sign-in link has expired or was already used. Please sign in again.");

  fetch("/api/auth/token", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ accessToken: token, clientId }),
  })
    .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
    .then(({ ok, data }) => {
      if (!ok) throw new Error(data.error || "Sign-in failed.");
      title.textContent = "You are signed in";
      message.textContent = "Taking you back…";
      location.replace("/" + next);
    })
    .catch((err) => fail(err.message));
})();
