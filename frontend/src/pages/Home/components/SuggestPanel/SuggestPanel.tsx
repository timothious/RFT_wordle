import type { SuggestPolicy } from '../../../../api'
import './SuggestPanel.css'

interface SuggestPanelProps {
  policy: SuggestPolicy
  suggestion: string | null
  disabled?: boolean
  onPolicyChange: (policy: SuggestPolicy) => void
  onAsk: () => void
  onApply: () => void
}

const POLICIES: SuggestPolicy[] = ['solver', 'base', 'rft']

export function SuggestPanel({
  policy,
  suggestion,
  disabled,
  onPolicyChange,
  onAsk,
  onApply,
}: SuggestPanelProps) {
  return (
    <section className="suggest-panel" aria-label="AI suggestion">
      <label className="suggest-panel__label">
        Policy
        <select
          value={policy}
          disabled={disabled}
          onChange={(event) => onPolicyChange(event.target.value as SuggestPolicy)}
        >
          {POLICIES.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </label>

      <button type="button" disabled={disabled} onClick={onAsk}>
        Ask AI
      </button>

      {suggestion ? (
        <>
          <p className="suggest-panel__guess">Suggestion: <strong>{suggestion}</strong></p>
          <button type="button" disabled={disabled} onClick={onApply}>
            Apply suggestion
          </button>
        </>
      ) : null}
    </section>
  )
}
