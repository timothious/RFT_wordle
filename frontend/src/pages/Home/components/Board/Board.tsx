import type { GuessRow } from '../../../../api'
import { Tile } from '../Tile'
import './Board.css'

interface BoardProps {
  board: GuessRow[]
  draft: string
  maxGuesses: number
  wordLength: number
  finished: boolean
}

export function Board({ board, draft, maxGuesses, wordLength, finished }: BoardProps) {
  const rows = Array.from({ length: maxGuesses }, (_, rowIndex) => {
    const played = board[rowIndex]
    if (played) {
      return played.guess.split('').map((letter, i) => (
        <Tile key={`${rowIndex}-${i}`} letter={letter} state={played.feedback[i] ?? 'gray'} />
      ))
    }

    const isActive = rowIndex === board.length && !finished
    const letters = isActive ? draft : ''

    return Array.from({ length: wordLength }, (_, i) => {
      const letter = letters[i] ?? ''
      return (
        <Tile
          key={`${rowIndex}-${i}`}
          letter={letter}
          state={letter ? 'filled' : 'empty'}
        />
      )
    })
  })

  return (
    <div className="board" role="grid" aria-label="Wordle board">
      {rows.map((cells, rowIndex) => (
        <div className="board__row" role="row" key={rowIndex}>
          {cells}
        </div>
      ))}
    </div>
  )
}
