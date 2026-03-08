import "dotenv/config";
import pg from "pg";

const url = process.env.WELLNESSBOX_PRISMA_URL;
if (!url) {
  console.error("WELLNESSBOX_PRISMA_URL is not set. Check your .env file.");
  process.exit(1);
}

const client = new pg.Client({
  connectionString: url,
  ssl: { rejectUnauthorized: false },
});

async function main() {
  await client.connect();
  const res = await client.query(`
    SELECT id,
        text,
        metadata,
        LEFT(embedding::text, 60) || '...' AS embedding
    FROM rag_chunks
    ORDER BY id
    LIMIT 50;
  `);
  console.log(JSON.stringify(res.rows, null, 2));
  await client.end();
}

main().catch((err) => {
  console.error("Error dumping rag_chunks:", err);
  process.exit(1);
});
