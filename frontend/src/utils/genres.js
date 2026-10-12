import {
  BookOpen,
  Compass,
  Crosshair,
  Drama,
  Eye,
  Film,
  Fingerprint,
  Heart,
  Landmark,
  Laugh,
  Music,
  Palette,
  Rocket,
  Shield,
  Skull,
  Sun,
  Trophy,
  Users,
  WandSparkles,
  Zap,
} from 'lucide-react';

// Visual identity per genre: an icon and a hue for generated posters / chips.
export const GENRE_STYLE = {
  Action: { icon: Zap, hue: 18 },
  Adventure: { icon: Compass, hue: 38 },
  Animation: { icon: Palette, hue: 190 },
  Biography: { icon: BookOpen, hue: 30 },
  Comedy: { icon: Laugh, hue: 48 },
  Crime: { icon: Fingerprint, hue: 0 },
  Drama: { icon: Drama, hue: 280 },
  Family: { icon: Users, hue: 150 },
  Fantasy: { icon: WandSparkles, hue: 265 },
  History: { icon: Landmark, hue: 35 },
  Horror: { icon: Skull, hue: 350 },
  Music: { icon: Music, hue: 320 },
  Mystery: { icon: Eye, hue: 230 },
  Romance: { icon: Heart, hue: 335 },
  'Science Fiction': { icon: Rocket, hue: 205 },
  Sport: { icon: Trophy, hue: 95 },
  Thriller: { icon: Crosshair, hue: 215 },
  War: { icon: Shield, hue: 75 },
  Western: { icon: Sun, hue: 28 },
};

const FALLBACK = { icon: Film, hue: 250 };

export function genreStyle(genre) {
  return GENRE_STYLE[genre] || FALLBACK;
}

// Deterministic per-title variation so posters of the same genre still differ.
export function titleHash(title) {
  let h = 0;
  for (let i = 0; i < title.length; i += 1) h = (h * 31 + title.charCodeAt(i)) % 360;
  return h;
}
