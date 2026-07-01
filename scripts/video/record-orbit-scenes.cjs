#!/usr/bin/env node
/*
Record repeatable Django Orbit product-demo scenes with Playwright.

Usage:
  node scripts/video/record-orbit-scenes.cjs --scene dashboard-smoke
  node scripts/video/record-orbit-scenes.cjs --scene debug-500
  node scripts/video/record-orbit-scenes.cjs --scene n-plus-one
  node scripts/video/record-orbit-scenes.cjs --scene health-safety
  node scripts/video/record-orbit-scenes.cjs --scene all

Set ORBIT_VIDEO_BASE_URL to target a different server.
*/

const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const ROOT = path.resolve(__dirname, "..", "..");
const RAW_DIR = path.join(ROOT, "output", "video", "raw");
const BASE_URL = process.env.ORBIT_VIDEO_BASE_URL || "http://127.0.0.1:8000";
const VIEWPORT = { width: 1440, height: 900 };

const args = process.argv.slice(2);
const sceneArg = valueFor("--scene") || "all";
const slowMo = Number(valueFor("--slow-mo") || 120);
const headed = args.includes("--headed");

function valueFor(flag) {
  const index = args.indexOf(flag);
  return index === -1 ? null : args[index + 1];
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function ensureOutput() {
  fs.mkdirSync(RAW_DIR, { recursive: true });
}

async function installVisualHelpers(page) {
  await page.addStyleTag({
    content: `
      .orbit-video-hotspot {
        position: fixed;
        z-index: 999999;
        width: 34px;
        height: 34px;
        border-radius: 999px;
        border: 3px solid #22d3ee;
        background: rgba(34, 211, 238, 0.12);
        pointer-events: none;
        transform: translate(-50%, -50%) scale(0.8);
        opacity: 0;
        transition: opacity 160ms ease, transform 180ms ease;
        box-shadow: 0 0 0 8px rgba(34, 211, 238, 0.08);
      }
      .orbit-video-hotspot.is-visible {
        opacity: 1;
        transform: translate(-50%, -50%) scale(1);
      }
      .orbit-video-callout {
        position: fixed;
        left: 28px;
        bottom: 28px;
        z-index: 999998;
        max-width: 520px;
        padding: 14px 18px;
        border-radius: 10px;
        border: 1px solid rgba(34, 211, 238, 0.5);
        background: rgba(2, 6, 23, 0.88);
        color: #e2e8f0;
        font: 600 18px/1.35 Inter, system-ui, sans-serif;
        box-shadow: 0 20px 50px rgba(0,0,0,0.35);
        backdrop-filter: blur(10px);
      }
    `,
  });
  await page.evaluate(() => {
    if (!document.querySelector(".orbit-video-hotspot")) {
      const dot = document.createElement("div");
      dot.className = "orbit-video-hotspot";
      document.body.appendChild(dot);
    }
  });
}

async function callout(page, text, ms = 1600) {
  await page.evaluate((message) => {
    let el = document.querySelector(".orbit-video-callout");
    if (!el) {
      el = document.createElement("div");
      el.className = "orbit-video-callout";
      document.body.appendChild(el);
    }
    el.textContent = message;
  }, text);
  await sleep(ms);
  await page.evaluate(() => {
    const el = document.querySelector(".orbit-video-callout");
    if (el) el.remove();
  });
}

async function highlightClick(page, locator, pauseMs = 600) {
  const box = await locator.boundingBox();
  if (box) {
    const x = box.x + box.width / 2;
    const y = box.y + box.height / 2;
    await page.mouse.move(x, y, { steps: 12 });
    await page.evaluate(
      ({ x, y }) => {
        const dot = document.querySelector(".orbit-video-hotspot");
        dot.style.left = `${x}px`;
        dot.style.top = `${y}px`;
        dot.classList.add("is-visible");
      },
      { x, y },
    );
    await sleep(220);
  }
  await locator.click();
  await sleep(pauseMs);
  await page.evaluate(() => {
    const dot = document.querySelector(".orbit-video-hotspot");
    if (dot) dot.classList.remove("is-visible");
  });
}

async function openOrbit(page) {
  await page.goto(`${BASE_URL}/orbit/`, { waitUntil: "networkidle" });
  await installVisualHelpers(page);
  const gotIt = page.getByRole("button", { name: "Got it" });
  if (await gotIt.isVisible().catch(() => false)) {
    await highlightClick(page, gotIt, 500);
  }
  await page.waitForSelector("#feed-container", { timeout: 15000 });
  await sleep(1200);
}

async function clickSidebar(page, label) {
  const item = page.getByText(label, { exact: true }).first();
  await highlightClick(page, item, 1000);
  await page.waitForSelector("#feed-container [data-entry-id]", { timeout: 15000 });
}

async function openFirstEntry(page) {
  const row = page.locator("#feed-container [data-entry-id]").first();
  await row.waitFor({ timeout: 15000 });
  await highlightClick(page, row, 1400);
  await page.waitForSelector("#detail-container #json-payload", { timeout: 15000 });
  await sleep(1200);
}

async function generateTraffic(page) {
  const paths = [
    "/",
    "/books/",
    "/duplicate-queries/",
    "/slow/?delay=0.2",
    "/log/",
    "/api/data/",
  ];
  for (const target of paths) {
    try {
      await page.goto(`${BASE_URL}${target}`, { waitUntil: "networkidle", timeout: 10000 });
    } catch (_) {
      // Demo generation should continue even if one endpoint fails.
    }
  }
  try {
    await page.goto(`${BASE_URL}/error/`, { waitUntil: "domcontentloaded", timeout: 10000 });
  } catch (_) {
    // Expected 500 path for exception capture.
  }
}

async function recordScene(name, fn) {
  await ensureOutput();
  const browser = await chromium.launch({ headless: !headed, slowMo });
  const context = await browser.newContext({
    viewport: VIEWPORT,
    recordVideo: { dir: RAW_DIR, size: VIEWPORT },
  });
  const page = await context.newPage();

  try {
    await fn(page);
  } finally {
    await context.close();
    await browser.close();
  }

  const videos = fs
    .readdirSync(RAW_DIR)
    .filter((file) => file.endsWith(".webm"))
    .map((file) => path.join(RAW_DIR, file))
    .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);

  if (videos[0]) {
    const finalPath = path.join(RAW_DIR, `${name}.webm`);
    if (fs.existsSync(finalPath)) fs.unlinkSync(finalPath);
    fs.renameSync(videos[0], finalPath);
    console.log(`recorded ${finalPath}`);
  }
}

