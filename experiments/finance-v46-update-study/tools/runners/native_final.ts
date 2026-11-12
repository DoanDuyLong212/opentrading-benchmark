/** Preserve the current native loop's authoritative completed-turn text.
 * Stop-gate recovery can discard streamed promise fragments without another
 * tool-start. Read only the final message: no JSON extraction, earlier-message
 * fallback, or file/tool-input answer recovery occurs here.
 */
export function completedFinalText(event: any): string | undefined {
  if (event?.type !== 'done' || event.outcome !== 'completed') return undefined
  const last = Array.isArray(event.messages) ? event.messages.at(-1) : undefined
  if (last?.role !== 'assistant') return ''
  if (typeof last.content === 'string') return last.content
  if (!Array.isArray(last.content)) return ''
  return last.content.filter((part: any) => part?.type === 'text' && typeof part.text === 'string')
    .map((part: any) => part.text).join('')
}
