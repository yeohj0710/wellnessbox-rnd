import "dotenv/config";

const q = process.argv[2] || "건강기능식품과 식품 차이";

const debugUrl = `http://localhost:3000/api/rag/debug?q=${encodeURIComponent(q)}`;
const dres = await fetch(debugUrl);
if (!dres.ok) {
  console.error("debug API error:", dres.status, await dres.text());
  process.exit(1);
}
const ddata = await dres.json();
const keyword = ddata.out?.[0]?.snippet?.split(/\s+/)[0] || "";

const chatRes = await fetch("http://localhost:3000/api/chat", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ messages: [{ role: "user", content: q }] }),
});
if (!chatRes.ok) {
  console.error("chat API error:", chatRes.status, await chatRes.text());
  process.exit(1);
}
const text = await chatRes.text();
console.log(text);
if (keyword && !text.includes(keyword)) {
  console.error("keyword not found in response:", keyword);
  process.exit(1);
}
