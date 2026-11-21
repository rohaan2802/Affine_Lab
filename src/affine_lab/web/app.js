const byId = (id) => document.getElementById(id);
let configuration = null;
const make = (tag, text, className) => {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
};
async function api(path, options) {
  const response = await fetch(path, options);
  const body = await response.json();
  if (!response.ok)
    throw new Error(body.error || `Request failed (${response.status})`);
  return body;
}
function setBusy(value) {
  for (const name of ["one", "all", "recorded"])
    byId(name).disabled = value || !configuration;
  byId("results").setAttribute("aria-busy", String(value));
}
function show(result) {
  byId("results").replaceChildren();
  byId("summary").textContent =
    `${result.sessions.filter((r) => r.verified).length}/${result.sessions.length} verified · ${result.mode}`;
  for (const row of result.sessions) {
    const article = make("article", undefined, "result");
    article.append(
      make("span", row.verified ? "VERIFIED" : "CHECK FAILED", "tag"),
    );
    article.append(make("h3", `Case ${row.case.id} · mood ${row.case.mood}`));
    article.append(make("p", row.case.concern));
    article.append(make("p", row.analysis.plaintext, "reply"));
    const stats = make("div", undefined, "stats");
    for (const text of [
      `a = ${row.analysis.a}`,
      `b = ${row.analysis.b}`,
      `inverse = ${row.analysis.a_inverse}`,
      `χ² = ${row.analysis.chi_squared.toFixed(2)}`,
    ])
      stats.append(make("span", text));
    article.append(stats);
    for (const [title, content] of [
      [
        "Captured-style request / reply",
        JSON.stringify(
          { request: row.request, response: row.response },
          null,
          2,
        ),
      ],
      [
        "Recovery proof and independent checks",
        row.analysis.proof.join("\n") +
          "\n\n" +
          JSON.stringify(row.checks, null, 2),
      ],
    ]) {
      const details = make("details");
      details.append(make("summary", title), make("pre", content));
      article.append(details);
    }
    byId("results").append(article);
  }
}
async function history() {
  const data = await api("/api/runs");
  byId("history").replaceChildren();
  if (!data.runs.length)
    byId("history").append(make("p", "No local run exports yet."));
  for (const run of data.runs) {
    const row = make("div", undefined, "history-row");
    row.append(
      make(
        "strong",
        `${run.run_time_utc} · ${run.mode} · ${run.cases} cases · ${run.all_passed ? "PASS" : "FAIL / partial"}`,
      ),
    );
    const downloads = make("div", undefined, "downloads");
    for (const filename of [
      "result.json",
      "summary.csv",
      "ciphertexts.csv",
      "key_recovery_proof.txt",
      "manifest.json",
    ]) {
      const a = make("a", filename);
      a.href = `/api/export/${run.id}/${filename}`;
      a.target = "_blank";
      a.rel = "noopener";
      downloads.append(a);
    }
    row.append(downloads);
    byId("history").append(row);
  }
}
async function recorded() {
  setBusy(true);
  try {
    const data = await api("/api/recorded");
    show(data);
    byId("message").textContent =
      "Recorded corpus inspected. Analysis was recomputed locally; no TCP exchange or model call was made.";
  } catch (error) {
    byId("message").textContent = error.message;
  } finally {
    setBusy(false);
  }
}
async function run(caseId) {
  setBusy(true);
  byId("message").textContent =
    configuration.mode === "replay"
      ? "Running real local TCP exchanges with recorded replies…"
      : "Requesting fresh Gemini replies over HTTPS; waiting for the actual result…";
  try {
    const data = await api("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Affine-Lab": "1" },
      body: JSON.stringify({ case: caseId }),
    });
    show(data);
    byId("message").textContent = data.all_passed
      ? `PASS · ${data.generation}. Export saved as ${data.export_name}.`
      : `FAIL / partial · ${data.error || "Some independent checks failed"}. Completed results were exported.`;
    await history();
  } catch (error) {
    byId("message").textContent = `Run failed: ${error.message}`;
  } finally {
    setBusy(false);
  }
}
byId("recorded").addEventListener("click", recorded);
byId("one").addEventListener("click", () => run(Number(byId("case").value)));
byId("all").addEventListener("click", () => run("all"));
function theme(value) {
  document.documentElement.dataset.theme = value;
  byId("theme").setAttribute(
    "aria-label",
    value === "dark" ? "Switch to light theme" : "Switch to dark theme",
  );
  try {
    localStorage.setItem("affine-lab-theme", value);
  } catch (_) {
    /* storage may be disabled */
  }
}
let initial = "light";
try {
  initial = localStorage.getItem("affine-lab-theme") || initial;
} catch (_) {}
theme(initial === "dark" ? "dark" : "light");
byId("theme").addEventListener("click", () =>
  theme(document.documentElement.dataset.theme === "dark" ? "light" : "dark"),
);
async function init() {
  try {
    configuration = await api("/api/status");
    byId("mode").textContent =
      configuration.mode === "replay"
        ? "OFFLINE REPLAY · recorded model replies"
        : "GEMINI · fresh model generation";
    byId("provider").textContent =
      `${configuration.model} · local TCP port ${configuration.tcp_port}`;
    for (const item of configuration.cases) {
      const option = make("option", `Case ${item.id} · mood ${item.mood}`);
      option.value = item.id;
      byId("case").append(option);
    }
    await recorded();
    await history();
  } catch (error) {
    byId("message").textContent = error.message;
  }
}
init();
