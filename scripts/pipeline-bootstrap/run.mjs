#!/usr/bin/env node
/**
 * Orchestrates the brownfield-bootstrap phases for a single repository:
 *   dispatch → clone → install → init → discovery → synthesis → ingest → complete
 *
 * Designed to run as a plain `node scripts/pipeline-bootstrap/run.mjs` step in
 * GitHub Actions. Does NOT use claude-code-action; ANTHROPIC_API_KEY is
 * consumed internally by `pipeline-init --brownfield`.
 *
 * Flags:
 *   --fixture <path>   Use path as working dir (skip git clone).
 *   --dry-run          Skip real pipeline-init; emit full event sequence with
 *                      a canned synthesis bundle. Still validates HMAC POST.
 *                      When used with --fixture, no network calls are made.
 */

import { createHash, createHmac } from "node:crypto";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { mkdir, mkdtemp, rm, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { emitEvent } from "./emit-event.mjs";

const execFileAsync = promisify(execFile);

export const PHASE_ORDER = [
  "dispatch",
  "clone",
  "install",
  "init",
  "discovery",
  "synthesis",
  "ingest",
  "complete",
];

function signBody(body, secret) {
  return "sha256=" + createHmac("sha256", secret).update(body).digest("hex");
}

function parseArgs(argv) {
  const args = { fixturePath: null, dryRun: false };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--fixture") args.fixturePath = argv[++i];
    else if (argv[i] === "--dry-run") args.dryRun = true;
  }
  return args;
}

function getPayload() {
  const raw = process.env.BOOTSTRAP_PAYLOAD;
  if (!raw) {
    // Fallback for --dry-run / --fixture local invocations
    return {
        bootstrap_job_id: process.env.BOOTSTRAP_JOB_ID ?? "dry-run-job",
        pipeline_id: process.env.BOOTSTRAP_PIPELINE_ID ?? "dry-run-pipeline",
        run_id: process.env.BOOTSTRAP_RUN_ID ?? "dry-run-run",
        repository_full_name: process.env.BOOTSTRAP_REPO ?? "Consiliency/dry-run",
        target_branch: process.env.BOOTSTRAP_TARGET_BRANCH ?? "main",
        policy_mode: process.env.BOOTSTRAP_POLICY_MODE ?? "observe",
        install_mode: process.env.BOOTSTRAP_INSTALL_MODE ?? "dispatch_existing_workflow",
        triggered_by_user_id: process.env.BOOTSTRAP_TRIGGERED_BY ?? "local",
      callback: {
        supabase_url: process.env.SUPABASE_URL ?? "",
        ingest_endpoint: process.env.BOOTSTRAP_INGEST_ENDPOINT ?? "",
        hmac_key_id: process.env.BOOTSTRAP_HMAC_KEY_ID ?? "dev",
      },
      schema_version: 2,
    };
  }
  return JSON.parse(raw);
}

function cannedSynthesisBundle() {
  return {
    discovery: {
      harnessRuns: [
        {
          harness: "claude",
          role: "discovery",
          toolCalls: [],
          output: { consensusSet: ["ARCHITECTURE.md"] },
        },
      ],
      consensusSet: ["ARCHITECTURE.md"],
    },
    synthesis: {
      architecture: {
        markdown: "# Architecture\n\nCanned dry-run architecture.",
        sidecar: {},
      },
      pipelineReadme: {
        markdown: "# Pipeline README\n\nCanned dry-run.",
        sidecar: {},
      },
      specRegistry: {
        markdown: "# Spec Registry\n\nCanned dry-run.",
        sidecar: {},
      },
      harnessConsensus: ["ARCHITECTURE.md"],
    },
  };
}

function sha256Json(value) {
  return createHash("sha256").update(JSON.stringify(value)).digest("hex");
}

