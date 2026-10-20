import { catalogSize, catalogSource } from '../utils/catalog'
import { ffmpegBundled, resolveFfmpegBin } from '../utils/ffmpeg-bin'
import { findProjectRoot } from '../utils/paths'

export default defineEventHandler(() => {
  return {
    ok: true,
    project_root: findProjectRoot(),
    catalog_source: catalogSource(),
    template_count: catalogSize(),
    generation_mode: 'mock (connect live token at /user/live-account for official API)',
    payment_enabled: false,
    ffmpeg: resolveFfmpegBin(),
    ffmpeg_bundled: ffmpegBundled(),
    local_url: 'http://127.0.0.1:3000/',
    windows_start: '双击 genspicy-clone/start-windows.bat 或 pnpm local',
  }
})
