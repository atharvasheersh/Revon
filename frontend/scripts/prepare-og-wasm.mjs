/**
 * @vercel/og 1.0.3 bundles HarfBuzz's JS loader but omits its hb.wasm asset.
 * Supply the installed binary to that loader so Node ESM and worker bundles
 * do not depend on CommonJS require(), __dirname or a runtime file fetch.
 * Remove this workaround when upgrading to an upstream self-contained build.
 */
import { readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";

const require = createRequire(import.meta.url);
const packagePath = require.resolve("@vercel/og/package.json");
const { version } = JSON.parse(readFileSync(packagePath, "utf8"));
if (version !== "1.0.3") {
  throw new Error("Review the HarfBuzz packaging workaround before changing @vercel/og.");
}
const wasm = readFileSync(require.resolve("harfbuzzjs/hb.wasm"));
if (!WebAssembly.validate(wasm)) throw new Error("Invalid HarfBuzz WASM asset.");
const binary = `Uint8Array.from(atob("${wasm.toString("base64")}"), (c) => c.charCodeAt(0))`;
const originalEnvironment = 'var ENVIRONMENT_IS_NODE = typeof process == "object" && process.versions?.node && process.type != "renderer";';
const patchedEnvironment = 'var ENVIRONMENT_IS_NODE = false; /* Revon: supply the packaged WASM directly. */';
const originalInit = "hb().then((instance) => {";
const patchedInit = `hb({wasmBinary: ${binary}}).then((instance) => {`;

const replacements = [];
for (const name of ["index.node.js", "index.edge.js"]) {
  const path = join(dirname(packagePath), "dist", name);
  const source = readFileSync(path, "utf8");
  if (source.includes(patchedEnvironment)) {
    if (source.split(patchedEnvironment).length !== 2 || source.split(patchedInit).length !== 2) {
      throw new Error(`Unexpected prepared HarfBuzz loader in ${name}.`);
    }
    continue;
  }
  if (source.split(originalEnvironment).length !== 2 || source.split(originalInit).length !== 2) {
    throw new Error(`Unexpected @vercel/og loader in ${name}; review the workaround.`);
  }
  replacements.push([path, source
    .replace(originalEnvironment, patchedEnvironment)
    .replace(originalInit, patchedInit)]);
}
// Preflight both bundles before writing either file. Repeated installs are safe.
for (const [path, source] of replacements) writeFileSync(path, source);
console.log("Prepared self-contained HarfBuzz WASM for @vercel/og.");
