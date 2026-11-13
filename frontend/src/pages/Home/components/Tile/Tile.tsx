import type { FeedbackColor } from '../../../../api'
import './Tile.css'

type TileState = FeedbackColor | 'empty' | 'filled'

interface TileProps {
  letter?: string
  state?: TileState
}

const stateClass: Record<TileState, string> = {
  empty: 'tile--empty',
  filled: 'tile--filled',
  green: 'tile--correct',
  yellow: 'tile--present',
  gray: 'tile--absent',
}

const stateLabel: Record<TileState, string> = {
  empty: 'empty',
  filled: 'typed',
  green: 'correct position',
  yellow: 'wrong position',
  gray: 'not in word',
}

export function Tile({ letter = '', state = 'empty' }: TileProps) {
  return (
    <div
      className={`tile ${stateClass[state]}`}
      data-state={state}
      aria-label={letter ? `${letter}, ${stateLabel[state]}` : 'empty'}
    >
      {letter}
    </div>
  )
}
