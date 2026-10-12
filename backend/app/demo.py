"""Command-line demo of the recommendation engine.

Run from the backend folder:
    .\\.venv\\Scripts\\python.exe -m app.demo
"""

import json

from .config import DATA_PATH
from .data_loader import load_movies
from .recommender import COMPONENTS, RecommendationEngine, UserPreferences

SAMPLE = {
    "genres": ["Science Fiction", "Thriller"],
    "languages": ["English"],
    "moods": ["Mind-Bending"],
    "keywords": ["time travel", "dreams", "artificial intelligence"],
    "year_min": 1995,
    "year_max": 2020,
    "min_rating": 7.5,
}


def main() -> None:
    engine = RecommendationEngine(load_movies(DATA_PATH))
    result = engine.recommend(UserPreferences(**SAMPLE))
    profile = result["profile"]

    print("SAMPLE INPUT")
    print(json.dumps(SAMPLE, indent=2))
    print("\nEFFECTIVE WEIGHTS (re-normalised over active components)")
    print("  " + "  ".join(f"{c}={profile['weights'][c]:.2f}" for c in COMPONENTS))
    print("\nFILTER REPORT", result["filter_report"])
    print("\nTOP PROFILE TERMS", ", ".join(t["term"] for t in profile["top_terms"][:8]))

    header = f"{'#':>2}  {'Title':<38}{'Score':>6}  " + "".join(f"{c[:5]:>7}" for c in COMPONENTS) + f"{'kw cos':>8}"
    print("\nRANKED RECOMMENDATIONS (component values in [0, 1])")
    print(header)
    print("-" * len(header))
    for r in result["recommendations"]:
        comps = r["components"]
        print(
            f"{r['rank']:>2}  {r['title'][:37]:<38}{r['score']:>6.3f}  "
            + "".join(f"{comps[c]['value']:>7.3f}" for c in COMPONENTS)
            + f"{comps['keyword']['raw']:>8.3f}"
        )

    print("\nEXPLANATIONS (top 3)")
    for r in result["recommendations"][:3]:
        print(f"\n#{r['rank']} {r['title']}  score={r['score']:.3f}")
        for c in COMPONENTS:
            comp = r["components"][c]
            print(f"   {c:<9} {comp['value']:.3f} x {comp['weight']:.2f} = {comp['contribution']:.3f}")
        for reason in r["reasons"]:
            print(f"   - {reason}")
        if r["top_terms"]:
            print(f"   shared TF-IDF terms: {', '.join(r['top_terms'])}")


if __name__ == "__main__":
    main()
