import "dotenv/config";

const q = process.argv[2] || "건강기능식품과 식품 차이";

const url = `http://localhost:3000/api/rag/debug?q=${encodeURIComponent(q)}`;

const res = await fetch(url);
if (!res.ok) {
  console.error("API error:", res.status, await res.text());
  process.exit(1);
}

const data = await res.json();

for (const d of data.out) {
  console.log(`[${d.rank}] (${d.score?.toFixed(3)}) ${d.snippet}\n`);
}
