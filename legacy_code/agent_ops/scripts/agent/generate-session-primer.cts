const fs = require("node:fs") as typeof import("node:fs");
const pathUtil = require("node:path") as typeof import("node:path");
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

type FileHotspotRow = {
  lines: number;
  file: string;
};

type FunctionHotspotRow = {
  lines: number;
  name: string;
  location: string;
};

type GuardSummary = {
  totalRoutes: string;
  guardedRoutes: string;
  expectedSessionRoutes: string;
  unexpectedReviewNeeded: string;
  missingMethodExports: string;
  publicOrInternalCandidates: string;
  guardPolicyViolations: string;
};

const REPO_ROOT = process.cwd();
const REFACTOR_REPORT_PATH = pathUtil.join(REPO_ROOT, "REFACTOR_HOTSPOTS.md");
const FUNCTION_REPORT_PATH = pathUtil.join(REPO_ROOT, "FUNCTION_HOTSPOTS.md");
const GUARD_REPORT_PATH = pathUtil.join(REPO_ROOT, "API_GUARD_MAP.md");
const REFACTOR_BACKLOG_PATH = pathUtil.join(REPO_ROOT, "REFACTOR_BACKLOG.md");
const OUTPUT_PATH = pathUtil.join(REPO_ROOT, "AGENT_SESSION_PRIMER.md");

type DomainEntryPoint = {
  label: string;
  detail: string;
};

const OPTIONAL_READ_NEXT_FILES = [
  "AGENT_PRECHECK.md",
  "REFACTOR_BACKLOG.md",
  "API_GUARD_MAP.md",
  "FUNCTION_HOTSPOTS.md",
  "REFACTOR_HOTSPOTS.md",
  "CHAT_AGENT_HANDOFF.md",
];

