#!/usr/bin/env node
/* Deterministic TDD commit guard.
 *
 * Exit 0: the guard passes, the commit may proceed.
 * Exit 1: the guard fails, and says which check and why.
 *
 * Node rather than bash, because bash is not a thing a plugin can count on.
 * Claude Code runs on Node, so Node is present wherever this plugin is — on
 * Windows as much as anywhere else. A guard that only runs on two of the three
 * platforms is not a guard, it is a convention that some people happen to be
 * held to.
 *
 * Detection is by file name, not by directory: a changed file counts as
 * production code when it has a recognized source extension and its name does
 * NOT match a test-naming pattern, and as a test when it does. That works for a
 * flat root (wordcount.py + test_wordcount.py) exactly as it does for
 * src/ + tests/, with no per-project glob to edit in the common case.
 *
 * Override only when a project's conventions genuinely do not fit -- a
 * non-standard test suffix, say. Set PRODUCTION_EXTS / TEST_NAME_PATTERNS as
 * environment variables, space-separated. Do not "fix" a false FAIL by
 * loosening these for one commit: fix the pattern once, here, if it is truly
 * wrong for every commit.
 *
 * The last test run is read from a file, not an environment variable, because a
 * variable set by one command does not survive into the next. Write the real
 * exit code to $SEED_LAST_TEST_RESULT_FILE (default
 * memory-bank/.local/last-test-exit-code) right after running the suite:
 *   npm test; echo $? > memory-bank/.local/last-test-exit-code
 */

import { spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";

const PRODUCTION_EXTS = (process.env.PRODUCTION_EXTS ?? "py js ts jsx tsx go rs java rb php c cpp h hpp cs").split(/\s+/).filter(Boolean);
const TEST_NAME_PATTERNS = (process.env.TEST_NAME_PATTERNS ?? "test_* *_test.* *.test.* *.spec.*").split(/\s+/).filter(Boolean);
const LAST_TEST_RESULT_FILE = process.env.SEED_LAST_TEST_RESULT_FILE ?? "memory-bank/.local/last-test-exit-code";

/** Git reports forward slashes on every platform, Windows included. Backslashes
    are handled anyway so the verdict never depends on who produced the path. */
export function basename(path) {
  const cut = Math.max(path.lastIndexOf("/"), path.lastIndexOf("\\"));
  return cut === -1 ? path : path.slice(cut + 1);
}

/** The handful of glob forms these patterns use -- `*` for any run of
    characters -- rather than a dependency for four literals. */
export function matchesName(name, pattern) {
  const expression = pattern.split("*").map((part) => part.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join(".*");
  return new RegExp(`^${expression}$`).test(name);
}

export function isTestFile(path, patterns = TEST_NAME_PATTERNS) {
  return patterns.some((pattern) => matchesName(basename(path), pattern));
}

export function isProductionFile(path, extensions = PRODUCTION_EXTS, patterns = TEST_NAME_PATTERNS) {
  const name = basename(path);
  const dot = name.lastIndexOf(".");
  if (dot <= 0) return false;
  return extensions.includes(name.slice(dot + 1)) && !isTestFile(path, patterns);
}

/** The whole decision, as a function of its inputs, so it can be tested without
    a repository and without a commit. */
export function evaluate({ staged, lastTestExitCode, extensions = PRODUCTION_EXTS, patterns = TEST_NAME_PATTERNS }) {
  if (staged.length === 0) return { ok: true, message: "nothing staged, nothing to check." };

  const testChanged = staged.some((change) => isTestFile(change.path, patterns));
  /* A deletion needs nothing added: removing code is not an untested change,
     and failing it here blocks an ordinary cleanup commit for no TDD reason. */
  const productionFiles = staged
    .filter((change) => !change.status.toUpperCase().startsWith("D") && isProductionFile(change.path, extensions, patterns))
    .map((change) => change.path);

  if (productionFiles.length > 0 && !testChanged) {
    return {
      ok: false,
      message: `FAIL — production file(s) added or changed with no test file in this commit:\n${productionFiles.join("\n")}`,
    };
  }

  /* Read from a recorded run rather than trusted from a claim. A project that
     never ran its suite has proved nothing in either direction, and treating
     that silence as green is what makes the check decorative. */
  if (lastTestExitCode === undefined) {
    return { ok: false, message: `FAIL — no recorded test result at ${LAST_TEST_RESULT_FILE}. Run the test suite and write its exit code there before committing (see this script's header).` };
  }
  if (lastTestExitCode !== "0") {
    return { ok: false, message: `FAIL — last recorded test run exited non-zero (${lastTestExitCode}), per ${LAST_TEST_RESULT_FILE}.` };
  }

  return { ok: true, message: "PASS" };
}

function main() {
  const inside = spawnSync("git", ["rev-parse", "--is-inside-work-tree"], { encoding: "utf8" });
  if (inside.status !== 0) {
    console.error("commit-guard: FAIL — not inside a git repository (run this from the project root, after `git init`).");
    process.exit(1);
  }

  const diff = spawnSync("git", ["diff", "--cached", "--name-status"], { encoding: "utf8" });
  if (diff.status !== 0) {
    console.error(`commit-guard: FAIL — could not read the staged diff: ${diff.stderr?.trim() || "git failed"}`);
    process.exit(1);
  }

  const staged = diff.stdout.split("\n").filter(Boolean).map((line) => {
    const parts = line.split("\t");
    /* A rename reports two paths; the one that now exists is the last. */
    return { status: parts[0] ?? "", path: parts[parts.length - 1] ?? "" };
  }).filter((change) => change.path);

  const lastTestExitCode = existsSync(LAST_TEST_RESULT_FILE) ? readFileSync(LAST_TEST_RESULT_FILE, "utf8").trim() : undefined;

  const verdict = evaluate({ staged, lastTestExitCode });
  if (verdict.ok) {
    console.log(`commit-guard: ${verdict.message}`);
    process.exit(0);
  }
  console.error(`commit-guard: ${verdict.message}`);
  process.exit(1);
}

/* Importable for tests, runnable as a command. */
if (process.argv[1] && import.meta.url === new URL(`file://${process.argv[1].replace(/\\/g, "/")}`).href) main();