function buildSynthesisArtifacts(bundle) {
  return [
    {
      kind: "architecture",
      path: ".pipeline/artifacts/roadmap/ARCHITECTURE.md",
      doc: bundle.synthesis.architecture,
    },
    {
      kind: "pipeline_readme",
      path: ".pipeline/artifacts/roadmap/PIPELINE-README.md",
      doc: bundle.synthesis.pipelineReadme,
    },
    {
      kind: "spec_registry",
      path: ".pipeline/specs/SPEC-GOVERNANCE-CANONICAL-SPEC-REGISTRY.md",
      doc: bundle.synthesis.specRegistry,
    },
  ].map(({ kind, path, doc }) => {
    const payload = {
      markdown: doc?.markdown ?? "",
      sidecar: doc?.sidecar ?? {},
    };
    return {
      kind,
      path,
      sha256: sha256Json({ kind, path, ...payload }),
      payload,
    };
  });
}

/**
 * @param {{
 *   emitFn?: typeof import("./emit-event.mjs").emitEvent,
 *   fetchFn?: typeof fetch,
 *   execFn?: typeof execFileAsync,
 *   markFailedFn?: typeof markBootstrapFailure,
 * }} deps
 */
export async function run(deps = {}) {
  const { emitFn = emitEvent, fetchFn = fetch, execFn = execFileAsync, markFailedFn = markBootstrapFailure } = deps;

  const args = parseArgs(process.argv.slice(2));
  const payload = getPayload();
  const {
    bootstrap_job_id,
    run_id,
    repository_full_name,
    target_branch = "main",
    callback: { supabase_url, ingest_endpoint, hmac_key_id },
  } = payload;

  const hmacSecret = process.env.BOOTSTRAP_HMAC_SECRET;

  async function emit(phase, message, data) {
    return emitFn({ bootstrap_job_id, phase, level: "info", message, data });
  }

  async function emitError(phase, message, data) {
    return emitFn({ bootstrap_job_id, phase, level: "error", message, data });
  }

  // ── dispatch ──────────────────────────────────────────────────────────────
  await emit("dispatch", `Bootstrap job ${bootstrap_job_id} received for ${repository_full_name}`);

  let workDir;
  let tempDir = null;

  try {
    // ── clone ────────────────────────────────────────────────────────────────
    if (args.fixturePath) {
      workDir = path.resolve(args.fixturePath);
      await emit("clone", `Using fixture directory: ${workDir}`);
    } else {
      tempDir = await mkdtemp(path.join(await bootstrapTempParent(), "bootstrap-"));
      workDir = path.join(tempDir, repository_full_name.split("/")[1]);
      await emit("clone", `Cloning ${repository_full_name} into ${workDir}`);

      const cloneToken = process.env.BOOTSTRAP_CLONE_TOKEN || process.env.GITHUB_TOKEN;
      if (!cloneToken) throw new Error("BOOTSTRAP_CLONE_TOKEN or GITHUB_TOKEN required for clone");

      const cloneUrl = `https://x-access-token:${cloneToken}@github.com/${repository_full_name}.git`;
      await execFn("git", ["clone", "--depth", "1", "--branch", target_branch, cloneUrl, workDir]).catch(async () => {
        await execFn("git", ["clone", "--depth", "1", cloneUrl, workDir]);
        await execFn("git", ["checkout", target_branch], { cwd: workDir });
      });

      await emit("clone", `Clone complete`, { target_branch });
    }

    // ── install ──────────────────────────────────────────────────────────────
    await emit("install", "Installing dependencies");
    if (!args.dryRun) {
      try {
        await execFn("npm", ["install", "--ignore-scripts"], { cwd: workDir });
      } catch {
        // Some repos may use pnpm or yarn — best-effort; pipeline-init handles its own install
        await emit("install", "npm install skipped or failed — continuing");
      }
    }
    await emit("install", "Install step complete");

    // ── init ─────────────────────────────────────────────────────────────────
    const pipelineInitBin = process.env.PIPELINE_INIT_BIN || "pipeline-init";
    const pipelineInitHarnesses = process.env.PIPELINE_INIT_HARNESSES || "claude";
    await emit("init", "Running pipeline-init --brownfield");
    if (!args.dryRun) {
      await linkGovernedPipelineInternals(workDir);
      await prepareCodexApiKeyAuth(workDir);
      const initResult = await execFn(pipelineInitBin, [
        "--brownfield",
        "--yes",
        "--harnesses",
        pipelineInitHarnesses,
      ], {
        cwd: workDir,
        env: {
          ...process.env,
          PIPELINE_NONINTERACTIVE: "1",
        },
      }).catch((error) => {
        throw new Error(`pipeline-init failed: ${summarizeProcessError(error)}`);
      });
      await emit("init", "pipeline-init command exited", {
        stdout_bytes: initResult?.stdout?.length ?? 0,
        stderr_bytes: initResult?.stderr?.length ?? 0,
        harnesses: pipelineInitHarnesses.split(",").map((item) => item.trim()).filter(Boolean),
      });
    }
    await emit("init", "pipeline-init complete");

    // ── discovery ────────────────────────────────────────────────────────────
    await emit("discovery", "Discovery phase starting");
    // Discovery runs inside pipeline-init; this event marks the completion boundary.
    await emit("discovery", "Discovery complete");

    // ── synthesis ────────────────────────────────────────────────────────────
    await emit("synthesis", "Synthesis phase starting");
    const bundle = args.dryRun
      ? cannedSynthesisBundle()
      : await readSynthesisBundle(workDir);
    if (!args.dryRun) {
      const summary = summarizeSynthesisBundle(bundle);
      await emit("synthesis", "Synthesis artifacts inspected", summary);
      if (summary.pipeline_phase_count === 0) {
        throw new Error("pipeline-init did not produce canonical roadmap phases");
      }
    }
    await emit("synthesis", "Synthesis complete");

    // ── ingest ───────────────────────────────────────────────────────────────
    await emit("ingest", "POSTing synthesis bundle to ingest endpoint");

    const ingestBody = JSON.stringify({
      bootstrap_job_id,
      run_id,
      bundle,
      artifacts: buildSynthesisArtifacts(bundle),
    });

    if (ingest_endpoint && hmacSecret) {
      const signature = signBody(ingestBody, hmacSecret);
      const response = await fetchFn(ingest_endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Bootstrap-Signature": signature,
          "X-Bootstrap-Key-Id": hmac_key_id,
          ...(process.env.VERCEL_AUTOMATION_BYPASS_SECRET
            ? { "x-vercel-protection-bypass": process.env.VERCEL_AUTOMATION_BYPASS_SECRET }
            : {}),
        },
        body: ingestBody,
      });

      if (!response.ok) {
        const detail = await response.text();
        throw new Error(`Ingest endpoint returned ${response.status}: ${detail}`);
      }
    } else if (args.dryRun) {
      // Validate HMAC signing path even in dry-run
      if (hmacSecret) {
        const sig = signBody(ingestBody, hmacSecret);
        if (!sig.startsWith("sha256=")) throw new Error("HMAC signature format wrong");
      }
      await emit("ingest", "Dry-run: ingest POST skipped");
    } else {
      await emit("ingest", "No ingest endpoint configured — skipping POST", { warn: true });
    }

    await emit("ingest", "Ingest complete");

    // ── complete ─────────────────────────────────────────────────────────────
    await emit("complete", `Bootstrap job ${bootstrap_job_id} succeeded`);
  } catch (err) {
    const phase = err._phase ?? "complete";
    await emitError(phase, `Bootstrap failed: ${err.message}`, { stack: err.stack });
    await markFailedFn({ bootstrap_job_id, run_id, error: err }).catch(() => {});
    throw err;
  } finally {
    if (tempDir) {
      await rm(tempDir, { recursive: true, force: true }).catch(() => {});
    }
  }
}

