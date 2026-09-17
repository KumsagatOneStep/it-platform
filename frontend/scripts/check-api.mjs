// Проверяет, что src/api/schema.d.ts сгенерирован из актуального backend/openapi.json.
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const COMMITTED = "src/api/schema.d.ts";
const dir = mkdtempSync(join(tmpdir(), "openapi-types-"));
const generated = join(dir, "schema.d.ts");

try {
  execFileSync(
    join("node_modules", ".bin", "openapi-typescript"),
    [process.env.OPENAPI_PATH ?? "../backend/openapi.json", "-o", generated],
    { stdio: "ignore" },
  );
  if (readFileSync(generated, "utf8") !== readFileSync(COMMITTED, "utf8")) {
    console.error(`${COMMITTED} устарел: выполните \`npm run gen:api\` и закоммитьте результат`);
    process.exitCode = 1;
  }
} finally {
  rmSync(dir, { recursive: true, force: true });
}
