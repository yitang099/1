import seedTemplates from '../data/templates.seed.json'
import { readFileSync, existsSync } from 'node:fs'
import { join } from 'node:path'

export type CatalogTemplate = {
  id: string
  slug: string
  template_name: string
  template_type: string
  tags: string[]
  card_tags?: string[]
  status: string
  sort_weight?: number
  generate_mode: string
  output_type?: string
  cover_url: string
  output_media: string
  duration: number
  base_cost: number
  extend_cost: number
  features: {
    name: string
    prompt?: string
    enabled: boolean
    require_vip_levels?: number[]
    extra_cost: number
  }[]
  display_scene?: string
  vip_only?: boolean
  enable_sound?: boolean
  input_medias?: { type: string; url: string }[]
  workflow_type?: string
}

let cache: CatalogTemplate[] | null = null

function slugify(name: string, id: string) {
  const base = name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 80)
  return `${base}-${id.slice(0, 8)}`
}

function normalize(raw: Record<string, unknown>): CatalogTemplate {
  const id = String(raw.id)
  const name = String(raw.template_name || 'Template')
  return {
    id,
    slug: String(raw.slug || slugify(name, id)),
    template_name: name,
    template_type: String(raw.template_type || ''),
    tags: Array.isArray(raw.tags) ? (raw.tags as string[]) : [],
    card_tags: Array.isArray(raw.card_tags) ? (raw.card_tags as string[]) : [],
    status: String(raw.status || 'published'),
    sort_weight: Number(raw.sort_weight || 0),
    generate_mode: String(raw.generate_mode || 'image_to_video'),
    output_type: String(raw.output_type || 'video'),
    cover_url: String(raw.cover_url || ''),
    output_media: String(raw.output_media || ''),
    duration: Number(raw.duration || 8),
    base_cost: Number(raw.base_cost || 30),
    extend_cost: Number(raw.extend_cost || 15),
    features: Array.isArray(raw.features) ? (raw.features as CatalogTemplate['features']) : [],
    display_scene: raw.display_scene ? String(raw.display_scene) : undefined,
    vip_only: Boolean(raw.vip_only),
    enable_sound: Boolean(raw.enable_sound),
    input_medias: raw.input_medias as CatalogTemplate['input_medias'],
    workflow_type: raw.workflow_type ? String(raw.workflow_type) : undefined,
  }
}

export function getCatalog(): CatalogTemplate[] {
  if (cache) return cache
  const catalogPath = join(process.cwd(), 'server/data/templates.catalog.json')
  if (existsSync(catalogPath)) {
    const parsed = JSON.parse(readFileSync(catalogPath, 'utf8')) as { items: Record<string, unknown>[] }
    cache = parsed.items.map((t) => normalize(t))
    return cache
  }
  cache = seedTemplates.map((t) =>
    normalize({ ...t, status: 'published' } as Record<string, unknown>),
  )
  return cache
}

export function catalogSize() {
  return getCatalog().length
}
