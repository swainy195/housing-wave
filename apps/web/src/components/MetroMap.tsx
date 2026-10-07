import * as maplibregl from 'maplibre-gl'
import type { Map as MapLibreMap } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { AlertTriangle, CalendarClock, CircleDot, DatabaseZap, MapPinned, Navigation } from 'lucide-react'
import { useEffect, useRef } from 'react'
import type { Project } from '../types'

maplibregl.setWorkerUrl(import.meta.env.DEV
  ? new URL('/node_modules/maplibre-gl/dist/maplibre-gl-worker.mjs', window.location.origin).toString()
  : new URL('/assets/maplibre-gl-worker.mjs', window.location.origin).toString())

type MarkerKind = 'NORMAL' | 'WARNING' | 'DELAYED' | 'DATA_GAP' | 'UPCOMING'

const metroRegions: GeoJSON.FeatureCollection = {
  type: 'FeatureCollection',
  features: [
    { type: 'Feature', properties: { name: '경기' }, geometry: { type: 'Polygon', coordinates: [[[126.48, 37.16], [126.68, 37.01], [127.18, 37.06], [127.74, 37.28], [127.81, 37.75], [127.53, 38.14], [126.87, 38.08], [126.46, 37.74], [126.48, 37.16]]] } },
    { type: 'Feature', properties: { name: '인천' }, geometry: { type: 'Polygon', coordinates: [[[126.28, 37.25], [126.72, 37.25], [126.83, 37.55], [126.55, 37.72], [126.20, 37.60], [126.28, 37.25]]] } },
    { type: 'Feature', properties: { name: '서울' }, geometry: { type: 'Polygon', coordinates: [[[126.76, 37.42], [127.19, 37.42], [127.21, 37.69], [126.76, 37.69], [126.76, 37.42]]] } },
  ],
}

function markerKind(project: Project): MarkerKind {
  if (project.progress?.status === 'DELAYED') return 'DELAYED'
  if (project.data_status === 'NOT_CONNECTED' || project.data_status === 'NOT_AVAILABLE') return 'DATA_GAP'
  if (project.progress?.status === 'WARNING') return 'WARNING'
  if (project.current_stage === 'SUPPLY' || project.current_stage === 'MOVE_IN') return 'UPCOMING'
  return 'NORMAL'
}

const markerSymbol: Record<MarkerKind, string> = { NORMAL: '●', WARNING: '!', DELAYED: '×', DATA_GAP: '—', UPCOMING: '›' }
const markerText: Record<MarkerKind, string> = { NORMAL: '정상', WARNING: '주의', DELAYED: '지연', DATA_GAP: '데이터 미확보', UPCOMING: '공급·입주 예정' }

export function MetroMap({ projects, selectedRegion, onRegion, onOpen }: { projects: Project[]; selectedRegion: string; onRegion: (region: string) => void; onOpen: (id: string) => void }) {
  const mapNode = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MapLibreMap | null>(null)
  const markersRef = useRef<maplibregl.Marker[]>([])
  const mappableProjects = projects.filter(project => project.latitude != null && project.longitude != null)

  useEffect(() => {
    if (!mapNode.current || mapRef.current) return
    const map = new maplibregl.Map({
      container: mapNode.current,
      center: [127.0, 37.52],
      zoom: 8.18,
      attributionControl: false,
      style: { version: 8, sources: {}, layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#e8efed' } }] },
    })
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right')
    map.on('load', () => {
      map.addSource('metro-regions', { type: 'geojson', data: metroRegions })
      map.addLayer({ id: 'metro-region-fill', type: 'fill', source: 'metro-regions', paint: { 'fill-color': ['match', ['get', 'name'], '서울', '#d8f0e8', '인천', '#dfe9f2', '#e9eee6'], 'fill-opacity': 0.88 } })
      map.addLayer({ id: 'metro-region-line', type: 'line', source: 'metro-regions', paint: { 'line-color': '#9eb4ae', 'line-width': 1.2 } })
    })
    const resizeObserver = new ResizeObserver(() => map.resize())
    resizeObserver.observe(mapNode.current)
    mapRef.current = map
    return () => { resizeObserver.disconnect(); map.remove(); mapRef.current = null }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    markersRef.current.forEach(marker => marker.remove())
    markersRef.current = mappableProjects.map(project => {
      const kind = markerKind(project)
      const node = document.createElement('button')
      node.className = `map-marker marker-${kind.toLowerCase()}`
      node.type = 'button'
      node.title = `${project.name} · ${markerText[kind]}`
      node.setAttribute('aria-label', `${project.name} ${markerText[kind]} 상세 보기`)
      node.innerHTML = `<span>${markerSymbol[kind]}</span>`
      node.addEventListener('click', () => onOpen(project.id))
      return new maplibregl.Marker({ element: node, anchor: 'center' }).setLngLat([project.longitude!, project.latitude!]).addTo(map)
    })
  }, [mappableProjects, onOpen])

  return (
    <section className="section metro-map-section" aria-labelledby="map-title">
      <div className="map-heading"><div><div className="eyebrow">METRO EXPLORER</div><h2 id="map-title"><MapPinned size={16} /> 수도권 사업 지도</h2></div><span><Navigation size={13} /> 좌표가 확인된 사업만 표시 · {mappableProjects.length}개</span></div>
      <div className="map-region-tabs" aria-label="지역 빠른 필터">
        {['전체', '서울', '경기', '인천'].map(region => <button key={region} className={(selectedRegion || '전체') === region ? 'active' : ''} onClick={() => onRegion(region === '전체' ? '' : region)}>{region}</button>)}
      </div>
      <div className="map-canvas" ref={mapNode} />
      <div className="map-legend">
        <span className="legend-normal"><CircleDot size={12} /> 정상</span><span className="legend-warning"><AlertTriangle size={12} /> 주의</span><span className="legend-delayed"><AlertTriangle size={12} /> 지연</span><span className="legend-gap"><DatabaseZap size={12} /> 데이터 미확보</span><span className="legend-upcoming"><CalendarClock size={12} /> 예정</span>
      </div>
    </section>
  )
}
