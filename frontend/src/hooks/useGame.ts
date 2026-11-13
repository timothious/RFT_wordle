import { useCallback, useEffect, useState } from 'react'
import { api, type GamePublicView, type SuggestPolicy } from '../api'

const STORAGE_KEY = 'rft-wordle-game-id'
const MAX_GUESSES = 6
const WORD_LENGTH = 5

export function useGame() {
  const [game, setGame] = useState<GamePublicView | null>(null)
  const [draft, setDraft] = useState('')
  const [suggestion, setSuggestion] = useState<string | null>(null)
  const [policy, setPolicy] = useState<SuggestPolicy>('solver')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const finished = game?.status === 'won' || game?.status === 'lost'

  const newGame = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    setSuggestion(null)
    setDraft('')
    try {
      const next = await api.createGame()
      setGame(next)
      sessionStorage.setItem(STORAGE_KEY, next.game_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start game')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    const existingId = sessionStorage.getItem(STORAGE_KEY)
    if (!existingId) return

    let cancelled = false
    ;(async () => {
      setIsLoading(true)
      try {
        const existing = await api.getGame(existingId)
        if (!cancelled) setGame(existing)
      } catch {
        sessionStorage.removeItem(STORAGE_KEY)
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [])

  const typeLetter = useCallback(
    (letter: string) => {
      if (finished || isLoading) return
      const normalized = letter.toLowerCase()
      if (!/^[a-z]$/.test(normalized)) return
      setDraft((prev) => (prev.length < WORD_LENGTH ? `${prev}${normalized}` : prev))
      setError(null)
    },
    [finished, isLoading],
  )

  const backspace = useCallback(() => {
    if (finished || isLoading) return
    setDraft((prev) => prev.slice(0, -1))
  }, [finished, isLoading])

  const submitGuess = useCallback(async () => {
    if (!game || finished || isLoading) return
    if (draft.length !== WORD_LENGTH) {
      setError('Enter a 5-letter word')
      return
    }

    setIsLoading(true)
    setError(null)
    try {
      const next = await api.submitGuess(game.game_id, draft)
      setGame(next)
      setDraft('')
      setSuggestion(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Guess failed')
    } finally {
      setIsLoading(false)
    }
  }, [draft, finished, game, isLoading])

  const requestSuggest = useCallback(async () => {
    if (!game || finished || isLoading) return
    setIsLoading(true)
    setError(null)
    try {
      const result = await api.suggest(game.game_id, policy, false)
      if (!result.raw_ok || !result.guess) {
        setSuggestion(null)
        setError(result.error ?? 'AI returned an invalid guess')
        return
      }
      setSuggestion(result.guess)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Suggestion failed')
    } finally {
      setIsLoading(false)
    }
  }, [finished, game, isLoading, policy])

  const applySuggestion = useCallback(async () => {
    if (!suggestion) return
    setDraft(suggestion.slice(0, WORD_LENGTH))
    setSuggestion(null)
  }, [suggestion])

  return {
    game,
    draft,
    suggestion,
    policy,
    setPolicy,
    isLoading,
    error,
    finished,
    maxGuesses: MAX_GUESSES,
    wordLength: WORD_LENGTH,
    newGame,
    typeLetter,
    backspace,
    submitGuess,
    requestSuggest,
    applySuggestion,
  }
}
