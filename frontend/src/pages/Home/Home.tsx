import { useEffect } from 'react'
import { BrandHeader } from '../../components'
import { useGame } from '../../hooks'
import {
  Board,
  Keyboard,
  NewGameButton,
  StatusBanner,
  SuggestPanel,
} from './components'
import './Home.css'

export function Home() {
  const {
    game,
    draft,
    suggestion,
    policy,
    setPolicy,
    isBooting,
    isBusy,
    error,
    shakeToken,
    finished,
    canType,
    maxGuesses,
    wordLength,
    newGame,
    typeLetter,
    backspace,
    submitGuess,
    requestSuggest,
    applySuggestion,
  } = useGame()

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.metaKey || event.ctrlKey || event.altKey) return
      if (event.key === 'Enter') {
        event.preventDefault()
        void submitGuess()
        return
      }
      if (event.key === 'Backspace') {
        event.preventDefault()
        backspace()
        return
      }
      if (/^[a-zA-Z]$/.test(event.key)) {
        event.preventDefault()
        typeLetter(event.key)
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [backspace, submitGuess, typeLetter])

  const board = game?.board ?? []

  return (
    <main className="home">
      <BrandHeader />

      <div className="home__toolbar">
        <NewGameButton disabled={isBusy || isBooting} onClick={() => void newGame()} />
      </div>

      <StatusBanner
        status={game?.status}
        remainingGuesses={game?.remaining_guesses}
        error={error}
        loading={isBooting}
      />

      <ul className="home__legend" aria-label="Color meaning">
        <li>
          <span className="home__legend-swatch home__legend-swatch--green" />
          Right letter, right spot
        </li>
        <li>
          <span className="home__legend-swatch home__legend-swatch--yellow" />
          Right letter, wrong spot
        </li>
        <li>
          <span className="home__legend-swatch home__legend-swatch--gray" />
          Not in the word
        </li>
      </ul>

      <Board
        board={board}
        draft={draft}
        maxGuesses={maxGuesses}
        wordLength={wordLength}
        finished={Boolean(finished)}
        shakeToken={shakeToken}
      />

      <SuggestPanel
        policy={policy}
        suggestion={suggestion}
        disabled={!canType || isBusy}
        onPolicyChange={setPolicy}
        onAsk={() => void requestSuggest()}
        onApply={() => void applySuggestion()}
      />

      <Keyboard
        board={board}
        disabled={!canType}
        onLetter={typeLetter}
        onBackspace={backspace}
        onEnter={() => void submitGuess()}
      />
    </main>
  )
}
