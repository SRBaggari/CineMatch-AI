# CineMatch AI: Recommendation Algorithm

This document explains how CineMatch AI turns a user's preferences into ranked, explained recommendations. The code is in `backend/app/recommender.py`. Default parameters are in `backend/app/config.py`.

## Why content-based filtering?

| Approach | Needs | Fits this project? |
|---|---|---|
| Collaborative filtering | Many users' ratings ("people like you also liked…") | No. There are no user accounts or rating history |
| **Content-based filtering** | Descriptions of the items | **Yes.** It works on the first request (no cold start), runs locally, and every score is explainable |

## Step 1: Movie feature vectors

Each of the N movies is represented by five features:

| Feature | Encoding | Built with |
|---|---|---|
| Genres | multi-hot vector over the 19 genres | `MultiLabelBinarizer` |
| Moods | multi-hot vector over the 15 moods | `MultiLabelBinarizer` |
| Language | one-hot vector over the 10 languages | `MultiLabelBinarizer` |
| Keywords + description | TF-IDF vector (~1,250 terms) | `TfidfVectorizer` |
| Release year | integer | — |

### TF-IDF text document

Each movie's text document has every keyword twice as a single squashed tag, then once as raw words, then the description:

```
"time travel" → timetravel timetravel time travel
document      = keyword tags ×2 + keyword words + description
```

Squashing (`normalize_token`) keeps a multi-word theme as one feature, so *time travel* does not match every description that merely mentions *time*. The raw words still let a free-text keyword match description text.

```
tfidf(t, d) = (1 + ln tf(t, d)) · (ln((1 + N) / (1 + df(t))) + 1)      (sublinear_tf, smooth_idf)
```

IDF rewards rare terms. `timeloop` appears in 2 documents, while `friendship` appears in 16, so a shared *time loop* is much stronger evidence of similar taste than a shared *friendship*. Each row is L2-normalised.

## Step 2: User profile

The user's preferences are mapped into the same spaces:

* **Genres, moods, languages:** multi-hot vectors of the chosen labels. Input is matched case-insensitively, and unknown labels are rejected with a 422.
* **Keywords:** turned into a document with the same rules and transformed by the *same fitted* vectoriser.
* **Liked movies (optional):** their mean TF-IDF vector is averaged with the keyword vector. If no genres or moods were chosen, the union of the liked movies' genres and moods is used ("pattern inference").
* **Year range:** `year_min` and/or `year_max`.

## Step 3: Component scores (all in [0, 1])

| Component | Formula | Notes |
|---|---|---|
| Genre | `cos(u, m) = (u·m)/(‖u‖‖m‖) = \|U∩M\| / √(\|U\|·\|M\|)` | Cosine of binary vectors. It rewards covering the user's genres and penalises extra, unrequested genres |
| Mood | same as genre | |
| Language | `1 if movie.language ∈ preferred else 0` | An indicator, so choosing several languages does not dilute the score |
| Keyword | `cos(tfidf_user, tfidf_movie) / max_m cos(…)` | Max-normalisation over the whole catalogue |
| Year | `max(0, 1 − d / 20)`, where `d` = years outside the range | 1 inside the range, 0.5 ten years away, 0 at twenty years |

**Why normalise the keyword score?** Genre and mood cosines reach 1.0 for a perfect match, but a short keyword query compared with a full description rarely gets above 0.4 even for the best movie. Without rescaling, the keyword weight would be ineffective in practice. Dividing by the best cosine in the catalogue maps the strongest text match to 1 and keeps proportions. The divisor is taken over all movies, not the filtered subset, so a movie's score never depends on which filters are applied. The un-normalised value is returned as `components.keyword.raw`.

## Step 4: Weighted score

```
active_c  = the user expressed a preference for component c
w'_c      = w_c / Σ_{k active} w_k        (0 for inactive components)
score     = Σ_c w'_c · s_c                ∈ [0, 1]
```

Default weights are genre 0.30, keyword 0.25, mood 0.20, language 0.15, and year 0.10. They can be overridden per request (`weights`). Any non-negative values are accepted, because they are re-normalised. A request whose active weights are all zero is rejected.

Re-normalising over active components means that a user who gives only genres is scored purely on genre. The score is not capped at 0.30 just because the other preferences were left blank.

**Hard filters vs. soft preferences:** if `strict_languages` or `strict_years` is set, that preference becomes a filter. Every remaining movie would score 1.0 on that component, which adds nothing to the ranking but inflates scores, so the component is switched off. The exception is when it is the only preference; the ranking then falls back to the tie-breakers.

## Step 5: Filtering and ranking

