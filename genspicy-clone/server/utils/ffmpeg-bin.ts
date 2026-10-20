import { existsSync } from 'node:fs'
import { createRequire } from 'node:module'
import { join } from 'node:path'
import { findProjectRoot } from './paths'

let cached: string | null | undefined

/** Prefer bundled ffmpeg-static; fall back to PATH `ffmpeg`. */
export function resolveFfmpegBin(): string {
  if (cached !== undefined) return cached || 'ffmpeg'

  const root = findProjectRoot()
  const req = createRequire(join(root, 'package.json'))

  try {
    const bundled = req('ffmpeg-static') as string | null
    if (bundled && existsSync(bundled)) {
      cached = bundled
      return bundled
    }
  } catch {
    /* optional */
  }

  const win = join(root, 'node_modules/ffmpeg-static/ffmpeg.exe')
  const nix = join(root, 'node_modules/ffmpeg-static/ffmpeg')
  if (existsSync(win)) {
    cached = win
    return win
  }
  if (existsSync(nix)) {
    cached = nix
    return nix
  }

  cached = 'ffmpeg'
  return 'ffmpeg'
}

export function ffmpegBundled(): boolean {
  const b = resolveFfmpegBin()
  return b !== 'ffmpeg' && existsSync(b)
}
