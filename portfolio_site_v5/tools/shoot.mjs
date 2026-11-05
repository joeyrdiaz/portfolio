// Full page screenshots, overflow checks, and a few live interactions.
// Uses the system Chrome DevTools protocol. No npm installs.
//   node tools/shoot.mjs
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync, rmSync } from "node:fs";
import { setTimeout as delay } from "node:timers/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const outDir = path.join(root, "screenshots");
mkdirSync(outDir, { recursive: true });
const port = 9333;
const profile = "/tmp/chrome-shoot-profile";
rmSync(profile, { recursive: true, force: true });

const chrome = spawn("/usr/bin/google-chrome", [
  "--headless=new",
  "--disable-gpu",
  "--no-sandbox",
  "--disable-dev-shm-usage",
  "--hide-scrollbars",
  "--force-device-scale-factor=1",
  `--remote-debugging-port=${port}`,
  `--user-data-dir=${profile}`,
  "about:blank",
], { stdio: "ignore" });

function die(error) {
  chrome.kill("SIGKILL");
  console.error(error);
  process.exit(1);
}

class CDP {
  constructor(ws) {
    this.ws = ws;
    this.id = 0;
    this.pending = new Map();
    this.listeners = [];
  }
  async open() {
    if (this.ws.readyState === 1) return;
    await new Promise((resolve, reject) => {
      this.ws.addEventListener("open", resolve, { once: true });
      this.ws.addEventListener("error", reject, { once: true });
    });
  }
  listen(fn) { this.listeners.push(fn); }
  send(method, params = {}, sessionId) {
    const id = ++this.id;
    const payload = { id, method, params };
    if (sessionId) payload.sessionId = sessionId;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify(payload));
    });
  }
  arm() {
    this.ws.addEventListener("message", (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(JSON.stringify(msg.error)));
        else resolve(msg.result);
      } else {
        for (const fn of this.listeners) fn(msg);
      }
    });
  }
}

