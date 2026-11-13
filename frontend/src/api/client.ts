import type { GamePublicView, SuggestPolicy, SuggestResponse } from './types'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8001'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const body = (await response.json()) as {
        message?: string
        detail?: string | { message?: string }
      }
      if (typeof body.message === 'string') message = body.message
      else if (typeof body.detail === 'string') message = body.detail
      else if (body.detail && typeof body.detail.message === 'string') {
        message = body.detail.message
      }
    } catch {
      /* ignore non-JSON errors */
    }
    throw new Error(message)
  }

  return response.json() as Promise<T>
}

export const api = {
  createGame: () =>
    request<GamePublicView>('/games', {
      method: 'POST',
      body: JSON.stringify({}),
    }),

  getGame: (gameId: string) => request<GamePublicView>(`/games/${gameId}`),

  submitGuess: (gameId: string, guess: string) =>
    request<GamePublicView>(`/games/${gameId}/guesses`, {
      method: 'POST',
      body: JSON.stringify({ guess }),
    }),

  suggest: (gameId: string, policy: SuggestPolicy, apply = false) =>
    request<SuggestResponse>(`/games/${gameId}/suggest`, {
      method: 'POST',
      body: JSON.stringify({ policy, apply }),
    }),
}