const scenes = {
  async "dashboard-smoke"(page) {
    await generateTraffic(page);
    await openOrbit(page);
    await callout(page, "Django Orbit records runtime evidence outside your app UI");
    await clickSidebar(page, "Requests");
    await openFirstEntry(page);
    await callout(page, "Every request links related SQL, logs and exceptions by family_hash");
    await sleep(1200);
  },

  async "debug-500"(page) {
    try {
      await page.goto(`${BASE_URL}/error/`, { waitUntil: "domcontentloaded", timeout: 10000 });
    } catch (_) {}
    await openOrbit(page);
    await callout(page, "Start from the runtime error, not a guess");
    await clickSidebar(page, "Exceptions");
    await openFirstEntry(page);
    const promptButton = page.getByTitle("Copy agent prompt").first();
    if (await promptButton.isVisible().catch(() => false)) {
      await highlightClick(page, promptButton, 1200);
      await callout(page, "Copy an agent-ready prompt with masked Orbit context");
    }
    await sleep(1200);
  },

  async "n-plus-one"(page) {
    await page.goto(`${BASE_URL}/duplicate-queries/`, { waitUntil: "networkidle" });
    await page.goto(`${BASE_URL}/slow/?delay=0.3`, { waitUntil: "networkidle" });
    await openOrbit(page);
    await callout(page, "Orbit surfaces slow queries and duplicate-query signals");
    await clickSidebar(page, "Requests");
    await openFirstEntry(page);
    await page.mouse.wheel(0, 520);
    await sleep(1000);
    await callout(page, "Use request detail to inspect related queries before changing ORM code");
    await sleep(1200);
  },

  async "health-safety"(page) {
    await openOrbit(page);
    const health = page.getByRole("link", { name: /Health/ }).first();
    await highlightClick(page, health, 1200);
    await page.waitForURL(/\/orbit\/health\//, { timeout: 10000 });
    await installVisualHelpers(page);
    await callout(page, "Health shows watcher status and agent/MCP safety posture");
    await sleep(2200);
  },
};

async function main() {
  const names = sceneArg === "all" ? Object.keys(scenes) : [sceneArg];
  for (const name of names) {
    if (!scenes[name]) {
      console.error(`Unknown scene: ${name}`);
      process.exitCode = 1;
      return;
    }
    console.log(`recording ${name}...`);
    await recordScene(name, scenes[name]);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

