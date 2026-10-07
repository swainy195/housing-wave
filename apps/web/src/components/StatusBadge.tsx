import { Check, CircleDashed, Link2Off, MinusCircle } from 'lucide-react'
import type { DataStatus } from '../types'
import { statusLabels } from '../utils/format'

const icons = {
  AVAILABLE: Check,
  PARTIAL: CircleDashed,
  NOT_CONNECTED: Link2Off,
  NOT_AVAILABLE: MinusCircle,
}

export function StatusBadge({ status, compact = false }: { status: DataStatus; compact?: boolean }) {
  const Icon = icons[status]
  return (
    <span className={`status-badge status-${status.toLowerCase()} ${compact ? 'compact' : ''}`}>
      <Icon size={compact ? 11 : 13} strokeWidth={2.2} aria-hidden="true" />
      {statusLabels[status]}
    </span>
  )
}

