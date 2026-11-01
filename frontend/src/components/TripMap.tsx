import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useEffect, useRef } from 'react';
import type { Theme } from '../hooks/useTheme';

export interface Pin {
  lat: number;
  lon: number;
  label: string;
  title: string;
  color: string;
  kind: 'stop' | 'hotel';
}

const BED =
  '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 4v16"/><path d="M2 8h18a2 2 0 0 1 2 2v10"/><path d="M2 17h20"/><path d="M6 8v9"/></svg>';

// Geoapify vector style URL for MapLibre GL
const geoapifyStyleUrl = (theme: Theme, apiKey: string) => {
  const styleName = theme === 'dark' ? 'dark-matter' : 'osm-bright';
  return `https://maps.geoapify.com/v1/styles/${styleName}/style.json?apiKey=${apiKey}`;
};

// CARTO basemaps (OpenStreetMap data): free fallback for light use, with attribution.
const styleFor = (theme: Theme): maplibregl.StyleSpecification => {
  const variant = theme === 'dark' ? 'dark_all' : 'light_all';
  return {
    version: 8,
    sources: {
      base: {
        type: 'raster',
        tiles: ['a', 'b', 'c', 'd'].map((s) => `https://${s}.basemaps.cartocdn.com/${variant}/{z}/{x}/{y}@2x.png`),
        tileSize: 256,
        attribution: '© OpenStreetMap contributors © CARTO',
      },
    },
    layers: [{ id: 'base', type: 'raster', source: 'base' }],
  };
};

function pinElement(p: Pin) {
  const el = document.createElement('div');
  el.className = `pin pin--${p.kind}`;
  el.style.setProperty('--pin', p.color);
  el.setAttribute('role', 'img');
  el.setAttribute('aria-label', p.title);
  el.title = p.title;
  if (p.kind === 'hotel') el.innerHTML = BED;
  else el.textContent = p.label;
  return el;
}

interface Props {
  pins: Pin[];
  theme: Theme;
  focus?: { lat: number; lon: number } | null;
  geoapifyApiKey?: string | null;
}

export default function TripMap({ pins, theme, focus, geoapifyApiKey }: Props) {
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const markers = useRef<maplibregl.Marker[]>([]);
  const reduce = () => matchMedia('(prefers-reduced-motion: reduce)').matches;

  const apiKey = (geoapifyApiKey ?? (import.meta.env.VITE_GEOAPIFY_API_KEY as string | undefined))?.trim();

  useEffect(() => {
    if (!box.current) return;
    const initialStyle = apiKey ? geoapifyStyleUrl(theme, apiKey) : styleFor(theme);

    const m = new maplibregl.Map({
      container: box.current,
      style: initialStyle,
      center: [0, 20],
      zoom: 1.2,
      attributionControl: { compact: true },
    });

    m.on('error', () => {
      // If remote style fails (e.g. invalid key or network error), safely fall back to CARTO
      try {
        m.setStyle(styleFor(theme));
      } catch {
        // ignore fallback errors
      }
    });

    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right');
    map.current = m;
    return () => {
      m.remove();
      map.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!map.current) return;
    const nextStyle = apiKey ? geoapifyStyleUrl(theme, apiKey) : styleFor(theme);
    map.current.setStyle(nextStyle);
  }, [theme, apiKey]);

  useEffect(() => {
    const m = map.current;
    if (!m) return;
    markers.current.forEach((x) => x.remove());
    markers.current = pins.map((p) => new maplibregl.Marker({ element: pinElement(p) }).setLngLat([p.lon, p.lat]).addTo(m));
    if (pins.length) {
      const b = new maplibregl.LngLatBounds();
      pins.forEach((p) => b.extend([p.lon, p.lat]));
      m.fitBounds(b, { padding: 64, maxZoom: 15, duration: reduce() ? 0 : 600 });
    }
  }, [pins]);

  useEffect(() => {
    if (focus && map.current) {
      map.current.easeTo({ center: [focus.lon, focus.lat], zoom: Math.max(map.current.getZoom(), 14), duration: reduce() ? 0 : 500 });
    }
  }, [focus]);

  return <div ref={box} className="map" role="region" aria-label="Map of today's stops" />;
}
