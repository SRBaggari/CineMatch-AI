import { Link } from 'react-router-dom';
import { Compass } from 'lucide-react';
import { StateMessage } from '../components/ui/Feedback.jsx';

export default function NotFoundPage() {
  return (
    <div className="page container narrow">
      <StateMessage
        icon={Compass}
        title="Page not found"
        action={
          <Link to="/" className="btn btn-primary">
            Back to home
          </Link>
        }
      >
        <p>The page you’re looking for doesn’t exist.</p>
      </StateMessage>
    </div>
  );
}