async function linkGovernedPipelineInternals(workDir) {
  const source = process.env.GOVERNED_PIPELINE_NODE_MODULES;
  if (!source) return false;
  await mkdir(path.join(workDir, "node_modules"), { recursive: true });
  await symlink(path.join(source, "@internal"), path.join(workDir, "node_modules", "@internal"), "dir")
    .catch((error) => {
      if (error?.code !== "EEXIST") throw error;
    });
  return true;
}

async function bootstrapTempParent() {
  const parent = process.env.GITHUB_WORKSPACE
    ? path.join(process.env.GITHUB_WORKSPACE, ".pipeline-bootstrap-work")
    : tmpdir();
  await mkdir(parent, { recursive: true });
  return parent;
}

async function prepareCodexApiKeyAuth(workDir) {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) return false;
  const codexHome = path.join(workDir, ".pipeline", "codex");
  await mkdir(codexHome, { recursive: true });
  await writeFile(
    path.join(codexHome, "auth.json"),
    `${JSON.stringify({ OPENAI_API_KEY: apiKey, auth_mode: "apikey" })}\n`,
    { encoding: "utf8", mode: 0o600 }
  );
  return true;
}

function summarizeProcessError(error) {
  const lines = [
    ...(error?.stdout ? String(error.stdout).split(/\r?\n/) : []),
    ...(error?.stderr ? String(error.stderr).split(/\r?\n/) : []),
  ]
    .map((line) => redactLogLine(line.trim()))
    .filter(Boolean);
  const tail = lines.slice(-12).join(" | ");
  return tail || error?.message || "unknown failure";
}

