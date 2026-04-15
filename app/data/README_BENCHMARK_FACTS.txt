benchmark_facts.json — operational workflow
-------------------------------------------

1) Citations
   Replace every "OPERATIONAL: ..." placeholder with a short VERBATIM quote from the named PDF.
   Keep statistic_label aligned with what the report actually says (median, quartiles, survey, etc.).

2) Coverage
   Add one object per (sector_id or industry_code) × metric_code × geography × optional company_stage.
   Null geography or company_stage = wildcard (matches any request value for that dimension).
   More specific rows (non-null geo/stage) win over wildcards.

3) After editing facts
   No server restart required; the next POST /benchmark/generate will read the file.
   If you also changed PDFs, run POST /sources/ingest to refresh chunk_store.json and the Chroma index (app/data/chroma).

4) LLM assist
   POST /benchmark/suggest-extract with the same body as /benchmark/generate (requires OPENAI_API_KEY).
   Merge vetted suggestions into this file manually — human review stays mandatory.

5) Embeddings / Chroma
   If you add OPENAI_API_KEY later, re-run POST /sources/ingest so vectors are rebuilt with the same embedding model settings.

Postgres is not required for this milestone; JSON files are the source of truth.
