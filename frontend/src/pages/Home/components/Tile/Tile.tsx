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

export function Tile({ letter = '', state = 'empty' }: TileProps) {
  return (
    <div className={`tile ${stateClass[state]}`} aria-label={letter ? `${letter} ${state}` : 'empty'}>
      {letter}
    </div>
  )
}
