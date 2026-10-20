import { refreshTemplatesFromCatalog } from '../utils/store'

export default defineNitroPlugin(() => {
  refreshTemplatesFromCatalog()
})
