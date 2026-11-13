import type { FeedbackColor, GuessRow } from '../../../../api'
import './Keyboard.css'

const ROWS = ['qwertyuiop', 'asdfghjkl', 'zxcvbnm']

type KeyState = FeedbackColor | 'unused'

const RANK: Record<KeyState, number> = {
  unused: 0,
  gray: 1,
  yellow: 2,
  green: 3,
}

function deriveKeyStates(board: GuessRow[]): Record<string, KeyState> {
  const states: Record<string, KeyState> = {}
  for (const row of board) {
    row.guess.split('').forEach((letter, i) => {
      const next = row.feedback[i] ?? 'gray'
      const prev = states[letter] ?? 'unused'
      if (RANK[next] > RANK[prev]) states[letter] = next
    })
  }
  return states
}

interface KeyboardProps {
  board: GuessRow[]
  disabled?: boolean
  onLetter: (letter: string) => void
  onBackspace: () => void
  onEnter: () => void
}

export function Keyboard({ board, disabled, onLetter, onBackspace, onEnter }: KeyboardProps) {
  const states = deriveKeyStates(board)

  return (
    <div className="keyboard" aria-label="On-screen keyboard">
      {ROWS.map((row, rowIndex) => (
        <div className="keyboard__row" key={row}>
          {rowIndex === 2 && (
            <button type="button" className="key key--action" disabled={disabled} onClick={onEnter}>
              Enter
            </button>
          )}
          {row.split('').map((letter) => {
            const state = states[letter] ?? 'unused'
            return (
              <button
                key={letter}
                type="button"
                className={`key key--${state}`}
                disabled={disabled}
                onClick={() => onLetter(letter)}
              >
                {letter}
              </button>
            )
          })}
          {rowIndex === 2 && (
            <button
              type="button"
              className="key key--action"
              disabled={disabled}
              onClick={onBackspace}
            >
              ⌫
            </button>
          )}
        </div>
      ))}
    </div>
  )
}
