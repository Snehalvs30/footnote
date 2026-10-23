/**
 * Removes Markdown formatting symbols from a passage, so source excerpts read as
 * clean text: "# Handbook ## Paid time off" becomes "Handbook Paid time off".
 * Only for display; the stored text (and what the LLM sees) is unchanged.
 */
export function stripMarkdown(text: string): string {
  return text
    .replace(/(^|\s)#{1,6}\s+/g, '$1') // headings: # Title, ## Section
    .replace(/(\*\*|__)(.+?)\1/g, '$2') // bold: **text**, __text__
    .replace(/`([^`]+)`/g, '$1') // inline code: `text`
    .replace(/^\s*[-*+]\s+/gm, '') // list bullets at the start of a line
    .replace(/\s{2,}/g, ' ') // spaces left behind
    .trim()
}

/**
 * Splits text into sentences. Splits only at . ! or ? followed by a space and a
 * capital letter or digit, so "1.67 days" and "a.m." aren't split.
 */
export function splitSentences(text: string): string[] {
  return text
    .split(/(?<=[.!?])\s+(?=[A-Z0-9"(])/)
    .map((sentence) => sentence.trim())
    .filter(Boolean)
}

// Common words that say nothing about which sentence was cited.
const STOP_WORDS = new Set(
  'the and for that with from this are was were has have had your their they them what which when will would about into than then only each per any not but can may must also its our you all'.split(
    ' ',
  ),
)

function keywords(text: string): string[] {
  return (text.toLowerCase().match(/[a-z0-9$][a-z0-9$.,%-]*/g) ?? [])
    .map((word) => word.replace(/[.,]+$/, ''))
    .filter((word) => word.length > 2 && !STOP_WORDS.has(word))
}

/**
 * Which sentences of a source passage most likely support the answer's claims
 * citing it. Compares keywords from the answer sentences that cite this source
 * (those containing "[n]") with each passage sentence, and keeps the best matches.
 *
 * A heuristic, run in the browser: good at pointing to the right sentence, but
 * not guaranteed. Returns no sentences when nothing matches clearly.
 */
export function citedSentences(answer: string, sourceNumber: number, sentences: string[]): Set<number> {
  const claims = splitSentences(answer).filter((sentence) => sentence.includes(`[${sourceNumber}]`))
  const target = new Set(keywords(claims.length > 0 ? claims.join(' ') : answer))

  const scores = sentences.map((sentence) => new Set(keywords(sentence).filter((word) => target.has(word))).size)
  const best = Math.max(0, ...scores)
  if (best < 2) return new Set()

  const threshold = Math.max(2, best * 0.6)
  return new Set(scores.flatMap((score, index) => (score >= threshold ? [index] : [])))
}