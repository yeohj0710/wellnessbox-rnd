const fs = require("node:fs") as typeof import("node:fs");
const pathUtil = require("node:path") as typeof import("node:path");

type SkillEntry = {
  name: string;
  description: string;
  relativePath: string;
};

function walkSkillFiles(dir: string): string[] {
  if (!fs.existsSync(dir)) return [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const out: string[] = [];

  for (const entry of entries) {
    const fullPath = pathUtil.join(dir, entry.name);
    if (!entry.isDirectory()) continue;
    const skillFile = pathUtil.join(fullPath, "SKILL.md");
    if (fs.existsSync(skillFile)) {
      out.push(skillFile);
      continue;
    }
    out.push(...walkSkillFiles(fullPath));
  }

  return out;
}

function extractFrontmatterBlock(markdown: string) {
  if (!markdown.startsWith("---")) return null;
  const match = markdown.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!match) return null;
  return match[1];
}

function unquote(value: string) {
  return value.replace(/^"(.*)"$/, "$1").replace(/^'(.*)'$/, "$1");
}

function readScalarValue(lines: string[], key: string): string | undefined {
  const keyPattern = new RegExp(`^${key}:\\s*(.*)$`);
  const topLevelKeyPattern = /^[A-Za-z0-9_-]+:\s*/;

  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];
    const match = line.match(keyPattern);
    if (!match) continue;

    const initialValue = match[1].trim();
    if (initialValue.length > 0 && initialValue !== "|" && initialValue !== ">") {
      return unquote(initialValue);
    }

    const continuation: string[] = [];
    for (let j = i + 1; j < lines.length; j += 1) {
      const next = lines[j];
      if (topLevelKeyPattern.test(next)) break;
      if (!/^\s+/.test(next)) break;
      continuation.push(next.trim());
    }

    const joined =
      initialValue === "|"
        ? continuation.join("\n")
        : continuation.join(" ");
    if (joined.trim().length > 0) {
      return unquote(joined.trim());
    }
    return undefined;
  }

  return undefined;
}

function readFrontmatter(markdown: string): Record<string, string> {
  const block = extractFrontmatterBlock(markdown);
  if (!block) return {};

  const lines = block.split(/\r?\n/);
  const name = readScalarValue(lines, "name");
  const description = readScalarValue(lines, "description");

  const out: Record<string, string> = {};
  if (name) out.name = name;
  if (description) out.description = description;
  return out;
}

function extractEntry(repoRoot: string, skillFile: string): SkillEntry {
  const raw = fs.readFileSync(skillFile, "utf8");
  const frontmatter = readFrontmatter(raw);
  const fallbackName = pathUtil.basename(pathUtil.dirname(skillFile));
  const name = frontmatter.name || fallbackName;
  const description =
    frontmatter.description || "No description found in frontmatter.";
  const relativePath = pathUtil.relative(repoRoot, skillFile).replace(/\\/g, "/");
  return { name, description, relativePath };
}

function scanSkillEntries(repoRoot: string, skillsRoot: string): SkillEntry[] {
  const files = walkSkillFiles(skillsRoot);
  return files
    .map((skillFile) => extractEntry(repoRoot, skillFile))
    .sort((a, b) => a.name.localeCompare(b.name));
}

function buildSkillCatalogMarkdown(entries: SkillEntry[]) {
  const lines: string[] = [];
  lines.push("# Agent Skills Catalog");
  lines.push("");
  lines.push("Auto-generated from `.agents/skills/**/SKILL.md`. Regenerate with:");
  lines.push("```bash");
  lines.push("npx ts-node scripts/agent/generate-skill-catalog.cts");
  lines.push("```");
  lines.push("");
  lines.push("Run `npm run agent:skills-catalog` to refresh this catalog.");
  lines.push("");
  lines.push("| Skill | Description | Path |");
  lines.push("|---|---|---|");
  for (const entry of entries) {
    lines.push(
      `| \`${entry.name}\` | ${entry.description.replace(/\|/g, "\\|")} | \`${entry.relativePath}\` |`
    );
  }
  lines.push("");
  return lines.join("\n");
}

module.exports = {
  buildSkillCatalogMarkdown,
  scanSkillEntries,
};
