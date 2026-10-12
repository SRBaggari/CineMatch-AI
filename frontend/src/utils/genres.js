import {
  BookOpen,
  Compass,
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
  Target,
  Trophy,
  Users,
  WandSparkles,
  Zap,
} from 'lucide-react';

// Icon and hue per genre. Hues stay in the purple / blue / cyan family with a
// few warm accents so generated posters remain varied but on-brand.
export const GENRE_STYLE = {
  Action: { icon: Zap, hue: 222 },
  Adventure: { icon: Compass, hue: 200 },
  Animation: { icon: Palette, hue: 188 },
  Biography: { icon: BookOpen, hue: 250 },
  Comedy: { icon: Laugh, hue: 285 },
  Crime: { icon: Fingerprint, hue: 236 },
  Drama: { icon: Drama, hue: 268 },
  Family: { icon: Users, hue: 195 },
  Fantasy: { icon: WandSparkles, hue: 290 },
  History: { icon: Landmark, hue: 245 },
  Horror: { icon: Skull, hue: 320 },
  Music: { icon: Music, hue: 300 },
  Mystery: { icon: Eye, hue: 255 },
  Romance: { icon: Heart, hue: 330 },
  'Science Fiction': { icon: Rocket, hue: 210 },
  Sport: { icon: Trophy, hue: 180 },
  Thriller: { icon: Target, hue: 230 },
  War: { icon: Shield, hue: 215 },
  Western: { icon: Sun, hue: 260 },
};

const FALLBACK = { icon: Film, hue: 260 };

export function genreStyle(genre) {
  return GENRE_STYLE[genre] || FALLBACK;
}

// Deterministic per-title variation so posters of the same genre still differ.
export function titleHash(title) {
  let h = 0;
  for (let i = 0; i < title.length; i += 1) h = (h * 31 + title.charCodeAt(i)) % 997;
  return h;
}
