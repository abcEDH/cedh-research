import { existsSync, readFileSync } from "node:fs";

const failures = [];

if (!existsSync("docs/supported-surfaces.md")) {
  failures.push("Missing docs/supported-surfaces.md");
}

if (!existsSync(".github/pull_request_template.md")) {
  failures.push("Missing .github/pull_request_template.md");
}

if (!existsSync("CONTRIBUTING.md")) {
  failures.push("Missing CONTRIBUTING.md");
}

if (existsSync("docs/supported-surfaces.md")) {
  const content = readFileSync("docs/supported-surfaces.md", "utf8");
  for (const route of ["/cards", "/turn-order", "/survival"]) {
    if (!content.includes(route)) {
      failures.push(`Retired route missing from supported surfaces doc: ${route}`);
    }
  }
}

if (failures.length > 0) {
  for (const failure of failures) {
    console.error(`repo hygiene: ${failure}`);
  }
  process.exit(1);
}

console.log("repo hygiene ok");
