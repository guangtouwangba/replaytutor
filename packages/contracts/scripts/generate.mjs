import { compile } from "json-schema-to-typescript";
import { mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import process from "node:process";

const packageRoot = resolve(import.meta.dirname, "..");
const schemaPath = resolve(packageRoot, "schema/contracts.json");
const outputDir = resolve(packageRoot, "src/generated");
const check = process.argv.includes("--check");
const document = JSON.parse(await readFile(schemaPath, "utf8"));

const generated = [];
for (const [name, schema] of Object.entries(document.models)) {
  const source = await compile(schema, name, {
    bannerComment: "",
    format: true,
    style: { singleQuote: false, semi: true, tabWidth: 2 },
  });
  generated.push({ name, source: `// Generated from Pydantic. Do not edit.\n\n${source.trim()}\n` });
}

const contracts = `// Generated from Pydantic. Do not edit.\n${generated.map(({ name }) => `export type { ${name} } from "./models/${name}";`).join("\n")}\n`;
const validators = `// Generated from Pydantic. Do not edit.\nimport Ajv from "ajv";\nimport type { ValidateFunction } from "ajv";\nimport addFormats from "ajv-formats";\n\nconst schemas = ${JSON.stringify(document.models, null, 2)} as const;\nconst ajv = new Ajv({ allErrors: true, strict: false });\naddFormats(ajv);\nconst cache = new Map<string, ValidateFunction>();\n\nexport function validateContract<T>(name: keyof typeof schemas, value: unknown): value is T {\n  let validator = cache.get(name);\n  if (!validator) {\n    validator = ajv.compile(schemas[name]);\n    cache.set(name, validator);\n  }\n  return validator(value) as boolean;\n}\n\nexport function contractValidationErrors(name: keyof typeof schemas): readonly unknown[] {\n  return cache.get(name)?.errors ?? [];\n}\n`;

async function update(path, content) {
  if (check) {
    let current = "";
    try { current = await readFile(path, "utf8"); } catch { /* reported below */ }
    if (current !== content) {
      console.error(`Generated contract is stale: ${path}`);
      process.exitCode = 1;
    }
    return;
  }
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, content);
}

await update(resolve(outputDir, "contracts.ts"), contracts);
await update(resolve(outputDir, "validators.ts"), validators);
for (const { name, source } of generated) {
  await update(resolve(outputDir, "models", `${name}.ts`), source);
}
if (!check) {
  await rm(resolve(outputDir, "legacy.ts"), { force: true });
}
