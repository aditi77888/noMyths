# noMyths

A scriptural fact-checking system providing evidence-based verdicts grounded in primary religious texts (starting with the Vedas: Rigveda, Samaveda, Yajurveda, Atharvaveda).

## Directory Structure
- data/: Raw, interim, processed corpora, and translation backlog.
- scrapers/: Text extraction tools for Sacred-Texts, GRETIL, SanskritDocuments, etc.
- pipeline/: Text cleaning, verse segmentation, cross-numbering alignment, metadata tagging, validation.
- configs/: Source registry, Pinecone config, model configs, and alignment maps.
- 	ranslation/: LLM-assisted translation queue and prompts.
- embeddings/: Embedding generation (English & Multilingual) and Pinecone upserts.
- classifier/: 3-Tier classification routing claims to relevant texts and decomposing queries.
- 
etrieval/: Hybrid search retriever and evidence-backed verdict generator.
- pi/: FastAPI backend with verification endpoint and verdict audit logging.
- eval/: Golden claims benchmark and evaluation harness.
- rontend/: Streamlit interactive UI.
- scripts/: Execution runners for pipeline stages.
- 	ests/: Automated unit and integration tests.
- docs/: Design documents, source registries, and translation backlogs.
