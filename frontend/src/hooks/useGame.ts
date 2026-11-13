import { useCallback, useEffect, useRef, useState } from 'react'
import { api, type GamePublicView, type SuggestPolicy } from '../api'

const STORAGE_KEY = 'rft-wordle-game-id'
const MAX_GUESSES = 6
const WORD_LENGTH = 5

function isInvalidWordError(message: string): boolean {
  const lower = message.toLowerCase()
  return (
    lower.includes('not in word list') ||
    lower.includes('dictionary') ||
    lower.includes('already used') ||
    lower.includes('invalid guess') ||
    lower.includes('5-letter')
  )
}

export function useGame() {
  const [game, setGame] = useState<GamePublicView | null>(null)
  const [draft, setDraft] = useState('')
  const [suggestion, setSuggestion] = useState<string | null>(null)
  const [policy, setPolicy] = useState<SuggestPolicy>('solver')
  const [isBooting, setIsBooting] = useState(true)
  const [isBusy, setIsBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [shakeToken, setShakeToken] = useState(0)
  const busyRef = useRef(false)

  const finished = game?.status === 'won' || game?.status === 'lost'
  const canType = Boolean(game) && !finished && !isBooting

  const triggerShake = useCallback(() => {
    setShakeToken((value) => value + 1)
  }, [])

  const newGame = useCallback(async () => {
    if (busyRef.current) return
    busyRef.current = true
    setIsBusy(true)
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
      busyRef.current = false
      setIsBusy(false)
      setIsBooting(false)
    }
  }, [])

  useEffect(() => {
    let cancelled = false

    ;(async () => {
      setIsBooting(true)
      const existingId = sessionStorage.getItem(STORAGE_KEY)
      try {
        if (existingId) {
          const existing = await api.getGame(existingId)
          if (!cancelled) {
            setGame(existing)
            setDraft('')
            setSuggestion(null)
            setError(null)
          }
          return
        }
        const next = await api.createGame()
        if (!cancelled) {
          setGame(next)
          setDraft('')
          sessionStorage.setItem(STORAGE_KEY, next.game_id)
          setError(null)
        }
      } catch (err) {
        sessionStorage.removeItem(STORAGE_KEY)
        if (!cancelled) {
          setGame(null)
          setError(err instanceof Error ? err.message : 'Cannot reach API')
        }
      } finally {
        if (!cancelled) setIsBooting(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [])

  const typeLetter = useCallback(
    (letter: string) => {
      if (!canType) return
      const normalized = letter.toLowerCase()
      if (!/^[a-z]$/.test(normalized)) return
      setSuggestion(null)
      setDraft((prev) => (prev.length < WORD_LENGTH ? `${prev}${normalized}` : prev))
    },
    [canType],
  )

  const backspace = useCallback(() => {
    if (!canType) return
    setSuggestion(null)
    setDraft((prev) => prev.slice(0, -1))
  }, [canType])

  const submitGuess = useCallback(async () => {
    if (!game || finished || isBooting || busyRef.current) return
    if (draft.length !== WORD_LENGTH) {
      triggerShake()
      return
    }

    busyRef.current = true
    setIsBusy(true)
    setError(null)
    const guess = draft
    try {
      const next = await api.submitGuess(game.game_id, guess)
      setGame(next)
      setDraft('')
      setSuggestion(null)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Guess failed'
      setError(message)
      if (isInvalidWordError(message)) triggerShake()
    } finally {
      busyRef.current = false
      setIsBusy(false)
    }
  }, [draft, finished, game, isBooting, triggerShake])

  const requestSuggest = useCallback(async () => {
    if (!game || finished || isBooting || busyRef.current) return
    busyRef.current = true
    setIsBusy(true)
    setError(null)
    try {
      const result = await api.suggest(game.game_id, policy, false)
      if (!result.raw_ok || !result.guess) {
        setSuggestion(null)
        triggerShake()
        return
      }
      const guess = result.guess.toLowerCase().slice(0, WORD_LENGTH)
      setSuggestion(guess)
      setDraft(guess)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Suggestion failed')
    } finally {
      busyRef.current = false
      setIsBusy(false)
    }
  }, [finished, game, isBooting, policy, triggerShake])

  const applySuggestion = useCallback(async () => {
    if (!game || !suggestion || finished || isBooting || busyRef.current) return

    busyRef.current = true
    setIsBusy(true)
    setError(null)
    try {
      const next = await api.submitGuess(game.game_id, suggestion)
      setGame(next)
      setDraft('')
      setSuggestion(null)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Could not apply suggestion'
      setError(message)
      if (isInvalidWordError(message)) triggerShake()
    } finally {
      busyRef.current = false
      setIsBusy(false)
    }
  }, [finished, game, isBooting, suggestion, triggerShake])

  return {
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