const DOMAIN_ENTRY_POINTS: DomainEntryPoint[] = [
  {
    label: "B2B admin reports",
    detail:
      "Start with `app/(admin)/admin/b2b-reports/B2bAdminReportClient.tsx`, then `app/(admin)/admin/b2b-reports/_lib/use-b2b-admin-report-detail-state.ts`, then `app/(admin)/admin/b2b-reports/_components/B2bAdminReportWorkspace.tsx`, then the integrated preview boundary `B2bIntegratedResultPreview.tsx`, `B2bIntegratedHealthMetricsSection.tsx`, `B2bIntegratedMedicationReviewSection.tsx`, and `_lib/b2b-integrated-result-preview-model.ts`, then `app/(admin)/admin/b2b-reports/_lib/use-b2b-admin-report-actions.ts`.",
  },
  {
    label: "Employee report",
    detail:
      "Start with `app/(features)/employee-report/EmployeeReportClient.tsx`, then the flow panels under `app/(features)/employee-report/_components/`, then the focused hooks under `app/(features)/employee-report/_lib/`, especially `client-utils.identity.ts`, `client-utils.request.ts`, and `client-utils.guidance.ts`.",
  },
  {
    label: "My data",
    detail:
      "Start with `app/my-data/page.tsx`, then `app/my-data/myDataPageData.ts`, then the focused section modules `myDataPageOverviewSections.tsx`, `myDataPageOrderSection.tsx`, `myDataPageResultSections.tsx`, and `myDataPageChatSection.tsx`. Keep `myDataPageSections.tsx` as the stable export surface only.",
  },
  {
    label: "Cart and order flow",
    detail:
      "Start with `components/order/cart.tsx`, then `components/order/hooks/useCartInteractionController.ts`, then `components/order/hooks/useCartPayment.ts`, then `app/(orders)/order-complete/page.tsx` together with `useOrderCompleteBootstrap.ts`, `useOrderCompleteNotifications.ts`, and `orderCompleteFlow.ts`. Keep stock/order mutations inside `lib/order/mutations.ts`.",
  },
  {
    label: "Home explore",
    detail:
      "Start with `app/(components)/homeProductSection.tsx`, then the extracted data hook `app/(components)/useHomeProductSectionData.ts`, then the view shell `app/(components)/homeProductSection.content.tsx`, then the pharmacy/actions/effects helpers around it.",
  },
  {
    label: "Column editor",
    detail:
      "Start with `app/(admin)/admin/column/editor/EditorAdminClient.tsx`, then `app/(admin)/admin/column/editor/_lib/use-column-editor-controller.ts`, then the focused subhooks `use-column-editor-post-actions.ts` and `use-column-editor-markdown-media.ts`, then the workspace/sidebar components under `app/(admin)/admin/column/editor/_components/`. Treat `app/column/editor/page.tsx` as redirect-only; there is no standalone legacy editor client.",
  },
  {
    label: "Public columns",
    detail:
      "Start with `app/column/_lib/columns.ts`, then the pure summary-query module `app/column/_lib/columns-summary-queries.ts`, then shared parsing/tag helpers in `app/column/_lib/columns-content-utils.ts`, and finally the DB/file source adapters `columns-db-source.ts` and `columns-file-source.ts`.",
  },
  {
    label: "Chat",
    detail:
      "Start with `app/chat/hooks/useChat.ts`, then `app/chat/hooks/useChat.commandLayer.ts`, then the recommendation hydration boundary `useChat.recommendation.ts` and `useChat.recommendation.catalog.ts`, then the interactive action boundary `useChat.interactiveActions.ts`, `useChat.interactiveActions.routes.ts`, and `useChat.interactiveActions.types.ts`, then the chat input boundary `app/chat/components/ChatInput.tsx`, `useChatInputController.ts`, `ChatInputActionAssist.tsx`, `chatInput.actions.ts`, and `chatInput.types.ts`, then the chat CTA surfaces under `app/chat/components/` especially `RecommendedProductActions.tsx`, `useRecommendedProductActionsController.ts`, and the focused resolve helpers `recommendedProductActions.resolve.ts`, `recommendedProductActions.resolve.catalog.ts`, `recommendedProductActions.resolve.name.ts`, `recommendedProductActions.resolve.category.ts`, then the dock shell files under `components/chat/` especially `DesktopChatDock.tsx`, `useDesktopChatDockLauncher.ts`, `DesktopChatDockPanel.tsx`, `useDesktopChatDockPanelShell.ts`, and the stable layout helpers `DesktopChatDock.layout.ts`, `DesktopChatDock.layout.geometry.ts`, and `DesktopChatDock.layout.storage.ts`, then `app/api/chat/route.ts` and shared prompt/context logic under `lib/chat/`.",
  },
  {
    label: "Health-link and NHIS",
    detail:
      "Start with `app/(features)/health-link/HealthLinkClient.tsx`, `app/api/health/nhis/fetch/route.ts`, and helpers under `lib/server/hyphen/`.",
  },
  {
    label: "Assess",
    detail:
      "Start with `app/assess/page.tsx`, then `app/assess/useAssessFlow.ts`, then the extracted boundaries `useAssessFlow.derived.ts`, `useAssessFlow.lifecycle.ts`, and `useAssessFlow.types.ts`, then the C-section modules under `app/assess/components/` especially `useCSectionController.ts`.",
  },
];

function readUtf8(filePath: string) {
  if (!fs.existsSync(filePath)) {
    throw new Error(`Required report missing: ${filePath}`);
  }
  return fs.readFileSync(filePath, "utf8");
}

function readUtf8IfExists(filePath: string) {
  if (!fs.existsSync(filePath)) return null;
  return fs.readFileSync(filePath, "utf8");
}

function extractSection(source: string, heading: string) {
  const marker = `## ${heading}`;
  const start = source.indexOf(marker);
  if (start < 0) return "";

  const afterStart = source.slice(start + marker.length);
  const nextHeadingOffset = afterStart.indexOf("\n## ");
  return nextHeadingOffset >= 0
    ? afterStart.slice(0, nextHeadingOffset)
    : afterStart;
}

