#!/usr/bin/env node
/**
 * Generate TypeScript types from the FastAPI OpenAPI schema.
 *
 * Steps:
 *   1. Run scripts/generate_openapi.py  -> openapi.json
 *   2. Run openapi-typescript            -> packages/shared-types/src/api.d.ts
 *
 * Usage (from repo root):
 *   node scripts/generate-openapi.js
 */

const { execSync } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");

const root = path.resolve(__dirname, "..");
const openapiPath = path.join(root, "openapi.json");
const outPath = path.join(root, "packages", "shared-types", "src", "api.d.ts");
const python = process.env.PYTHON || "python";

function run(cmd, cwd = root) {
  console.log(`$ ${cmd}`);
  execSync(cmd, { cwd, stdio: "inherit" });
}

try {
  run(`${python} ${path.join("scripts", "generate_openapi.py")}`);
} catch {
  console.error("Failed to generate openapi.json. Ensure API deps are installed.");
  process.exit(1);
}

if (!fs.existsSync(openapiPath)) {
  console.error(`openapi.json not found at ${openapiPath}`);
  process.exit(1);
}

fs.mkdirSync(path.dirname(outPath), { recursive: true });
run(`npx --yes openapi-typescript "${openapiPath}" -o "${outPath}"`);

console.log(`\nGenerated types at ${outPath}`);
