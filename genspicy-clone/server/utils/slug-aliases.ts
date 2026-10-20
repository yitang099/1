/** Legacy / marketing slugs → canonical catalog slug */
export const SLUG_ALIASES: Record<string, string> = {
  'hyper-realistic-face-swap': 'hyper-realistic-face-swap-cum-288b5fa3',
  'face-swap': 'hyper-realistic-face-swap-cum-288b5fa3',
}

export function resolveSlug(input: string) {
  const key = input.trim().toLowerCase()
  return SLUG_ALIASES[key] || input
}
