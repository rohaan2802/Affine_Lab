"use strict";
const $ = (id) => document.getElementById(id);
const root = document.documentElement;
function theme(value) {
  root.dataset.theme = value;
  $("theme").setAttribute(
    "aria-label",
    value === "dark" ? "Switch to light theme" : "Switch to dark theme",
  );
  try {
    localStorage.setItem("affine-portfolio-theme", value);
  } catch (_) {}
}
let saved;
try {
  saved = localStorage.getItem("affine-portfolio-theme");
} catch (_) {}
theme(saved === "dark" ? "dark" : "light");
$("theme").onclick = () =>
  theme(root.dataset.theme === "dark" ? "light" : "dark");
function menu(open) {
  $("nav").classList.toggle("open", open);
  $("menu").setAttribute("aria-expanded", String(open));
  $("menu").setAttribute(
    "aria-label",
    open ? "Close navigation" : "Open navigation",
  );
  $("hamburger").toggleAttribute("hidden", open);
  $("close-menu").toggleAttribute("hidden", !open);
}
$("menu").onclick = () =>
  menu($("menu").getAttribute("aria-expanded") !== "true");
document
  .querySelectorAll("#nav a")
  .forEach((link) => link.addEventListener("click", () => menu(false)));
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") menu(false);
});
const navLinks = [...document.querySelectorAll("#nav a")];
const sections = navLinks.map((a) =>
  document.querySelector(a.getAttribute("href")),
);
function onScroll() {
  let current = sections[0];
  for (const section of sections)
    if (section.getBoundingClientRect().top <= 160) current = section;
  // A short footer cannot reach the header threshold at the end of the page.
  const atBottom =
    window.scrollY > 0 &&
    Math.ceil(window.scrollY + window.innerHeight) >= root.scrollHeight - 2;
  if (atBottom) current = sections[sections.length - 1];
  navLinks.forEach((a) => {
    const active = a.hash === "#" + current.id;
    a.classList.toggle("active", active);
    if (active) a.setAttribute("aria-current", "location");
    else a.removeAttribute("aria-current");
  });
  $("backtop").hidden = window.scrollY < 450;
}
window.addEventListener("scroll", onScroll, { passive: true });
window.addEventListener("resize", onScroll);
window.addEventListener("hashchange", onScroll);
onScroll();
$("backtop").onclick = () =>
  window.scrollTo({
    top: 0,
    behavior: matchMedia("(prefers-reduced-motion: reduce)").matches
      ? "instant"
      : "smooth",
  });
const figures = window.AFFINE_FIGURES;
let category = "All",
  filtered = figures,
  selected = 0,
  opener = null,
  swipeStart = null;
