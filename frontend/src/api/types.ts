export type FeedbackColor = 'green' | 'yellow' | 'gray'

export type GameStatus = 'in_progress' | 'won' | 'lost'

export type SuggestPolicy = 'solver' | 'base' | 'rft'

export interface GuessRow {
  guess: string
  feedback: FeedbackColor[]
}

export interface GamePublicView {
  game_id: string
  status: GameStatus
  remaining_guesses: number
  board: GuessRow[]
}

export interface SuggestResponse {
  policy: SuggestPolicy
  guess: string | null
  raw_ok: boolean
  error: string | null
  applied: boolean
  board?: GamePublicView
}

export interface ApiErrorBody {
  code: string
  message: string
}