function redactLogLine(line) {
  return line
    .replace(/(token|secret|key|authorization|password)=\S+/gi, "$1=[redacted]")
    .replace(/gh[pousr]_[A-Za-z0-9_]{20,}/g, "[redacted-token]")
    .replace(/[A-Za-z0-9+/]{80,}={0,2}/g, "[redacted-blob]");
}

async function markBootstrapFailure({ bootstrap_job_id, run_id, error }) {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) return;

  const { createClient } = await import("@supabase/supabase-js");
  const supabase = createClient(url, key, { auth: { persistSession: false } });
  const failure = {
    code: "bootstrap_runner_failed",
    message: error?.message ?? "Bootstrap runner failed",
  };

  await supabase
    .from("bootstrap_jobs")
    .update({ status: "failed", error: failure })
    .eq("id", bootstrap_job_id);

  if (run_id) {
    await supabase
      .from("agent_runs")
      .update({ status: "failed", end_time: new Date().toISOString() })
      .eq("id", run_id);
  }
}

function summarizeSynthesisBundle(bundle) {
  const sidecar = bundle?.synthesis?.pipelineReadme?.sidecar;
  const phases = Array.isArray(sidecar?.phases) ? sidecar.phases : [];
  return {
    discovery_artifact_count: bundle?.discovery?.harnessRuns?.length ?? 0,
    architecture_present: Boolean(bundle?.synthesis?.architecture?.markdown),
    pipeline_readme_present: Boolean(bundle?.synthesis?.pipelineReadme?.markdown),
    pipeline_phase_count: phases.filter((phase) => phase?.id || phase?.phase_id).length,
    spec_registry_present: Boolean(bundle?.synthesis?.specRegistry?.markdown),
    harness_consensus_count: bundle?.synthesis?.harnessConsensus?.length ?? 0,
  };
}

/**
 * Reads the synthesis output written by pipeline-init from the working directory.
 * Pipeline-init writes .pipeline/synthesis/ after a brownfield run.
 */