function parseMarkdownTableRows(section: string) {
  const rows: string[][] = [];
  for (const rawLine of section.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line.startsWith("|")) continue;
    if (line.includes("|---")) continue;
    const cells = line
      .split("|")
      .slice(1, -1)
      .map((cell) => cell.trim());
    if (cells.length === 0) continue;
    if (cells.every((cell) => cell.length === 0)) continue;
    rows.push(cells);
  }
  return rows;
}

function stripInlineCode(value: string) {
  return value.replace(/`/g, "");
}

function parseFileHotspots(source: string, heading: string, limit: number) {
  const section = extractSection(source, heading);
  const tableRows = parseMarkdownTableRows(section);
  const parsed: FileHotspotRow[] = [];
  for (const row of tableRows) {
    if (row.length < 2) continue;
    if (!/\d/.test(row[0])) continue;
    const lines = Number(row[0].replace(/[^\d]/g, ""));
    const file = stripInlineCode(row[1]);
    if (!Number.isFinite(lines) || !file) continue;
    parsed.push({ lines, file });
    if (parsed.length >= limit) break;
  }
  return parsed;
}

function parseFunctionHotspots(source: string, heading: string, limit: number) {
  const section = extractSection(source, heading);
  const tableRows = parseMarkdownTableRows(section);
  const parsed: FunctionHotspotRow[] = [];
  for (const row of tableRows) {
    if (row.length < 4) continue;
    if (!/\d/.test(row[0])) continue;
    const lines = Number(row[0].replace(/[^\d]/g, ""));
    const name = stripInlineCode(row[2]);
    const location = stripInlineCode(row[3]);
    if (!Number.isFinite(lines) || !name || !location) continue;
    parsed.push({ lines, name, location });
    if (parsed.length >= limit) break;
  }
  return parsed;
}

function parseGuardSummary(source: string): GuardSummary {
  const fallback = "N/A";
  const capture = (label: string) => {
    const pattern = new RegExp(`- ${label}: \\*\\*([^*]+)\\*\\*`);
    const match = source.match(pattern);
    return match?.[1]?.trim() || fallback;
  };

  return {
    totalRoutes: capture("Total routes"),
    guardedRoutes: capture("Guarded routes"),
    expectedSessionRoutes: capture("Expected session-managed routes"),
    unexpectedReviewNeeded: capture("Unexpected review needed"),
    missingMethodExports: capture("Missing method exports"),
    publicOrInternalCandidates: capture("Public/Internal candidate routes"),
    guardPolicyViolations: capture("Guard policy violations"),
  };
}

function parseRecentBacklogItems(source: string, heading: string, limit: number) {
  const section = extractSection(source, heading);
  const items: string[] = [];
  for (const rawLine of section.split(/\r?\n/)) {
    const line = rawLine.trim();
    const match = line.match(/^\d+\.\s+(.+)$/);
    if (!match) continue;
    items.push(match[1].trim());
  }
  return items.slice(-limit).reverse();
}

function buildMarkdown(input: {
  runtimeFileHotspots: FileHotspotRow[];
  runtimeFunctionHotspots: FunctionHotspotRow[];
  guardSummary: GuardSummary;
  readNextFiles: string[];
  recentBacklogItems: string[];
}) {
  const lines: string[] = [];
  lines.push("# Agent Session Primer");
  lines.push("");
  lines.push("Auto-generated by `scripts/agent/generate-session-primer.cts`.");
  lines.push(
    "Run `npm run agent:context-refresh` (or `npm run agent:session-primer`) to refresh."
  );
  lines.push("");
  lines.push("## Fast Start");
  lines.push("");
  lines.push("1. `npm run audit:encoding`");
  lines.push("2. `npm run audit:hotspots`");
  lines.push("3. `npm run agent:guard-map`");
  lines.push("4. `npm run lint`");
  lines.push("5. `npm run build`");
  lines.push("");
  lines.push("## Read Next");
  lines.push("");
  for (const file of input.readNextFiles) {
    lines.push(`- \`${file}\``);
  }
  lines.push("");
  lines.push("## Domain Entry Points");
  lines.push("");
  for (const entry of DOMAIN_ENTRY_POINTS) {
    lines.push(`- ${entry.label}: ${entry.detail}`);
  }
  lines.push("");
  lines.push("## Guard Snapshot");
  lines.push("");
  lines.push(`- Total routes: **${input.guardSummary.totalRoutes}**`);
  lines.push(`- Guarded routes: **${input.guardSummary.guardedRoutes}**`);
  lines.push(
    `- Expected session-managed routes: **${input.guardSummary.expectedSessionRoutes}**`
  );
  lines.push(
    `- Unexpected review needed: **${input.guardSummary.unexpectedReviewNeeded}**`
  );
  lines.push(
    `- Missing method exports: **${input.guardSummary.missingMethodExports}**`
  );
  lines.push(
    `- Public/Internal candidate routes: **${input.guardSummary.publicOrInternalCandidates}**`
  );
  lines.push(
    `- Guard policy violations: **${input.guardSummary.guardPolicyViolations}**`
  );
  lines.push("");
  if (input.recentBacklogItems.length > 0) {
    lines.push("## Recent Refactors");
    lines.push("");
    for (const item of input.recentBacklogItems) {
      lines.push(`- ${item}`);
    }
    lines.push("");
  }
  lines.push("## Runtime File Hotspots (Top 12)");
  lines.push("");
  for (const row of input.runtimeFileHotspots) {
    lines.push(`- ${String(row.lines).padStart(4, " ")} lines: \`${row.file}\``);
  }
  lines.push("");
  lines.push("## Runtime Function Hotspots (Top 12)");
  lines.push("");
  for (const row of input.runtimeFunctionHotspots) {
    lines.push(
      `- ${String(row.lines).padStart(4, " ")} lines: \`${row.name}\` (\`${row.location}\`)`
    );
  }
  lines.push("");
  lines.push("## Critical Edit Invariants");
  lines.push("");
  lines.push(
    "- Order integrity: keep stock decrement only inside `lib/order/mutations.ts:createOrder` transaction."
  );
  lines.push(
    "- Route ownership/auth: use guards from `lib/server/route-auth.ts` only."
  );
  lines.push("- Prisma: keep singleton pattern in `lib/db.ts`.");
  lines.push(
    "- Admin gate: keep `app/api/verify-password/route.ts`, `lib/admin-token.ts`, and `middleware.ts` aligned."
  );
  lines.push("");
  return lines.join("\n");
}

