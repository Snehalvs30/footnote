interface Props {
  text: string
  sourceCount: number
  /** The footnote currently open in the source panel, if it belongs to this answer. */
  activeNumber: number | null
  onCite: (sourceNumber: number) => void
}

/**
 * Renders answer text, turning citations like [2] into superscript footnote
 * markers you can click. A number with no matching source is shown struck
 * through: the model cited something it wasn't given.
 */
export function AnswerText({ text, sourceCount, activeNumber, onCite }: Props) {
  // split() with a capture group keeps the matches: "a [1] b" -> ["a ", "[1]", " b"]
  const parts = text.split(/(\[\d+\])/g)

  return (
    <p className="answer-text">
      {parts.map((part, index) => {
        const match = part.match(/^\[(\d+)\]$/)
        if (!match) return <span key={index}>{part}</span>

        const number = Number(match[1])
        if (number < 1 || number > sourceCount) {
          return (
            <sup key={index} className="cite cite--invalid" title="Cites a source that wasn't provided">
              {number}
            </sup>
          )
        }
        return (
          <sup key={index}>
            <button
              type="button"
              className="cite"
              aria-pressed={number === activeNumber}
              onClick={() => onCite(number)}
              aria-label={`Show source ${number}`}
            >
              {number}
            </button>
          </sup>
        )
      })}
    </p>
  )
}
