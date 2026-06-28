---
paths:
  - "datasets/**/*.jsonl"
---

# Evaluation dataset is immutable

- Never edit, reorder, or regenerate `datasets/bug_to_user_story.jsonl`; the 15 examples are the fixed grading set (SPEC "Dicas Finais": "Não altere os datasets de avaliação — apenas os prompts").
- When a metric is low, change `prompts/bug_to_user_story_v2.yml`, never the data.
