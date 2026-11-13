import type { GameStatus } from '../../../../api'
import './StatusBanner.css'

interface StatusBannerProps {
  status?: GameStatus
  remainingGuesses?: number
  error?: string | null
}

export function StatusBanner({ status, remainingGuesses, error }: StatusBannerProps) {
  let message = 'Start a new game to play.'
  if (status === 'in_progress' && remainingGuesses != null) {
    message = `${remainingGuesses} guess${remainingGuesses === 1 ? '' : 'es'} left`
  } else if (status === 'won') {
    message = 'You solved it.'
  } else if (status === 'lost') {
    message = 'Out of guesses.'
  }

  return (
    <div className="status-banner" role="status">
      <p className="status-banner__message">{message}</p>
      {error ? <p className="status-banner__error">{error}</p> : null}
    </div>
  )
}