async function browserVersion() {
  for (let i = 0; i < 40; i++) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json/version`);
      if (response.ok) return response.json();
    } catch { /* retry */ }
    await delay(150);
  }
  throw new Error("Chrome did not open a debugging port");
}

async function openTarget(cdp, url) {
  const created = await cdp.send("Target.createTarget", { url: "about:blank" });
  const { targetInfo } = await cdp.send("Target.getTargetInfo", { targetId: created.targetId });
  const { sessionId } = await cdp.send("Target.attachToTarget", { targetId: created.targetId, flatten: true });
  return { sessionId, targetId: targetInfo.targetId };
}

async function evaluate(cdp, sessionId, expression) {
  const result = await cdp.send("Runtime.evaluate", {
    expression,
    returnByValue: true,
    awaitPromise: true,
  }, sessionId);
  if (result.exceptionDetails) {
    throw new Error(JSON.stringify(result.exceptionDetails));
  }
  return result.result.value;
}

async function screenshot(cdp, sessionId, file, clip) {
  const shot = await cdp.send("Page.captureScreenshot", {
    format: "png",
    captureBeyondViewport: true,
    clip,
  }, sessionId);
  writeFileSync(file, Buffer.from(shot.data, "base64"));
}

async function prepare(cdp, sessionId, url, width, height, reduced, scheme = "light") {
  const problems = [];
  cdp.listen((msg) => {
    if (msg.sessionId !== sessionId) return;
    if (msg.method === "Runtime.exceptionThrown") {
      problems.push("pageerror: " + (msg.params.exceptionDetails.exception?.description || msg.params.exceptionDetails.text));
    }
    if (msg.method === "Runtime.consoleAPICalled" && msg.params.type === "error") {
      const text = msg.params.args.map((arg) => arg.value || arg.description || "").join(" ");
      problems.push("console: " + text);
    }
    if (msg.method === "Network.loadingFailed") {
      problems.push("failed: " + msg.params.errorText + " " + (msg.params.requestId || ""));
    }
    if (msg.method === "Network.responseReceived" && msg.params.response.status >= 400) {
      problems.push("status " + msg.params.response.status + " " + msg.params.response.url);
    }
  });
  await cdp.send("Page.enable", {}, sessionId);
  await cdp.send("Runtime.enable", {}, sessionId);
  await cdp.send("Network.enable", {}, sessionId);
  await cdp.send("Emulation.setDeviceMetricsOverride", {
    width,
    height,
    deviceScaleFactor: 1,
    mobile: width < 800,
  }, sessionId);
  await cdp.send("Emulation.setEmulatedMedia", {
    features: [
      { name: "prefers-reduced-motion", value: reduced ? "reduce" : "no-preference" },
      { name: "prefers-color-scheme", value: scheme },
    ],
  }, sessionId);
  await cdp.send("Page.navigate", { url }, sessionId);
  for (let i = 0; i < 50; i++) {
    const state = await evaluate(cdp, sessionId, "document.readyState");
    if (state === "complete") break;
    await delay(100);
  }
  const images = await evaluate(cdp, sessionId, `(() => {
    document.querySelectorAll('.reveal').forEach((el) => el.classList.add('in'));
    const imgs = [...document.images].filter((img) => img.getAttribute('src'));
    for (const img of imgs) {
      img.loading = 'eager';
      img.src = img.getAttribute('src');
    }
    return Promise.all(imgs.map((img) => img.decode().then(() => img.naturalWidth).catch(() => 0)));
  })()`);
  problems.push(...(images || []).map((width, index) => width ? "" : "image " + index + " did not decode").filter(Boolean));
  // Let load animations and count ups settle before measuring or capturing.
  await delay(reduced ? 120 : 1800);
  return problems;
}

const report = { pages: {}, interactions: {} };

try {
  const version = await browserVersion();
  const browser = new CDP(new WebSocket(version.webSocketDebuggerUrl));
  await browser.open();
  browser.arm();
  const fileUrl = "file://" + path.join(root, "index.html");

  async function measure(url, width, height, label, scheme = "light") {
    const page = await openTarget(browser, url);
    const problems = await prepare(browser, page.sessionId, url, width, height, false, scheme);
    const metrics = await evaluate(browser, page.sessionId, `(() => {
      const visible = [...document.querySelectorAll("body *")].filter((el) => {
        const style = getComputedStyle(el);
        if (style.display === "none" || style.visibility === "hidden") return false;
        const rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0 && el.innerText && el.innerText.trim();
      });
      const fonts = visible.map((el) => parseFloat(getComputedStyle(el).fontSize)).filter((n) => n > 0);
      const overflow = [...document.querySelectorAll("body *")].filter((el) => {
        if (el.closest(".marquee, .sr-only, .skip")) return false;
        const rect = el.getBoundingClientRect();
        return rect.right > window.innerWidth + 1 || rect.left < -1;
      }).slice(0, 6).map((el) => el.tagName + "." + String(el.className).slice(0, 80));
      return {
        scrollWidth: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth,
        scrollHeight: document.documentElement.scrollHeight,
        minFont: fonts.length ? Math.min(...fonts) : null,
        overflow,
      };
    })()`);
    report.pages[label] = { ...metrics, problems };
    const heightPx = Math.ceil(metrics.scrollHeight);
    if (label.startsWith("full_") || label.startsWith("calc_")) {
      await screenshot(browser, page.sessionId, path.join(outDir, label + ".png"), {
        x: 0, y: 0, width, height: heightPx, scale: 1,
      });
    }
    await browser.send("Target.closeTarget", { targetId: page.targetId });
    return metrics;
  }

  for (const width of [360, 390, 768, 1280, 1536]) {
    await measure(fileUrl, width, 900, width === 390 || width === 768 || width === 1280 ? "full_" + width : "check_" + width);
  }
  for (const width of [390, 1280]) {
    await measure(fileUrl, width, 900, "full_" + width + "_dark", "dark");
  }

  const calcPage = await openTarget(browser, fileUrl);
  const calcProblems = await prepare(
    browser,
    calcPage.sessionId,
    fileUrl + "?leads=120&ticket=2500&close=35&hours=8#calculator",
    390,
    844,
  );
  const calc = await evaluate(browser, calcPage.sessionId, `(() => {
    const expected = quoteLeak(120, 2500, 35, 8);
    const box = document.getElementById("calculator").getBoundingClientRect();
    return {
      month: document.getElementById("r-month").textContent,
      year: document.getElementById("r-year").textContent,
      text: document.getElementById("r-text").textContent,
      formula: document.getElementById("r-formula").textContent,
      expectedMonth: Math.round(expected.monthly),
      expectedYear: Math.round(expected.annual),
      top: box.top + window.scrollY,
      height: box.height,
      width: box.width,
    };
  })()`);
  report.interactions.calculator = { ...calc, problems: calcProblems };
  await screenshot(browser, calcPage.sessionId, path.join(outDir, "calculator_390.png"), {
    x: 0,
    y: Math.max(0, calc.top - 12),
    width: 390,
    height: Math.ceil(calc.height + 24),
    scale: 1,
  });
  await browser.send("Target.closeTarget", { targetId: calcPage.targetId });

  const live = await openTarget(browser, fileUrl);
  const liveProblems = await prepare(browser, live.sessionId, fileUrl, 390, 844);
  const behavior = await evaluate(browser, live.sessionId, `(() => {
    document.getElementById("leads").value = "";
    document.getElementById("leads").dispatchEvent(new Event("input", { bubbles: true }));
    const error = document.getElementById("leads-err").textContent;
    const invalid = document.getElementById("leads").getAttribute("aria-invalid");
    document.getElementById("nav-toggle").click();
    const open = document.getElementById("nav-toggle").getAttribute("aria-expanded");
    document.querySelector("#nav-links a").click();
    const closed = document.getElementById("nav-toggle").getAttribute("aria-expanded");
    const math = document.querySelector(".math");
    math.querySelector("summary").click();
    const mathOpen = math.open;
    const charts = {
      monthCols: document.querySelectorAll(".mcol").length,
      ageCols: document.querySelectorAll(".acol").length,
      sourceRows: document.querySelectorAll(".src-row").length,
      dataTables: document.querySelectorAll("table.sr-only").length,
      images: document.querySelectorAll("main img").length,
    };
    document.getElementById("leads").value = "94";
    document.querySelector('#hours-presets [data-hours="30"]').click();
    const presetHours = document.getElementById("hours").value;
    const presetPressed = document.querySelector('#hours-presets [data-hours="30"]').getAttribute("aria-pressed");
    const presetMonth = document.getElementById("r-month").textContent;
    const steps = document.querySelectorAll("#r-formula li").length;
    return { error, invalid, open, closed, mathOpen, charts, presetHours, presetPressed, presetMonth, steps };
  })()`);
  report.interactions.behavior390 = { ...behavior, problems: liveProblems };
  await browser.send("Target.closeTarget", { targetId: live.targetId });

  const motion = await openTarget(browser, fileUrl);
  await prepare(browser, motion.sessionId, fileUrl, 1280, 900, true);
  report.interactions.reducedMotion = await evaluate(browser, motion.sessionId, `(() => {
    const el = document.querySelector(".reveal");
    const style = getComputedStyle(el);
    return { opacity: style.opacity, transform: style.transform };
  })()`);
  await browser.send("Target.closeTarget", { targetId: motion.targetId });

  writeFileSync(path.join(outDir, "audit.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  chrome.kill("SIGKILL");
} catch (error) {
  die(error.stack || error.message || String(error));
}
