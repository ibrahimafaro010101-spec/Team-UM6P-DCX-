// assets/app.js
(function () {
  try {
    // Scroll top
    window.scrollTo({ top: 0, behavior: "smooth" });

    // Auto-focus first textarea (NLQ)
    const ta = parent.document.querySelector('textarea');
    if (ta) ta.focus();
  } catch (e) {
    console.log("JS injection ignored:", e);
  }
})();
