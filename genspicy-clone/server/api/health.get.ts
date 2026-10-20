import { catalogSize, catalogSource } from '../utils/catalog'
import { findProjectRoot } from '../utils/paths'

export default defineEventHandler(() => {
  return {
    ok: true,
    project_root: findProjectRoot(),
    catalog_source: catalogSource(),
    template_count: catalogSize(),
    generation_mode: 'mock (connect live token at /user/live-account for official API)',
    payment_enabled: false,
  }
})
