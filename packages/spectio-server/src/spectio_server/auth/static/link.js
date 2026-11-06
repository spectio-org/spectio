// The bootstrap page of the token link (dev-env §15.3 "Access"; P1 Task 12): take the ticket
// from the fragment, drop it from the address bar and the history, exchange it for the session
// cookie, then open the app.
"use strict";
(function () {
  const ticket = location.hash.slice(1);
  history.replaceState(null, "", location.pathname);
  function expired() {
    document.getElementById("wait").hidden = true;
    document.getElementById("expired").hidden = false;
  }
  if (!ticket) {
    expired();
    return;
  }
  fetch("/api/v1/auth/magic-links:exchange", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticket: ticket }),
    credentials: "same-origin",
  }).then(function (answer) {
    if (answer.ok) {
      location.replace("/");
    } else {
      expired();
    }
  }, expired);
})();
