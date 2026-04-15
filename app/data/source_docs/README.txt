Place sector reports under subfolders so ingestion can tag chunks and retrieval stays scoped:

  saas/          — B2B SaaS & AI SaaS benchmark reports (.txt or .pdf)
  distilleries/ — distillery & spirits reports (.txt or .pdf)

Run: POST /sources/ingest (refreshes chunk_store.json and the Chroma index under app/data/chroma/).

Adding a new sector: create a folder here, map it in app/services/source_sectors.py and app/services/metric_catalog.py, then re-ingest.
