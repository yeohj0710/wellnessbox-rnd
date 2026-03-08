const fs = require("node:fs") as typeof import("node:fs");
const pathUtil = require("node:path") as typeof import("node:path");
const {
  buildSkillCatalogMarkdown,
  scanSkillEntries,
} = require("../lib/skill-catalog.cts") as {
  buildSkillCatalogMarkdown: (
    entries: Array<{
      name: string;
      description: string;
      relativePath: string;
    }>
  ) => string;
  scanSkillEntries: (
    repoRoot: string,
    skillsRoot: string
  ) => Array<{
    name: string;
    description: string;
    relativePath: string;
  }>;
};
const { writeIfChanged } = require("../lib/write-if-changed.cts") as {
  writeIfChanged: (options: {
    outputPath: string;
    content: string;
    rootDir?: string;
    encoding?: BufferEncoding;
  }) => {
    changed: boolean;
    outputPath: string;
    relativePath: string;
  };
};

const REPO_ROOT = process.cwd();
const SKILLS_ROOT = pathUtil.join(REPO_ROOT, ".agents", "skills");
const OUTPUT_PATH = pathUtil.join(REPO_ROOT, "AGENT_SKILLS_CATALOG.md");

function main() {
  if (!fs.existsSync(SKILLS_ROOT)) {
    throw new Error(`Skills root not found: ${SKILLS_ROOT}`);
  }

  const entries = scanSkillEntries(REPO_ROOT, SKILLS_ROOT);
  const writeResult = writeIfChanged({
    outputPath: OUTPUT_PATH,
    content: buildSkillCatalogMarkdown(entries),
    rootDir: REPO_ROOT,
  });
  if (writeResult.changed) {
    console.log(`Wrote ${entries.length} skills to ${writeResult.relativePath}`);
  } else {
    console.log(
      `Skill catalog unchanged (${entries.length} skills): ${writeResult.relativePath}`
    );
  }
}

main();