function main() {
  const refactorReport = readUtf8(REFACTOR_REPORT_PATH);
  const functionReport = readUtf8(FUNCTION_REPORT_PATH);
  const guardReport = readUtf8(GUARD_REPORT_PATH);
  const refactorBacklog = readUtf8IfExists(REFACTOR_BACKLOG_PATH) ?? "";

  const runtimeFileHotspots = parseFileHotspots(refactorReport, "Runtime Top 25", 12);
  const runtimeFunctionHotspots = parseFunctionHotspots(
    functionReport,
    "Runtime Top 50",
    12
  );
  const guardSummary = parseGuardSummary(guardReport);
  const readNextFiles = OPTIONAL_READ_NEXT_FILES.filter((file) =>
    fs.existsSync(pathUtil.join(REPO_ROOT, file))
  );
  const recentBacklogItems = parseRecentBacklogItems(
    refactorBacklog,
    "Completed in this cycle",
    8
  );

  const markdown = buildMarkdown({
    runtimeFileHotspots,
    runtimeFunctionHotspots,
    guardSummary,
    readNextFiles,
    recentBacklogItems,
  });

  const writeResult = writeIfChanged({
    outputPath: OUTPUT_PATH,
    content: markdown,
    rootDir: REPO_ROOT,
  });
  if (writeResult.changed) {
    console.log(`Wrote session primer: ${writeResult.relativePath}`);
  } else {
    console.log(`Session primer unchanged: ${writeResult.relativePath}`);
  }
}

main();
