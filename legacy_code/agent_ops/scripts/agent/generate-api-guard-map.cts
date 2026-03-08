const pathUtil = require("node:path") as typeof import("node:path");

type RouteClassification =
  | "guarded"
  | "review_expected"
  | "review_unexpected"
  | "public_or_internal";

type GuardMapEntry = {
  file: string;
  route: string;
  methods: string[];
  guards: string[];
  directGuards: string[];
  importsRouteAuth: boolean;
  usesGetSession: boolean;
  note: string | null;
  classification: RouteClassification;
};

type GuardMapGroups = {
  guarded: Array<{ route: string }>;
  expectedReview: Array<{ route: string }>;
  unexpectedReview: Array<{ route: string }>;
  publicOrInternal: Array<{ route: string }>;
  missingMethodExports: Array<{ route: string }>;
};

type GuardPolicy = {
  routePrefix: string;
  requiredTokens: string[];
  note: string;
};

type GuardPolicyViolation = {
  route: string;
  file: string;
  guards: string[];
  requiredTokens: string[];
  missingTokens: string[];
  note: string;
};

const {
  EXPECTED_SESSION_ROUTE_ENTRIES,
  ROUTE_GUARD_POLICIES,
  ROUTE_GUARD_TOKENS,
} = require("../lib/api-route-guard-config.cts") as {
  EXPECTED_SESSION_ROUTE_ENTRIES: Array<{
    route: string;
    routeFile: string;
    note: string;
  }>;
  ROUTE_GUARD_POLICIES: GuardPolicy[];
  ROUTE_GUARD_TOKENS: string[];
};
const {
  buildGuardMapMarkdown,
  evaluateRouteGuardPolicies,
  groupRouteEntries,
  scanApiGuardEntries,
} = require("../lib/guard-map.cts") as {
  buildGuardMapMarkdown: (input: {
    entries: GuardMapEntry[];
    groups: GuardMapGroups;
    policyViolations?: GuardPolicyViolation[];
  }) => string;
  evaluateRouteGuardPolicies: (
    entries: GuardMapEntry[],
    policies: GuardPolicy[]
  ) => GuardPolicyViolation[];
  groupRouteEntries: (entries: GuardMapEntry[]) => GuardMapGroups;
  scanApiGuardEntries: (input: {
    repoRoot: string;
    apiRoot: string;
    routeGuardTokens: string[];
    expectedSessionRouteNotes: Record<string, string>;
  }) => GuardMapEntry[];
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
const API_ROOT = pathUtil.join(REPO_ROOT, "app", "api");
const OUTPUT_PATH = pathUtil.join(REPO_ROOT, "API_GUARD_MAP.md");

const EXPECTED_SESSION_ROUTES: Record<string, string> = Object.fromEntries(
  EXPECTED_SESSION_ROUTE_ENTRIES.map((item) => [item.route, item.note])
);

function main() {
  const strict = process.argv.includes("--strict");
  const entries = scanApiGuardEntries({
    repoRoot: REPO_ROOT,
    apiRoot: API_ROOT,
    routeGuardTokens: ROUTE_GUARD_TOKENS,
    expectedSessionRouteNotes: EXPECTED_SESSION_ROUTES,
  });
  const groups = groupRouteEntries(entries);
  const policyViolations = evaluateRouteGuardPolicies(
    entries,
    ROUTE_GUARD_POLICIES
  );

  const nextContent = buildGuardMapMarkdown({
    entries,
    groups,
    policyViolations,
  });
  const writeResult = writeIfChanged({
    outputPath: OUTPUT_PATH,
    content: nextContent,
    rootDir: REPO_ROOT,
  });
  if (writeResult.changed) {
    console.log(`Wrote guard map: ${writeResult.relativePath}`);
  } else {
    console.log(`Guard map unchanged: ${writeResult.relativePath}`);
  }

  if (
    strict &&
    (
      groups.unexpectedReview.length > 0 ||
      groups.missingMethodExports.length > 0 ||
      policyViolations.length > 0
    )
  ) {
    if (groups.missingMethodExports.length > 0) {
      console.error(
        `[guard-map] routes missing method exports detected: ${groups.missingMethodExports.length}`
      );
    }
    if (groups.unexpectedReview.length > 0) {
      console.error(
        `[guard-map] unexpected review routes detected: ${groups.unexpectedReview.length}`
      );
    }
    if (policyViolations.length > 0) {
      console.error(
        `[guard-map] route guard policy violations detected: ${policyViolations.length}`
      );
    }
    process.exitCode = 1;
  }
}

main();
