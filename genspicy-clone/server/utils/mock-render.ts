import { execFile } from 'node:child_process'
import { promisify } from 'node:util'
import { mkdirSync, writeFileSync, existsSync, unlinkSync } from 'node:fs'
import { join } from 'node:path'
import { dataDir } from './paths'
import { MOCK_OUTPUT_URL } from './mock-output'

const execFileAsync = promisify(execFile)

async function downloadToTemp(url: string): Promise<string> {
  const res = await fetch(url, { redirect: 'follow' })
  if (!res.ok) throw new Error(`download failed ${res.status}`)
  const buf = Buffer.from(await res.arrayBuffer())
  if (buf.length > 12 * 1024 * 1024) throw new Error('image too large')
  const tmp = join(dataDir(), 'tmp', `${crypto.randomUUID()}.img`)
  mkdirSync(join(dataDir(), 'tmp'), { recursive: true })
  writeFileSync(tmp, buf)
  return tmp
}

async function resolveLocalInputPath(
  inputUrl: string,
  siteOrigin: string,
): Promise<{ path: string; removeAfter: string | null }> {
  const u = inputUrl.trim()
  if (u.startsWith('/media/uploads/')) {
    const name = u.replace('/media/uploads/', '')
    const path = join(dataDir(), 'uploads', name)
    if (!existsSync(path)) throw new Error('upload not found')
    return { path, removeAfter: null }
  }
  if (u.startsWith('http://') || u.startsWith('https://')) {
    const path = await downloadToTemp(u)
    return { path, removeAfter: path }
  }
  if (u.startsWith('/')) {
    const path = await downloadToTemp(`${siteOrigin.replace(/\/$/, '')}${u}`)
    return { path, removeAfter: path }
  }
  throw new Error('unsupported input url')
}

/** Build a short MP4 from the user's image (Ken Burns) — not real face swap, but output matches input. */
export async function renderMockVideoFromInput(inputUrl: string, jobId: string, durationSec: number) {
  const siteOrigin = process.env.NUXT_PUBLIC_SITE_URL || 'http://127.0.0.1:3000'
  let local = ''
  let removeAfter: string | null = null
  try {
    const resolved = await resolveLocalInputPath(inputUrl, siteOrigin)
    local = resolved.path
    removeAfter = resolved.removeAfter
    const outDir = join(dataDir(), 'outputs')
    mkdirSync(outDir, { recursive: true })
    const outName = `${jobId}.mp4`
    const outPath = join(outDir, outName)
    const t = Math.max(5, Math.min(60, durationSec))
    // 480x864 portrait, subtle zoom
    const vf = `scale=480:864:force_original_aspect_ratio=decrease,pad=480:864:(ow-iw)/2:(oh-ih)/2:black,zoompan=z='min(zoom+0.001,1.08)':d=${t * 25}:s=480x864:fps=25`
    await execFileAsync(
      'ffmpeg',
      ['-y', '-loop', '1', '-i', local, '-t', String(t), '-vf', vf, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', outPath],
      { timeout: 120_000 },
    )
    return `/media/outputs/${outName}`
  } catch (e) {
    console.warn('[mock-render] fallback to sample webm', e)
    return MOCK_OUTPUT_URL
  } finally {
    if (removeAfter && existsSync(removeAfter)) {
      try {
        unlinkSync(removeAfter)
      } catch {
        /* ignore */
      }
    }
  }
}