1. `min_rating` (always a hard filter), plus the strict year and language filters when set.
2. Remove liked and `exclude_movie_ids` movies.
3. Remove movies with score 0, which match none of the preferences.
4. Sort by **score ↓, rating ↓, movie_id ↑** (`numpy.lexsort`). Scores are rounded to 6 decimals first, so floating-point noise cannot reorder movies with genuinely equal scores.
5. Return the first `top_n` (default 10).

**Duplicates** are prevented at three levels. The loader drops repeated ids and repeated title+year pairs. Request lists are de-duplicated case-insensitively. Each movie index appears once in the candidate set, with a defensive `seen` check on output.

If nothing survives, the response has an empty list, a `message` naming the step that removed every movie, and a `filter_report` such as `{"total": 130, "after_min_rating": 0, …}`.

## Step 6: Explanation

For each recommendation the engine returns:

* `components`: value, raw value, effective weight, contribution, and an active flag for each of the five components. The contributions add up to `score`.
* `matched`: the movie's genres, moods, language, and keywords that match the user's, plus whether its year is inside the range.
* `reasons`: one sentence per contributing component, ordered by contribution (largest first).
* `top_terms`: the TF-IDF terms with the largest `profile_t × movie_t`, which are the terms driving the keyword cosine.
* `similar_to`: when liked movies were given, the liked movie closest to this one.

### What the score means

The score is a weighted similarity used to **rank** movies. It is not a probability, and it is not calibrated against real user feedback. A score of 0.72 means "72% of the maximum weighted match under these weights", not "72% chance you will enjoy it". The UI shows it as a 0–1 relevance score.

## Worked example

Input (the request in `app/demo.py`):

```json
{"genres": ["Science Fiction", "Thriller"], "languages": ["English"], "moods": ["Mind-Bending"],
 "keywords": ["time travel", "dreams", "artificial intelligence"],
 "year_min": 1995, "year_max": 2020, "min_rating": 7.5}
```

All five components are active, so the default weights are used unchanged.

| # | Movie | genre | language | mood | keyword (raw cos) | year | **score** |
|---|---|---|---|---|---|---|---|
| 1 | Ex Machina | 0.817 | 1 | 0.577 | 0.460 (0.192) | 1.0 | **0.725** |
| 2 | Inception | 0.817 | 1 | 0.577 | 0.425 (0.178) | 1.0 | **0.717** |
| 3 | The Matrix | 0.500 | 1 | 0.577 | 0.479 (0.200) | 1.0 | **0.635** |
| 4 | Terminator 2 | 0.500 | 1 | 0.000 | 1.000 (0.418) | 0.8 | **0.630** |
| 5 | The Prestige | 0.707 | 1 | 0.577 | 0.000 (0.000) | 1.0 | **0.578** |

Checking Ex Machina by hand:

* **Genre:** Ex Machina has genres {Science Fiction, Drama, Thriller} and the user chose {Science Fiction, Thriller}, so the cosine is 2 / √(2·3) = **0.817**.
* **Mood:** Ex Machina has moods {Thought-Provoking, Suspenseful, Mind-Bending} and the user chose {Mind-Bending}, so the cosine is 1 / √(1·3) = **0.577**.
* **Score:** 0.30·0.817 + 0.15·1 + 0.20·0.577 + 0.25·0.460 + 0.10·1 = **0.725**.

Terminator 2 has the best text match (both *time travel* and *artificial intelligence*), so its keyword score is exactly 1.0. Its year score is 0.8 because 1991 is 4 years before 1995: 1 − 4/20 = 0.8.

## Item-to-item similarity ("More like this")

The blocks are combined into one vector per movie: `[ √0.35·ĝ , √0.30·t̂ , √0.25·m̂ , √0.10·l̂ ]`, where each block is L2-normalised. The cosine between two such vectors equals the weighted average of the per-block cosines. All pairs are precomputed once at startup (an N×N matrix).

## Complexity

| Operation | Cost |
|---|---|
| Startup | O(N·V) TF-IDF + O(N²) item matrix, under a second for N = 130 (plus library import time) |
| One recommendation | O(N·(G + M + L + nnz)) vector operations, a few milliseconds |

For catalogues of 100k+ movies, the N² item matrix should be replaced with on-demand similarity or an approximate nearest-neighbour index.

## Known limitations

* The catalogue is small and its metadata is approximate (see the README provenance note).
* TF-IDF matches vocabulary, not meaning. *spaceship* and *starship* are unrelated tokens. Sentence embeddings would address this.
* Content-based filtering tends to recommend "more of the same". A diversity re-ranking step such as MMR would help.
* The default weights were chosen by judgement, not learned from user feedback.
