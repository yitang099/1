export function ok<T>(data: T) {
  return { code: 0, message: 'ok', data }
}

export function err(code: number, message: string) {
  return { code, message, data: null }
}

export function readAuth(event: { headers: Headers }) {
  return event.headers.get('authorization') || event.headers.get('Authorization') || undefined
}
