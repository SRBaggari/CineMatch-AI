import { Bookmark, ThumbsDown, ThumbsUp } from 'lucide-react';
import { useApp } from '../../context/AppContext.jsx';

// Like / dislike are mutually exclusive; favourite is independent. Saved in SQLite via the API.
export default function FeedbackButtons({ movie, size = 'md', showLabels = false }) {
  const { feedback, updateFeedback } = useApp();
  const state = feedback[movie.movie_id] || { reaction: null, favorite: false };
  const iconSize = size === 'sm' ? 15 : 17;

  const react = (reaction) => updateFeedback(movie, { reaction: state.reaction === reaction ? null : reaction });

  return (
    <div className={`feedback-buttons size-${size}`} role="group" aria-label={`Feedback for ${movie.title}`}>
      <button
        type="button"
        className={`fb-btn fb-like ${state.reaction === 'like' ? 'is-on' : ''}`}
        aria-pressed={state.reaction === 'like'}
        title={state.reaction === 'like' ? 'Remove like' : 'Like: boost similar movies'}
        onClick={() => react('like')}
      >
        <ThumbsUp size={iconSize} fill={state.reaction === 'like' ? 'currentColor' : 'none'} />
        {showLabels && <span>{state.reaction === 'like' ? 'Liked' : 'Like'}</span>}
      </button>
      <button
        type="button"
        className={`fb-btn fb-dislike ${state.reaction === 'dislike' ? 'is-on' : ''}`}
        aria-pressed={state.reaction === 'dislike'}
        title={state.reaction === 'dislike' ? 'Remove dislike' : 'Dislike: hide it and demote similar movies'}
        onClick={() => react('dislike')}
      >
        <ThumbsDown size={iconSize} fill={state.reaction === 'dislike' ? 'currentColor' : 'none'} />
        {showLabels && <span>{state.reaction === 'dislike' ? 'Disliked' : 'Dislike'}</span>}
      </button>
      <button
        type="button"
        className={`fb-btn fb-fav ${state.favorite ? 'is-on' : ''}`}
        aria-pressed={state.favorite}
        title={state.favorite ? 'Remove from favourites' : 'Save to favourites'}
        onClick={() => updateFeedback(movie, { favorite: !state.favorite })}
      >
        <Bookmark size={iconSize} fill={state.favorite ? 'currentColor' : 'none'} />
        {showLabels && <span>{state.favorite ? 'Saved' : 'Favourite'}</span>}
      </button>
    </div>
  );
}
