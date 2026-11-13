import type { GameStatus } from '../../../../api'
import './StatusBanner.css'

interface StatusBannerProps {
  status?: GameStatus
  remainingGuesses?: number
  error?: string | null
  loading?: boolean
}

export function StatusBanner({
  status,
  remainingGuesses,
  error,
  loading,
}: StatusBannerProps) {
  let message = 'Connecting to API…'
  if (!loading && !status) {
    message = 'No active game. Click New Game.'
  } else if (loading && !status) {
    message = 'Connecting to API…'
  } else if (status === 'in_progress' && remainingGuesses != null) {
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
