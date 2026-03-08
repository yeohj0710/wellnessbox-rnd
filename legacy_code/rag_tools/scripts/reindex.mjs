import "dotenv/config";

const res = await fetch("http://localhost:3000/api/rag/reindex", {
  method: "POST",
});
if (!res.ok) {
  console.error("reindex API error:", res.status, await res.text());
  process.exit(1);
}
const data = await res.json();
console.log(JSON.stringify(data, null, 2));

const hasAny =
  Array.isArray(data.results) && data.results.some((r) => r.chunks > 0);
if (!hasAny) {
  console.error(
    "reindex 결과에 chunks>0 문서가 없습니다. reindexAll이 실행되지 않았을 가능성이 있습니다."
  );
  process.exit(2);
}
