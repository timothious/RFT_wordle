import './NewGameButton.css'

interface NewGameButtonProps {
  disabled?: boolean
  onClick: () => void
}

export function NewGameButton({ disabled, onClick }: NewGameButtonProps) {
  return (
    <button type="button" className="new-game-button" disabled={disabled} onClick={onClick}>
      New Game
    </button>
  )
}
