import type { GamePublicView, SuggestPolicy, SuggestResponse } from './types'

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8001').replace(
  /\/$/,
  '',
)

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        ...(init?.headers ?? {}),
      },
      ...init,
    })
  } catch {
    throw new Error(`Cannot reach API at ${API_BASE}. Is Docker running on port 8001?`)
  }

  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const body = (await response.json()) as {
        code?: string
        message?: string
        detail?: string | { message?: string; code?: string }
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
  baseUrl: API_BASE,

  health: () => request<{ status: string }>('/health'),

  createGame: () =>
    request<GamePublicView>('/games', {
      method: 'POST',
      body: JSON.stringify({}),
    }),

  getGame: (gameId: string) => request<GamePublicView>(`/games/${gameId}`),

  submitGuess: (gameId: string, guess: string) =>
    request<GamePublicView>(`/games/${gameId}/guesses`, {
      method: 'POST',
      body: JSON.stringify({ guess: guess.toLowerCase() }),
    }),

  suggest: (gameId: string, policy: SuggestPolicy, apply = false) =>
    request<SuggestResponse>(`/games/${gameId}/suggest`, {
      method: 'POST',
      body: JSON.stringify({ policy, apply }),
    }),
}
