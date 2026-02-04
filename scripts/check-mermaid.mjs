import { execSync } from 'node:child_process';
import { readFileSync } from 'node:fs';

const mdFiles = execSync('git ls-files "*.md"', { encoding: 'utf8' })
  .split('\n')
  .map((line) => line.trim())
  .filter(Boolean);

const errors = [];

const mermaidBlockRegex = /```mermaid\n([\s\S]*?)```/g;
const labelRegex = /\[[^\]]+\]/g;

for (const file of mdFiles) {
  const contents = readFileSync(file, 'utf8');
  let match;
  while ((match = mermaidBlockRegex.exec(contents)) !== null) {
    const block = match[1];
    if (block.includes('\\n')) {
      errors.push(`${file}: mermaid block contains literal \\n; use single-line labels instead.`);
    }
    if (block.includes('<br/>') || block.includes('<br />')) {
      errors.push(`${file}: mermaid block contains <br/>; GitHub Mermaid parser rejects HTML in labels.`);
    }

    const labels = block.match(labelRegex) ?? [];
    for (const label of labels) {
      const content = label.slice(1, -1).trim();
      if (!content.startsWith('"') || !content.endsWith('"')) {
        errors.push(`${file}: label ${label} must be quoted like ["..."] for GitHub Mermaid compatibility.`);
        continue;
      }
      const inner = content.slice(1, -1);
      if (inner.includes('(') || inner.includes(')') || inner.includes(',')) {
        errors.push(`${file}: label ${label} contains parentheses or commas; replace with separators like "·" or ":".`);
      }
    }
  }
}

if (errors.length > 0) {
  console.error('Mermaid lint failed:\n' + errors.map((err) => `- ${err}`).join('\n'));
  process.exit(1);
}

console.log('Mermaid lint passed.');
