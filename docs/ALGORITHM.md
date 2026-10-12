# CineMatch AI: Recommendation Algorithm

This document explains, step by step, how CineMatch AI turns a user's preferences into ranked, explained recommendations. All the code is in `backend/app/recommender.py`.

## Why content-based filtering?

| Approach | Needs | Fits this project? |
|---|---|---|
| Collaborative filtering | Many users' ratings ("people like you also liked…") | No. The app has no user accounts and no rating history |
| **Content-based filtering** | Descriptions of the items | **Yes.** It works from the first request (no cold-start problem), runs locally, and is explainable |
| Hybrid | Both | Part of it: content similarity is blended with rule-based pattern scores |

## Step 1: Feature engineering (the "content soup")

Each movie's metadata becomes a single string. Fields are repeated to set their importance:

| Field | Repeat | Reason |
|---|---|---|
| genres | ×3 | Strongest signal of taste |
| moods | ×2 | Captures how a film feels |
| keywords | ×2 | Specific themes ("time loop", "serial killer") |
| director | ×1 | Style signal |
| cast | ×1 | Star preference |
| overview | ×1 | Free-text context |

Multi-word labels are normalised into single tokens (`normalize_token` in `data_loader.py`):

```
"Science Fiction"   → sciencefiction
"Christopher Nolan" → christophernolan
"Mind-Bending"      → mindbending
```

Without this step, "Christopher Nolan" and "Christopher Lloyd" would share the token *christopher* and look falsely similar.

Real soup for **Toy Story**:

```
animation comedy family adventure ×3 · funny heartwarming feelgood ×2 ·
toys friendship jealousy rivalry adventure ×2 · johnlasseter · tomhanks timallen donrickles ·
A cowboy doll feels threatened when a flashy new space ranger toy becomes his owner's favourite.
```

## Step 2: TF-IDF vectorisation

`TfidfVectorizer(stop_words="english", sublinear_tf=True)` converts the 130 soups into a 130 × ~1,600 sparse matrix.

```
tfidf(t, d) = (1 + log tf(t, d)) × (ln((1 + N) / (1 + df(t))) + 1)
```

* **TF** (term frequency, log-scaled because `sublinear_tf=True`) rewards terms that appear often in one movie, such as the repeated genres.
* **IDF** (inverse document frequency) rewards rare terms. `timeloop` appears in 2 movies and `drama` in 75, so a shared *time loop* says much more than a shared *drama*.
* Each row is L2-normalised, so cosine similarity becomes a dot product.

The engine also precomputes the 130 × 130 **item-similarity matrix**, which is used for "More like this" and for "similar to a movie you liked".

## Step 3: Building the user profile vector

The engine combines two sources of preference:

1. **Explicit preferences.** Genres, moods, and keywords are turned into a pseudo-document using the same repetition weights. Each keyword is added both as a squashed tag (`timetravel`) and as raw words (`time travel`), so it can match tags and overview text. The pseudo-document is then transformed by the *same fitted* vectoriser.
2. **Behavioural preferences.** The mean TF-IDF vector of the movies the user marked as liked.

```
profile = normalize( mean( normalize(explicit), normalize(liked_mean) ) )
```

The highest-weighted dimensions of this vector are shown in the UI as **"Your AI Taste Profile"**.

**Pattern inference:** if the user liked movies but picked no genres or moods, the union of the liked movies' genres and moods becomes the target set for Step 5.

## Step 4: Cosine similarity

```
content(u, m) = (profile · movie_m) / (‖profile‖ · ‖movie_m‖)   ∈ [0, 1]
```

This is computed for all movies in one vectorised scikit-learn call.

## Step 5: Hybrid scoring, filtering, ranking

```
score = w_c·content + w_g·Jaccard(G_user, G_movie) + w_m·Jaccard(M_user, M_movie) + w_q·rating_norm

Jaccard(A, B) = |A ∩ B| / |A ∪ B|
rating_norm  = (rating − min_rating) / (max_rating − min_rating)
```

The default weights are content 0.55, genre 0.20, mood 0.15, and quality 0.10, set in `config.py`. A component with no signal (no target genres, for example) is switched off and the remaining weights are re-normalised to sum to 1.

Hard filters (year range, minimum rating, languages) are applied next. Already-liked movies are removed, and the rest are sorted by score.

## Step 6: Explanation

For every recommended movie, the engine returns:

* **Matched genres, moods, and keywords**: set intersections with the user's targets.
* **similar_to**: the liked movie with the highest item similarity, plus any shared director, cast, or keywords.
* **shared_features**: the five dimensions with the largest `profile_i × movie_i`. These are the terms that contribute most to the cosine score.
* **score_breakdown**: score, weight, and contribution for each component. The contributions add up exactly to the final score.
* **reasons**: readable sentences built from the items above.

## Worked example: a user who liked *Toy Story*

Request: `{"liked_movie_ids": [30]}`. No genres or moods were selected, so they are inferred:

* Genres → {Animation, Adventure, Comedy, Family}
* Moods → {Feel-Good, Funny, Heartwarming}

Top recommendation: **Finding Nemo**

| Component | Score | Weight | Contribution |
|---|---|---|---|
| Content (cosine) | 0.267 | 0.55 | 0.147 |
| Genre (Jaccard) | 1.000 | 0.20 | 0.200 |
| Mood (Jaccard) | 1.000 | 0.15 | 0.150 |
| Quality (8.2/10) | 0.607 | 0.10 | 0.061 |
| **Final** | | | **0.558 → 56% match** |

Explanation shown to the user:

* Matches your genres: Animation, Adventure, Comedy, Family
* Fits the mood you want: Feel-Good, Funny, Heartwarming
* 27% similar to Toy Story, which you liked
* Strongest shared signals: Animation · Adventure · Comedy · friendship · Family

## Complexity

| Operation | Cost |
|---|---|
| Startup (TF-IDF + item matrix) | O(N·V) + O(N²). A few seconds at startup for N = 130, mostly library imports |
| One recommendation | O(N·V) sparse dot products, a few milliseconds |
| Memory | Item matrix N² floats (130² ≈ 17k) |

With much larger catalogues (100k+ movies), the N² matrix should be replaced with on-demand similarity or an approximate nearest-neighbour index.

## Known limitations

* The dataset is small and hand-curated (130 movies), so results are bounded by the catalogue.
* Content-based filtering can over-specialise and recommend "more of the same". A diversity re-ranking step such as MMR would help.
* TF-IDF matches vocabulary, not meaning. *spaceship* and *starship* are unrelated tokens. Sentence embeddings would fix this, at the cost of a heavier model.
