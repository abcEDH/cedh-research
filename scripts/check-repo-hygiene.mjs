import { existsSync, readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";

const failures = [];
const plannedRetirementRoutes = ["/cards", "/turn-order", "/survival"];
const generatedPaths = [
  {
    dir: "apps/web/playwright-report",
    allow: [],
    label: "Playwright report output",
  },
  {
    dir: "packages/backend/reports",
    allow: ["packages/backend/reports/README.md"],
    label: "backend report outputs",
  },
];

if (!existsSync("docs/supported-surfaces.md")) {
  failures.push("Missing docs/supported-surfaces.md");
}

if (!existsSync(".github/pull_request_template.md")) {
  failures.push("Missing .github/pull_request_template.md");
} else {
  const prTemplate = readFileSync(".github/pull_request_template.md", "utf8");
  if (!prTemplate.includes("## What needs human verification")) {
    failures.push("Missing 'What needs human verification' section in PR template");
  }
}

if (!existsSync("CONTRIBUTING.md")) {
  failures.push("Missing CONTRIBUTING.md");
}

if (existsSync("docs/supported-surfaces.md")) {
  const content = readFileSync("docs/supported-surfaces.md", "utf8");
  if (!content.includes("## Planned Retirement")) {
    failures.push("Missing planned-retirement section in supported surfaces doc");
  }
  for (const route of plannedRetirementRoutes) {
    if (!content.includes(route)) {
      failures.push(`Planned-retirement route missing from supported surfaces doc: ${route}`);
    }
  }
}

for (const { dir, allow, label } of generatedPaths) {
  const tracked = execFileSync("git", ["ls-files", "--", dir], { encoding: "utf8" })
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  const unexpected = tracked.filter((file) => !allow.includes(file));
  if (unexpected.length > 0) {
    failures.push(`Tracked ${label} found: ${unexpected.join(", ")}`);
  }
}

if (failures.length > 0) {
  for (const failure of failures) {
    console.error(`repo hygiene: ${failure}`);
  }
  process.exit(1);
}

console.log("repo hygiene ok");
