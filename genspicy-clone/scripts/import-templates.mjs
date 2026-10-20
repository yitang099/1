/**
 * Downloads the public Genspicy template catalog into server/data/templates.catalog.json
 * Run: node scripts/import-templates.mjs
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const outPath = path.join(__dirname, '../server/data/templates.catalog.json')
const API = 'https://api.genspicy.ai/api/v1/generation-template.list'
const PAGE_SIZE = 100

function slugify(name, id) {
  const base = String(name || 'template')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 80)
  return `${base}-${id.slice(0, 8)}`
}

async function fetchPage(page) {
  const url = `${API}?page=${page}&page_size=${PAGE_SIZE}`
  const res = await fetch(url)
  if (!res.ok) throw new Error(`HTTP ${res.status} page ${page}`)
  const json = await res.json()
  if (json.code !== 0) throw new Error(json.message || `code ${json.code}`)
  return json.data
}

async function main() {
  const first = await fetchPage(1)
  const total = first.total
  const items = [...first.items]
  const pages = Math.ceil(total / PAGE_SIZE)
  console.log(`Total ${total}, pages ${pages}`)

  for (let p = 2; p <= pages; p++) {
    const data = await fetchPage(p)
    items.push(...data.items)
    if (p % 10 === 0) console.log(`Fetched page ${p}/${pages} (${items.length} items)`)
  }

  const enriched = items.map((t) => ({
    ...t,
    slug: t.slug || slugify(t.template_name, t.id),
  }))

  fs.mkdirSync(path.dirname(outPath), { recursive: true })
  fs.writeFileSync(outPath, JSON.stringify({ total: enriched.length, imported_at: new Date().toISOString(), items: enriched }))
  console.log(`Wrote ${enriched.length} templates to ${outPath}`)
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
