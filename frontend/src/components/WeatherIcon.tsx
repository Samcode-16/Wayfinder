import { Cloud, CloudFog, CloudLightning, CloudRain, CloudSnow, CloudSun, Sun } from 'lucide-react';

export default function WeatherIcon({ summary, size = 18 }: { summary: string; size?: number }) {
  const s = summary.toLowerCase();
  const Icon = s.includes('thunder')
    ? CloudLightning
    : s.includes('snow')
      ? CloudSnow
      : /rain|drizzle|shower/.test(s)
        ? CloudRain
        : s.includes('fog')
          ? CloudFog
          : s.includes('overcast')
            ? Cloud
            : /partly|mostly/.test(s)
              ? CloudSun
              : s.includes('clear')
                ? Sun
                : Cloud;
  return <Icon size={size} aria-hidden />;
}
