# Footnote evaluation

20 answerable and 6 unanswerable questions. Model: ollama / default model. top_k=6, min_relevance=0.5.

| Metric | Result |
|---|---|
| Retrieval hit rate (evidence in top 6) | 20/20 (100%) |
| Retrieval MRR | 0.93 |
| Correct answers | 19/20 (95%) |
| Correct answers with valid citations | 19/19 (100%) |
| Correct refusals (unanswerable) | 6/6 (100%) |
| False refusals (answerable) | 0/20 (0%) |
| Invalid citations | 0 |
| Median seconds per question | 2.8 |

Top-1 relevance scores: answerable min 0.584 / median 0.707; unanswerable max 0.765 / median 0.615.
Best separating threshold: 0.584 (22/26 questions on the right side).

Misses:
- sms-mfa: missing expected facts
