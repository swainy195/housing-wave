import { Check, RefreshCw, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api } from '../services/api'
import type { ReviewCandidateDetail, ReviewCandidateList } from '../types'

const label: Record<string, string> = { region: '지역', district: '지구명', project_name: '사업명', block: '블록', housing_type: '주택유형', address: '주소', units: '호수' }
const mark: Record<string, string> = { MATCH: '✓ 일치', PARTIAL: '≈ 일부 일치', MISMATCH: '× 불일치', UNKNOWN: '? 미확보' }

export function ReviewPanel() {
  const [list, setList] = useState<ReviewCandidateList | null>(null)
  const [detail, setDetail] = useState<ReviewCandidateDetail | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const load = () => api.reviewCandidates().then(rows => { setList(rows); if (!detail && rows.items[0]) open(rows.items[0].candidate_type, rows.items[0].candidate_id) }).catch(e => setError(e.message))
  const open = (type: string, id: string) => api.reviewCandidate(type, id).then(setDetail).catch(e => setError(e.message))
  useEffect(() => { load() }, [])
  const decide = async (id: string, decision: 'verify' | 'reject') => {
    setBusy(true); setError('')
    try { await (decision === 'verify' ? api.verifySuggestion(id) : api.rejectSuggestion(id)); if (detail) await open(detail.candidate_type, detail.candidate.id); load() }
    catch (e) { setError(e instanceof Error ? e.message : '검토 결과를 저장하지 못했습니다.') } finally { setBusy(false) }
  }
  const rebuild = async () => { setBusy(true); try { await api.rebuildSuggestions(); setDetail(null); load() } catch (e) { setError(e instanceof Error ? e.message : '추천을 다시 만들지 못했습니다.') } finally { setBusy(false) } }
  return <main className="review-page">
    <section className="review-heading"><div><span className="page-kicker">HUMAN-IN-THE-LOOP</span><h1>사업 연결 검토</h1><p>추천은 자동 연결이 아닙니다. 공식 원문과 비교한 뒤 담당자가 최종 승인합니다.</p></div><button onClick={rebuild} disabled={busy}><RefreshCw size={15} /> 추천 새로 만들기</button></section>
    {error && <p className="review-error">{error}</p>}
    <section className="review-summary">{[['검토 필요', list?.summary.review_required ?? '—'], ['검증 완료', list?.summary.matched ?? '—'], ['거절 기록', list?.summary.rejected ?? '—']].map(([name, value]) => <div key={name}><span>{name}</span><b>{value}</b></div>)}</section>
    <div className="review-grid"><aside className="review-list"><h2>검토대상</h2>{list?.items.map(item => <button key={`${item.candidate_type}-${item.candidate_id}`} className={detail?.candidate.id === item.candidate_id ? 'selected' : ''} onClick={() => open(item.candidate_type, item.candidate_id)}><small>LIVE · {item.candidate_type === 'LH_NOTICE' ? 'LH 공고' : '입주계획'}</small><b>{item.name}</b><span>{item.province} · 추천 {item.suggestion_count}건 · {item.candidate_status}</span></button>)}</aside>
      <section className="review-detail">{detail ? <><div className="candidate-card"><small>REVIEW REQUIRED · {detail.candidate_type === 'LH_NOTICE' ? 'LH 공고' : '입주계획'}</small><h2>{detail.candidate.name}</h2><p>{detail.candidate.province} · 지구 {detail.candidate.district ?? '미확보'} · 블록 {detail.candidate.block ?? '미확보'}</p><p>주소 {detail.candidate.address ?? '미확보'} · 호수 {detail.candidate.units?.toLocaleString() ?? '미확보'} · 유형 {detail.candidate.housing_type ?? '미확보'}</p>{detail.retrievals.length > 0 && <p className="retrieval-note">공식 역검색 기준: {detail.retrievals.map(r => `${r.project_name} · “${r.search_query}”`).join(' / ')}</p>}</div>
        <h2>추천 사업 <span>상위 {detail.suggestions.length}건</span></h2>{detail.suggestions.length ? detail.suggestions.map(s => <article className="suggestion" key={s.id}><header><div><small>{s.match_rank}위 · {s.review_status}</small><h3>{s.project_name}</h3><p>{s.province} · {s.housing_type ?? '유형 미확보'} · {s.planned_units.toLocaleString()}호</p></div><strong>{Number(s.score).toFixed(0)}<small>점</small></strong></header><div className="evidence-table"><div className="evidence-head"><span>항목</span><span>Candidate</span><span>Project</span><span>판정</span></div>{Object.entries(s.match_evidence).map(([key, value]) => <div className="evidence-row" key={key}><b>{label[key] ?? key}</b><span>{value.candidate ?? '—'}</span><span>{value.project ?? '—'}</span><em className={value.status.toLowerCase()} title={value.reason}>{mark[value.status]}</em></div>)}</div>{s.review_status === 'PENDING' && <div className="review-actions"><button className="verify" disabled={busy} onClick={() => decide(s.id, 'verify')}><Check size={15} /> 검증 승인</button><button disabled={busy} onClick={() => decide(s.id, 'reject')}><X size={15} /> 거절</button></div>}</article>) : <p className="review-empty">안전 기준을 통과한 추천이 없습니다. 후보 상태는 검토 필요로 유지됩니다.</p>}</> : <p className="review-empty">검토 대상을 불러오는 중입니다.</p>}</section></div>
  </main>
}