const make = (tag, text, cls) => {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (cls) el.className = cls;
  return el;
};
for (const name of ["All", ...new Set(figures.map((f) => f.category))]) {
  const button = make("button", name, "chip");
  button.type = "button";
  button.setAttribute("aria-pressed", String(name === category));
  button.onclick = () => {
    category = name;
    document
      .querySelectorAll(".chip")
      .forEach((b) => b.setAttribute("aria-pressed", String(b === button)));
    render();
  };
  $("filters").append(button);
}
function render() {
  const query = $("search").value.toLowerCase().trim();
  filtered = figures.filter(
    (f) =>
      (category === "All" || f.category === category) &&
      `${f.title} ${f.caption} ${f.category}`.toLowerCase().includes(query),
  );
  $("gallery").replaceChildren();
  $("gallery-count").textContent =
    `${filtered.length} of ${figures.length} figures`;
  $("empty").hidden = filtered.length !== 0;
  filtered.forEach((f, index) => {
    const figure = make("figure", undefined, "figure-card"),
      button = make("button", undefined, "figure-open");
    button.type = "button";
    button.setAttribute("aria-label", `Open figure ${f.id}: ${f.title}`);
    const img = make("img");
    img.src = f.preview;
    img.alt = f.title;
    img.width = 960;
    img.height = 600;
    img.loading = "lazy";
    button.append(img);
    button.onclick = () => open(index, button);
    const caption = make("figcaption");
    caption.append(
      make("span", f.category, "category"),
      make("h3", f.title),
      make("p", f.caption),
    );
    figure.append(button, caption);
    $("gallery").append(figure);
  });
}
function showFigure() {
  const f = filtered[selected];
  $("viewer-title").textContent =
    `${String(f.id).padStart(2, "0")} / ${figures.length} · ${f.title}`;
  $("viewer-image").src = f.full;
  $("viewer-image").alt = f.title;
  $("viewer-caption").textContent = f.caption;
  $("original").href = f.full;
  $("stage").classList.remove("zoomed");
  $("zoom").setAttribute("aria-pressed", "false");
  $("zoom").textContent = "Zoom +";
  $("stage").scrollTo(0, 0);
}
function open(index, button) {
  selected = index;
  opener = button;
  showFigure();
  $("viewer").showModal();
  $("viewer-close").focus();
}
function step(delta) {
  selected = (selected + delta + filtered.length) % filtered.length;
  showFigure();
}
$("previous").onclick = () => step(-1);
$("next").onclick = () => step(1);
$("viewer-close").onclick = () => $("viewer").close();
$("viewer").addEventListener("close", () => {
  if (opener?.isConnected) opener.focus();
});
$("viewer").addEventListener("click", (e) => {
  if (e.target === $("viewer")) $("viewer").close();
});
$("zoom").onclick = () => {
  const on = $("stage").classList.toggle("zoomed");
  $("zoom").setAttribute("aria-pressed", String(on));
  $("zoom").textContent = on ? "Reset zoom" : "Zoom +";
};
$("viewer").addEventListener("keydown", (e) => {
  if (e.key === "ArrowRight") {
    e.preventDefault();
    step(1);
  }
  if (e.key === "ArrowLeft") {
    e.preventDefault();
    step(-1);
  }
});
$("stage").addEventListener(
  "touchstart",
  (e) => {
    if (!$("stage").classList.contains("zoomed"))
      swipeStart = e.changedTouches[0].clientX;
  },
  { passive: true },
);
$("stage").addEventListener(
  "touchend",
  (e) => {
    if (swipeStart !== null) {
      const distance = e.changedTouches[0].clientX - swipeStart;
      if (Math.abs(distance) > 55) step(distance < 0 ? 1 : -1);
    }
    swipeStart = null;
  },
  { passive: true },
);
$("search").addEventListener("input", render);
render();
document.querySelectorAll("[data-tab]").forEach(
  (button) =>
    (button.onclick = () => {
      document.querySelectorAll("[data-tab]").forEach((b) => {
        b.setAttribute("aria-selected", String(b === button));
        $(b.dataset.tab).hidden = b !== button;
      });
    }),
);
const frequency = [
  8.167, 1.492, 2.782, 4.253, 12.702, 2.228, 2.015, 6.094, 6.966, 0.153, 0.772,
  4.025, 2.406, 6.749, 7.507, 1.929, 0.095, 5.987, 6.327, 9.056, 2.758, 0.978,
  2.36, 0.15, 1.974, 0.074,
];
const multipliers = [1, 3, 5, 7, 9, 11, 15, 17, 19, 21, 23, 25];
const mod = (n) => ((n % 26) + 26) % 26;
function inverse(a) {
  for (let i = 1; i < 26; i++) if (mod(a * i) === 1) return i;
  throw Error("a must be coprime to 26");
}
function transform(text, a, b, decode = false) {
  const inv = inverse(a);
  return [...text]
    .map((ch) => {
      const c = ch.charCodeAt(0),
        base = c >= 65 && c <= 90 ? 65 : c >= 97 && c <= 122 ? 97 : null;
      if (base === null) return ch;
      return String.fromCharCode(
        base + mod(decode ? inv * (c - base - b) : a * (c - base) + b),
      );
    })
    .join("");
}
function recover(text) {
  const count = Array(26).fill(0);
  for (const c of text.toUpperCase())
    if (c >= "A" && c <= "Z") count[c.charCodeAt(0) - 65]++;
  const n = count.reduce((a, b) => a + b, 0);
  if (!n) throw Error("Enter text with ASCII letters.");
  const rows = [];
  for (const a of multipliers)
    for (let b = 0; b < 26; b++) {
      let score = 0;
      for (let p = 0; p < 26; p++) {
        const expected = (n * frequency[p]) / 100;
        score += (count[mod(a * p + b)] - expected) ** 2 / expected;
      }
      rows.push({ a, b, score });
    }
  rows.sort((x, y) => x.score - y.score || x.a - y.a || x.b - y.b);
  return rows;
}
window.AffinePlayground = { transform, recover };
$("sample").onclick = () => {
  $("cipher-input").value = window.AFFINE_SAMPLE;
};
$("sample").click();
$("cipher-form").addEventListener("submit", (e) => {
  e.preventDefault();
  try {
    const text = $("cipher-input").value;
    if (text.length > 20000)
      throw Error("Keep the playground below 20,000 characters.");
    const action = $("cipher-action").value;
    let result;
    if (action === "recover") {
      const ranked = recover(text),
        key = ranked[0];
      result = `312 candidates scored · a=${key.a}, b=${key.b}, inverse=${inverse(key.a)}\nχ²=${key.score.toFixed(3)} · runner-up=${ranked[1].score.toFixed(3)}\n\n${transform(text, key.a, key.b, true)}\n\nThis score is a language-fit ranking, not a probability.`;
    } else {
      const a = Number($("key-a").value),
        b = Number($("key-b").value);
      if (!multipliers.includes(a) || !Number.isInteger(b) || b < 0 || b > 25)
        throw Error("Choose a valid multiplier and a shift from 0 to 25.");
      result = transform(text, a, b, action === "decrypt");
    }
    $("cipher-output").textContent = result;
    updateDetails(text, action);
  } catch (error) {
    $("cipher-output").textContent = error.message;
  }
});

