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