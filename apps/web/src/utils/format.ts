import type { DataStatus, Stage } from '../types'

export const stageLabels: Record<Stage, string> = {
  POLICY: '정책',
  BUSINESS: '사업화',
  PERMIT: '인허가',
  CONSTRUCTION: '건설',
  SUPPLY: '공급',
  MOVE_IN: '입주',
}

export const statusLabels: Record<DataStatus, string> = {
  AVAILABLE: '확보',
  PARTIAL: '일부확보',
  NOT_CONNECTED: '미연계',
  NOT_AVAILABLE: '미제공',
}

export const issueLabels: Record<string, string> = {
  SCHEDULE_DELAY: '일정 지연',
  PROGRESS_DELAY: '공정 저하',
  STALE_DATA: '기준일 경과',
  DATA_GAP: '데이터 공백',
  SCHEDULE_CHANGED: '일정 변경',
}

export const progressLabels: Record<string, string> = {
  NORMAL: '정상',
  WARNING: '주의',
  DELAYED: '지연',
  DATA_CHECK: '데이터 확인',
}

export const formatUnits = (value: number | null | undefined) =>
  value === null || value === undefined ? '데이터 미확보' : `${value.toLocaleString('ko-KR')}호`

export const formatDate = (value: string | null | undefined) => {
  if (!value) return '미확보'
  if (/^\d{4}-\d{2}$/.test(value)) return value.replace('-', '.')
  const date = new Date(value)
  return `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')}`
}
