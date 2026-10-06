#!/usr/bin/env node
/**
 * Start the whole FormTrap system with one command:   npm run dev
 *
 *   1. checks that PHP, Python, the Python packages and the exported models are there
 *   2. creates the database, tables and rules if they are missing
 *   3. starts the scoring service (Python, port 5055) and the web application (PHP, port 8090)
 *   4. on a first run, loads the dataset history so the dashboards have something to show
 *
 * Options:  --open        open the form and the data-mining view in the browser
 *           --no-import   do not load the dataset history into an empty database
 *           --smoke       start everything, confirm it answers, then stop again (a quick self-check)
 *           --stop        stop a scoring service and web application left running by an earlier start
 * Ctrl+C stops everything this command started.
 */
import { spawn, spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import http from "node:http";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const software = path.join(root, "software");
const python = process.env.PYTHON || "python";
const WEB_PORT = process.env.FORMTRAP_WEB_PORT || "8090";
const ML_PORT = "5055"; // the address in software/config.php ('ml' => 'url') points here
const WEB = `http://127.0.0.1:${WEB_PORT}`;
const ML = `http://127.0.0.1:${ML_PORT}`;
const flags = new Set(process.argv.slice(2));
const windows = process.platform === "win32";

const colour = (code, text) => (process.stdout.isTTY ? `\x1b[${code}m${text}\x1b[0m` : text);
const tags = { dev: colour("1", "[dev]   "), ml: colour("36", "[ml]    "), web: colour("33", "[web]   "), import: colour("35", "[import]") };
const say = (text) => console.log(`${tags.dev} ${text}`);
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const children = [];
let stopping = false;

function killTree(pid) {
  if (windows) {
    spawnSync("taskkill", ["/pid", String(pid), "/T", "/F"], { stdio: "ignore" });
  } else {
    try { process.kill(Number(pid), "SIGTERM"); } catch { /* already gone */ }
  }
}

function stop(code = 0) {
  if (stopping) return;
  stopping = true;
  for (const child of children) {
    if (child.exitCode === null) killTree(child.pid);
  }
  process.exit(code);
}

function fail(message, hint) {
  console.error(`${tags.dev} ${colour("31", message)}`);
  if (hint) console.error(`${tags.dev} ${hint}`);
  stop(1);
}

/** Run a command to completion. */
function run(command, args, options = {}) {
  const result = spawnSync(command, args, { encoding: "utf8", ...options });
  return { ok: result.status === 0, status: result.status, output: `${result.stdout || ""}${result.stderr || ""}`.trim() };
}

/** Start a long-running process and print its output line by line under a tag. */
function start(tag, command, args, options = {}) {
  const child = spawn(command, args, { stdio: ["ignore", "pipe", "pipe"], ...options });
  const print = (chunk) => {
    for (const line of chunk.toString().split(/\r?\n/)) {
      // the PHP development server announces every connection twice; keep only the request lines
      if (line.trim() && !/ (Accepted|Closing)$/.test(line)) console.log(`${tags[tag]} ${line}`);
    }
  };
  child.stdout.on("data", print);
  child.stderr.on("data", print);
  child.on("error", (error) => fail(`could not start ${command}: ${error.message}`));
  child.on("exit", (code) => {
    if (stopping) return;
    if (tag === "import") {
      say(code === 0 ? "dataset history loaded; refresh the dashboards" : "the import stopped with an error (see above)");
    } else {
      fail(`${command} stopped unexpectedly (exit code ${code})`, "Is the port already used by another program?");
    }
  });
  children.push(child);
  return child;
}

/** One HTTP request without keep-alive. Resolves to { status, body } or null when nothing answers. */
function request(url, { method = "GET", json } = {}) {
  return new Promise((resolve) => {
    const payload = json === undefined ? null : JSON.stringify(json);
    const req = http.request(url, {
      method, agent: false, timeout: 3000,
      headers: payload ? { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(payload) } : {},
    }, (res) => {
      let body = "";
      res.on("data", (chunk) => { body += chunk; });
      res.on("end", () => resolve({ status: res.statusCode, body }));
    });
    req.on("timeout", () => req.destroy());
    req.on("error", () => resolve(null));
    req.end(payload ?? undefined);
  });
}

const responds = async (url) => (await request(url))?.status === 200;

async function waitFor(url, label, seconds) {
  for (let i = 0; i < seconds * 2; i += 1) {
    if (await responds(url)) return;
    await sleep(500);
  }
  fail(`${label} did not answer at ${url} within ${seconds} seconds`);
}

function openInBrowser(url) {
  const [command, args] = windows ? ["cmd", ["/c", "start", "", url]] : process.platform === "darwin" ? ["open", [url]] : ["xdg-open", [url]];
  spawn(command, args, { stdio: "ignore", detached: true }).unref();
}

/** Process ids listening on a TCP port, with the program name of each. */
function listeners(port) {
  const found = [];
  if (windows) {
    for (const line of run("netstat", ["-ano", "-p", "TCP"]).output.split(/\r?\n/)) {
      const match = line.trim().match(/^TCP\s+\S+:(\d+)\s+\S+\s+LISTENING\s+(\d+)$/);
      if (match && match[1] === String(port)) {
        const task = run("tasklist", ["/FI", `PID eq ${match[2]}`, "/FO", "CSV", "/NH"]).output;
        // netstat can still list a port for a process that has already exited; tasklist then finds no task
        if (task.startsWith('"')) found.push({ pid: match[2], name: task.split(",")[0].replaceAll('"', "") });
      }
    }
  } else {
    for (const pid of run("lsof", ["-ti", `tcp:${port}`, "-sTCP:LISTEN"]).output.split(/\s+/).filter(Boolean)) {
      found.push({ pid, name: run("ps", ["-p", pid, "-o", "comm="]).output });
    }
  }
  return found.filter((p, i) => found.findIndex((q) => q.pid === p.pid) === i);
}

// ---------------------------------------------------------------- --stop
if (flags.has("--stop")) {
  let stopped = 0;
  for (const [label, port, expected] of [["scoring service", ML_PORT, /python/i], ["web application", WEB_PORT, /php/i]]) {
    const owners = listeners(port);
    if (!owners.length) say(`${label}: nothing is listening on port ${port}`);
    for (const { pid, name } of owners) {
      if (expected.test(name)) {
        killTree(pid);
        stopped += 1;
        say(`${label}: stopped ${name} (process ${pid}) on port ${port}`);
      } else {
        say(`${label}: port ${port} is used by ${name} (process ${pid}), which is not part of FormTrap; left alone`);
      }
    }
  }
  say(stopped ? "stopped" : "nothing to stop");
  process.exit(0);
}

// ---------------------------------------------------------------- 1. requirements
if (!run("php", ["-v"]).ok) fail("PHP was not found on the PATH.", "Install PHP 8 with the pdo_mysql and curl extensions.");
if (!run(python, ["--version"]).ok) fail("Python was not found on the PATH.", "Install Python 3.10+ or set the PYTHON environment variable.");

const extensions = run("php", ["-m"]).output.toLowerCase();
for (const extension of ["pdo_mysql", "curl"]) {
  if (!extensions.includes(extension)) fail(`The PHP extension ${extension} is not enabled.`, "Enable it in php.ini.");
}

if (!run(python, ["-c", "import flask, sklearn, joblib, scipy, numpy"]).ok) {
  fail("Python packages for the scoring service are missing.", `Run: ${python} -m pip install -r software/ml_service/requirements.txt`);
}

for (const file of ["spam_model.joblib", "campaign_model.joblib", "model_card.json", "clusters.json", "rules.json", "metrics.json"]) {
  if (!existsSync(path.join(software, "ml_service", "artifacts", file))) {
    fail(`The exported model file ${file} is missing.`, "Run: npm run notebook   (executes the notebook and copies its exports)");
  }
}

// ---------------------------------------------------------------- 2. database
const setup = run("php", ["setup_database.php"], { cwd: software });
const lines = setup.output.split(/\r?\n/);
if (!setup.ok) {
  for (const line of lines) console.error(`${tags.dev} ${line}`);
  fail(setup.status === 2 ? "The MySQL server is not reachable." : "Database setup failed.");
}
const database = JSON.parse(lines.pop());
for (const line of lines) say(line);

// ---------------------------------------------------------------- 3. services
process.on("SIGINT", () => { say("stopping"); stop(0); });
process.on("SIGTERM", () => stop(0));

if (await responds(`${ML}/health`)) {
  say(`scoring service already running at ${ML}`);
} else {
  start("ml", python, ["app.py"], {
    cwd: path.join(software, "ml_service"),
    env: { ...process.env, PORT: ML_PORT, PYTHONIOENCODING: "utf-8", PYTHONUNBUFFERED: "1" },
  });
}
if (await responds(`${WEB}/index.php`)) {
  say(`web application already running at ${WEB}`);
} else {
  start("web", "php", ["-S", `127.0.0.1:${WEB_PORT}`], { cwd: software });
}
await waitFor(`${ML}/health`, "The scoring service", 90);
await waitFor(`${WEB}/index.php`, "The web application", 30);

console.log("");
say(colour("32", "FormTrap is running"));
say(`  Contact form      ${WEB}/index.php`);
say(`  Dashboard         ${WEB}/dashboard.php`);
say(`  Data mining       ${WEB}/mining.php`);
say(`  Scoring service   ${ML}/health`);
say(children.length ? "  Press Ctrl+C to stop" : "  Both were already running; stop them with: npm run stop");
console.log("");

if (flags.has("--smoke")) {
  const answer = await request(`${ML}/predict`, {
    method: "POST",
    json: { name: "Test User", message: "Hello, could you tell me your opening hours on Friday? Thank you." },
  });
  const probability = answer ? JSON.parse(answer.body).spam_probability : undefined;
  if (probability === undefined) fail("smoke test: the scoring service did not return a prediction");
  say(`smoke test: the scoring service answered with spam probability ${probability}; stopping`);
  stop(0);
}

// ---------------------------------------------------------------- 4. first run: history for the dashboards
if (database.submissions === 0 && !flags.has("--no-import")) {
  const dataset = path.join(root, "data", "prepared", "formtrap_spam_clean.csv");
  if (existsSync(dataset)) {
    say("the database is empty: loading the dataset history in the background (about two minutes)");
    start("import", "php", [path.join("cron", "import_dataset.php"), dataset], { cwd: software });
  } else {
    say("the database is empty and data/prepared/formtrap_spam_clean.csv was not found; run: npm run data");
  }
}

if (flags.has("--open")) {
  openInBrowser(`${WEB}/index.php`);
  openInBrowser(`${WEB}/mining.php`);
}
