import {
  Brain,
  Flame,
  Ghost,
  HandHeart,
  HeartCrack,
  Heart,
  Laugh,
  Lightbulb,
  Moon,
  Mountain,
  Smile,
  Sparkles,
  Timer,
  WandSparkles,
  Zap,
} from 'lucide-react';

// Presentation for the mood selection cards. Keys must match the dataset's mood labels;
// unknown moods from the backend fall back to a generic card.
export const MOOD_STYLE = {
  'Action-Packed': { icon: Zap, blurb: 'Chases, fights and adrenaline' },
  Dark: { icon: Moon, blurb: 'Bleak, intense, morally grey' },
  Emotional: { icon: HeartCrack, blurb: 'Stories that hit you hard' },
  Epic: { icon: Mountain, blurb: 'Grand scale and big stakes' },
  'Feel-Good': { icon: Smile, blurb: 'Leaves you smiling' },
  Funny: { icon: Laugh, blurb: 'Jokes, wit and laughs' },
  Gritty: { icon: Flame, blurb: 'Raw, rough and realistic' },
  Heartwarming: { icon: HandHeart, blurb: 'Kindness and connection' },
  Inspiring: { icon: Sparkles, blurb: 'Underdogs and big dreams' },
  'Mind-Bending': { icon: Brain, blurb: 'Twists that mess with reality' },
  Romantic: { icon: Heart, blurb: 'Love stories' },
  Scary: { icon: Ghost, blurb: 'Fear, dread and jump scares' },
  Suspenseful: { icon: Timer, blurb: 'Edge-of-your-seat tension' },
  'Thought-Provoking': { icon: Lightbulb, blurb: 'Ideas that stay with you' },
  Whimsical: { icon: WandSparkles, blurb: 'Playful, quirky and magical' },
};

export function moodStyle(mood) {
  return MOOD_STYLE[mood] || { icon: Sparkles, blurb: '' };
}