async function readSynthesisBundle(workDir) {
  const { readFile } = await import("node:fs/promises");

  async function readDoc(candidates) {
    for (const candidate of candidates) {
      const mdPath = path.join(workDir, candidate.markdown);
      const jsonPath = path.join(workDir, candidate.sidecar);
      try {
        const markdown = await readFile(mdPath, "utf8");
        let sidecar = {};
        try {
          const raw = await readFile(jsonPath, "utf8");
          sidecar = JSON.parse(raw);
        } catch {}
        return { markdown, sidecar };
      } catch {}
    }
    return { markdown: "", sidecar: {} };
  }

  async function readDiscoveryArtifact(name) {
    try {
      const raw = await readFile(path.join(workDir, ".pipeline", "artifacts", "synthesis", name), "utf8");
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }

  const codeDiscovery = await readDiscoveryArtifact("current-state-discovery.code.json");
  const docsDiscovery = await readDiscoveryArtifact("current-state-discovery.docs.json");
  const diagramsDiscovery = await readDiscoveryArtifact("current-state-discovery.diagrams.json");
  const gitDiscovery = await readDiscoveryArtifact("current-state-discovery.git.json");
  const testsDiscovery = await readDiscoveryArtifact("current-state-discovery.tests.json");

  return {
    discovery: {
      harnessRuns: [
        ["code", codeDiscovery],
        ["docs", docsDiscovery],
        ["diagrams", diagramsDiscovery],
        ["git", gitDiscovery],
        ["tests", testsDiscovery],
      ]
        .filter(([, output]) => Boolean(output))
        .map(([role, output]) => ({
          harness: "pipeline-init",
          role,
          toolCalls: [],
          output,
        })),
      consensusSet: ["ARCHITECTURE.md", "PIPELINE-README.md", "SPEC-GOVERNANCE-CANONICAL-SPEC-REGISTRY.md"],
    },
    synthesis: {
      architecture: await readDoc([
        { markdown: ".pipeline/artifacts/roadmap/ARCHITECTURE.md", sidecar: ".pipeline/artifacts/roadmap/ARCHITECTURE.json" },
        { markdown: ".pipeline/synthesis/ARCHITECTURE.md", sidecar: ".pipeline/synthesis/ARCHITECTURE.json" },
      ]),
      pipelineReadme: await readDoc([
        { markdown: ".pipeline/artifacts/roadmap/PIPELINE-README.md", sidecar: ".pipeline/artifacts/roadmap/PIPELINE-README.json" },
        { markdown: ".pipeline/synthesis/PIPELINE-README.md", sidecar: ".pipeline/synthesis/PIPELINE-README.json" },
      ]),
      specRegistry: await readDoc([
        {
          markdown: ".pipeline/specs/SPEC-GOVERNANCE-CANONICAL-SPEC-REGISTRY.md",
          sidecar: ".pipeline/specs/SPEC-GOVERNANCE-CANONICAL-SPEC-REGISTRY.json",
        },
        {
          markdown: ".pipeline/synthesis/SPEC-GOVERNANCE-CANONICAL-SPEC-REGISTRY.md",
          sidecar: ".pipeline/synthesis/SPEC-GOVERNANCE-CANONICAL-SPEC-REGISTRY.json",
        },
      ]),
      harnessConsensus: ["pipeline-init"],
    },
  };
}

// Emit function that logs to stdout — used in dry-run mode when no Supabase is available
let _consoleSeq = 0;
export async function consoleEmitEvent({ bootstrap_job_id, phase, level = "info", message, data }) {
  _consoleSeq += 1;
  const row = { bootstrap_job_id, seq: _consoleSeq, phase, level, message, at: new Date().toISOString() };
  console.log(JSON.stringify(row));
  return row;
}

// Run when invoked directly
if (process.argv[1] && process.argv[1].endsWith("run.mjs")) {
  const args = parseArgs(process.argv.slice(2));
  const canEmitToSupabase = Boolean(process.env.SUPABASE_URL && process.env.SUPABASE_SERVICE_ROLE_KEY);
  const emitFn = args.dryRun && !canEmitToSupabase ? consoleEmitEvent : emitEvent;
  run({ emitFn }).catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
