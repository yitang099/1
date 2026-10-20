/** Same-origin demo video so playback works in CN / via tunnel (no cdn.genspicy.ai). */
export const MOCK_OUTPUT_URL = '/demo/sample.webm'

export function mockOutputForTemplate(_templateId: string) {
  return MOCK_OUTPUT_URL
}