let lastAnalysis = null;
function updateDetails(text, action) {
  const ranked = action === "recover" ? recover(text) : [];
  const key = ranked[0] || {
    a: Number($("key-a").value),
    b: Number($("key-b").value),
  };
  const plain =
    action === "encrypt" ? text : transform(text, key.a, key.b, true);
  const bins = Array(26).fill(0);
  for (const c of plain.toUpperCase())
    if (c >= "A" && c <= "Z") bins[c.charCodeAt(0) - 65]++;
  const total = bins.reduce((a, b) => a + b, 0);
  lastAnalysis = {
    action,
    input: text,
    key: { a: key.a, b: key.b, inverse: inverse(key.a) },
    output: $("cipher-output").textContent,
    letters: total,
    top_candidates: ranked.slice(0, 5),
    frequencies: bins.map((count, i) => ({
      letter: String.fromCharCode(65 + i),
      count,
      percent: total ? (100 * count) / total : 0,
      english_percent: frequency[i],
    })),
    note: "Language-fit candidates are not independent verification.",
  };
  $("candidate-rows").replaceChildren();
  if (!ranked.length) {
    const row = make("tr"),
      cell = make("td", "Candidate ranking is shown for key recovery.");
    cell.colSpan = 4;
    row.append(cell);
    $("candidate-rows").append(row);
  }
  ranked.slice(0, 5).forEach((c, i) => {
    const row = make("tr");
    for (const value of [i + 1, c.a, c.b, c.score.toFixed(3)])
      row.append(make("td", String(value)));
    $("candidate-rows").append(row);
  });
  $("frequency-chart").replaceChildren();
  const ns = "http://www.w3.org/2000/svg",
    svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 650 260");
  svg.setAttribute("role", "img");
  svg.setAttribute(
    "aria-label",
    "Recovered letter frequencies compared with standard English",
  );
  const element = (tag, attrs, text) => {
    const e = document.createElementNS(ns, tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
    if (text !== undefined) e.textContent = text;
    return e;
  };
  const ceiling = Math.max(
    16,
    ...lastAnalysis.frequencies.map((f) => f.percent),
  );
  for (const value of [0, ceiling / 2, ceiling]) {
    const y = 218 - (value / ceiling) * 180;
    svg.append(
      element("line", { x1: 32, y1: y, x2: 644, y2: y, class: "chart-grid" }),
      element(
        "text",
        { x: 1, y: y + 4, class: "chart-label" },
        value.toFixed(0) + "%",
      ),
    );
  }
  lastAnalysis.frequencies.forEach((f, i) => {
    const x = 36 + i * 23.2,
      g = element("g", {
        tabindex: "0",
        "aria-label": `${f.letter}: observed ${f.percent.toFixed(2)} percent, reference ${f.english_percent.toFixed(2)} percent`,
      });
    g.append(
      element(
        "title",
        {},
        `${f.letter} · observed ${f.percent.toFixed(2)}% · English ${f.english_percent.toFixed(2)}%`,
      ),
    );
    for (const [value, offset, cls] of [
      [f.percent, 0, "actual"],
      [f.english_percent, 9, "reference"],
    ])
      g.append(
        element("rect", {
          x: x + offset,
          y: 218 - (value / ceiling) * 180,
          width: 8,
          height: (value / ceiling) * 180,
          class: cls,
        }),
      );
    g.append(
      element("text", { x: x + 3, y: 240, class: "chart-label" }, f.letter),
    );
    svg.append(g);
  });
  const legend = make("div", undefined, "chart-legend");
  legend.append(
    make("span", "Recovered / input text"),
    make("span", "English reference"),
  );
  $("frequency-chart").append(svg, legend);
  $("export-status").textContent =
    total < 100 ? "Short text: statistical recovery may be unreliable." : "";
}
$("copy-result").onclick = async () => {
  if (!lastAnalysis) {
    $("export-status").textContent = "Run an analysis first.";
    return;
  }
  try {
    await navigator.clipboard.writeText($("cipher-output").textContent);
    $("export-status").textContent = "Result copied.";
  } catch (_) {
    const range = document.createRange();
    range.selectNodeContents($("cipher-output"));
    const selection = getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    $("export-status").textContent = "Result selected. Press Ctrl+C to copy.";
  }
};
$("download-result").onclick = () => {
  if (!lastAnalysis) {
    $("export-status").textContent = "Run an analysis first.";
    return;
  }
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(lastAnalysis, null, 2)], {
      type: "application/json",
    }),
  );
  const link = make("a");
  link.href = url;
  link.download = "affine-analysis.json";
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  $("export-status").textContent = "Analysis JSON downloaded.";
};

// Enlarge text-heavy previews without cropping their image contents.
$("preview-size").addEventListener("click", () => {
  const large = $("gallery").classList.toggle("large-previews");
  $("preview-size").setAttribute("aria-pressed", String(large));
  $("preview-size").textContent = large ? "Standard grid" : "Larger previews";
});
