# islamic-rag-system

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Version](https://img.shields.io/badge/version-0.1.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Description

islamic-rag-system is a Python project analyzed by PyDevKit.

## Features

- Automatic project metadata discovery
- Public function and class inventory
- Dependency and entry point detection

## Installation

```bash
pip install -e .
```

## Usage

```bash
python pydevkit\pydevkit\cli.py
```

## CLI Commands

- No console scripts detected

## Project Structure

- `_run_index.py`
- `pydevkit\pydevkit\__init__.py`
- `pydevkit\pydevkit\analysis\__init__.py`
- `pydevkit\pydevkit\analysis\doctor.py`
- `pydevkit\pydevkit\analysis\inspector.py`
- `pydevkit\pydevkit\cli.py`
- `pydevkit\pydevkit\deadcode\__init__.py`
- `pydevkit\pydevkit\deadcode\reporter.py`
- `pydevkit\pydevkit\deadcode\scanner.py`
- `pydevkit\pydevkit\readme\__init__.py`
- `pydevkit\pydevkit\readme\analyzer.py`
- `pydevkit\pydevkit\readme\generator.py`
- `pydevkit\pydevkit\report\__init__.py`
- `pydevkit\pydevkit\report\generator.py`
- `pydevkit\pydevkit\testgen\__init__.py`
- `pydevkit\pydevkit\testgen\extractor.py`
- `pydevkit\pydevkit\testgen\generator.py`
- `pydevkit\pydevkit\utils\__init__.py`
- `pydevkit\pydevkit\utils\api_client.py`
- `pydevkit\pydevkit\utils\config.py`
- `pydevkit\pydevkit\utils\file_utils.py`
- `pydevkit\sample_project\example.py`
- `pydevkit\sample_project\tests\test_example.py`
- `pydevkit\setup.py`
- `pydevkit\tests\test_analysis.py`
- `pydevkit\tests\test_deadcode.py`
- `pydevkit\tests\test_readme.py`
- `pydevkit\tests\test_report.py`
- `pydevkit\tests\test_testgen.py`
- `scripts\__init__.py`
- `scripts\evaluate_rag.py`
- `scripts\index_all.py`
- `scripts\load_hadiths.py`
- `scripts\load_quran.py`
- `scripts\load_tafsir.py`
- `scripts\run_indexing.py`
- `scripts\test.py`
- `scripts\test_citation_engine.py`
- `scripts\test_quran_query.py`
- `scripts\test_tafsir.py`
- `src\__init__.py`
- `src\agents\__init__.py`
- `src\agents\classifier.py`
- `src\agents\final_test_query.py`
- `src\agents\islamic_graph.py`
- `src\agents\state.py`
- `src\agents\test_classifier.py`
- `src\agents\test_islamic_graph.py`
- `src\api\main.py`
- `src\api\v1\__init__.py`
- `src\api\v1\api_keys.py`
- `src\api\v1\ask.py`
- `src\api\v1\auth.py`
- `src\api\v1\health.py`
- `src\api\v1\tenants.py`
- `src\auth\__init__.py`
- `src\auth\api_keys.py`
- `src\auth\dependencies.py`
- `src\auth\jwt.py`
- `src\auth\passwords.py`
- `src\config\settings.py`
- `src\core\__init__.py`
- `src\core\islamic_chunker.py`
- `src\core\islamic_vectorDB.py`
- `src\core\test_chunker.py`
- `src\core\test_vectorDB.py`
- `src\db\__init__.py`
- `src\db\base.py`
- `src\db\database.py`
- `src\db\models\__init__.py`
- `src\db\models\api_key.py`
- `src\db\models\conversation.py`
- `src\db\models\document.py`
- `src\db\models\tenant.py`
- `src\db\models\usage_record.py`
- `src\db\models\user.py`
- `src\db\session.py`
- `src\middleware\__init__.py`
- `src\middleware\error_handling.py`
- `src\middleware\security.py`
- `src\middleware\tenant.py`
- `src\services\__init__.py`
- `src\services\cache_service.py`
- `src\services\conversation_service.py`
- `src\services\tenant_service.py`
- `src\utils\__init__.py`
- `src\utils\citation_engine.py`
- `src\utils\translator.py`

## Public Functions

- `run_doctor` in `pydevkit\pydevkit\analysis\doctor.py`: Run project health checks and return a normalized report.
- `inspect_project` in `pydevkit\pydevkit\analysis\inspector.py`: Return a consolidated project inspection report.
- `cli` in `pydevkit\pydevkit\cli.py`: PyDevKit developer productivity commands.
- `deadcode` in `pydevkit\pydevkit\cli.py`: Find unused functions, variables, and imports.
- `readme` in `pydevkit\pydevkit\cli.py`: Generate a README.md file.
- `testgen` in `pydevkit\pydevkit\cli.py`: Generate pytest tests for public functions.
- `inspect` in `pydevkit\pydevkit\cli.py`: Inspect project structure, metrics, and risks.
- `doctor` in `pydevkit\pydevkit\cli.py`: Run project health checks.
- `report` in `pydevkit\pydevkit\cli.py`: Generate an HTML report for the project.
- `print_deadcode_report` in `pydevkit\pydevkit\deadcode\reporter.py`: Print dead code results as a Rich table.
- `scan_deadcode` in `pydevkit\pydevkit\deadcode\scanner.py`: Scan a project for unused public functions, imports, and variables.
- `remove_unused_imports` in `pydevkit\pydevkit\deadcode\scanner.py`: Remove unused import aliases identified by scan_deadcode.
- `analyze_project` in `pydevkit\pydevkit\readme\analyzer.py`: Analyze a Python project and return README-friendly metadata.
- `generate_readme` in `pydevkit\pydevkit\readme\generator.py`: Generate README.md for a project.
- `generate_html_report` in `pydevkit\pydevkit\report\generator.py`: Build the complete HTML report string.
- `generate_report` in `pydevkit\pydevkit\report\generator.py`: Run all analyses and write an HTML report.
- `extract_functions` in `pydevkit\pydevkit\testgen\extractor.py`: Extract public functions and metadata from a project.
- `generate_tests` in `pydevkit\pydevkit\testgen\generator.py`: Generate pytest test files for public functions in a project.
- `is_offline_fallback_error` in `pydevkit\pydevkit\utils\api_client.py`: Return True when callers should use deterministic offline generation.
- `call_groq` in `pydevkit\pydevkit\utils\api_client.py`: Call Groq chat completions and return the response text.
- `load_config` in `pydevkit\pydevkit\utils\config.py`: Load .pydevkit.toml from a project directory with safe defaults.
- `get_python_files` in `pydevkit\pydevkit\utils\file_utils.py`: Return Python files below a path, excluding ignored/generated folders.
- `read_file_safe` in `pydevkit\pydevkit\utils\file_utils.py`: Read a text file while tolerating encoding issues.
- `write_file` in `pydevkit\pydevkit\utils\file_utils.py`: Write text to a file, creating parent directories when required.
- `add_numbers` in `pydevkit\sample_project\example.py`: Add two integers and return the total.
- `multiply_numbers` in `pydevkit\sample_project\example.py`: Multiply two integers and return the product.
- `normalize_text` in `pydevkit\sample_project\example.py`: Normalize whitespace and lowercase a string.
- `unused_discount` in `pydevkit\sample_project\example.py`: Calculate a discounted price.
- `unused_slugify` in `pydevkit\sample_project\example.py`: Convert a phrase into a simple URL slug.
- `distance_from_origin` in `pydevkit\sample_project\example.py`: Calculate distance from the origin for a point.
- `test_add_numbers_is_callable` in `pydevkit\sample_project\tests\test_example.py`: Assert add_numbers can be imported.
- `test_multiply_numbers_is_callable` in `pydevkit\sample_project\tests\test_example.py`: Assert multiply_numbers can be imported.
- `test_normalize_text_is_callable` in `pydevkit\sample_project\tests\test_example.py`: Assert normalize_text can be imported.
- `test_unused_discount_is_callable` in `pydevkit\sample_project\tests\test_example.py`: Assert unused_discount can be imported.
- `test_unused_slugify_is_callable` in `pydevkit\sample_project\tests\test_example.py`: Assert unused_slugify can be imported.
- `test_distance_from_origin_is_callable` in `pydevkit\sample_project\tests\test_example.py`: Assert distance_from_origin can be imported.
- `test_load_config_reads_pydevkit_toml` in `pydevkit\tests\test_analysis.py`: Assert .pydevkit.toml values are loaded into config.
- `test_load_config_normalizes_empty_output` in `pydevkit\tests\test_analysis.py`: Assert empty configured output is normalized to None.
- `test_deadcode_respects_config_ignore_names` in `pydevkit\tests\test_analysis.py`: Assert configured names are ignored by the deadcode scanner.
- `test_inspect_project_returns_summary` in `pydevkit\tests\test_analysis.py`: Assert inspect_project returns useful summary metrics.
- `test_doctor_does_not_flag_local_imports_as_missing` in `pydevkit\tests\test_analysis.py`: Assert doctor treats project modules as local imports.
- `test_doctor_treats_subfolder_module_stems_as_local_imports` in `pydevkit\tests\test_analysis.py`: Assert doctor allows tests that import a local module by file stem.
- `test_doctor_does_not_flag_known_dev_dependencies_as_unused` in `pydevkit\tests\test_analysis.py`: Assert common tooling requirements are not treated as unused runtime deps.
- `test_run_doctor_reports_health_issues` in `pydevkit\tests\test_analysis.py`: Assert doctor reports missing project hygiene files.
- `test_scan_deadcode_detects_unused_sample_symbols` in `pydevkit\tests\test_deadcode.py`: Assert unused sample functions and imports are reported.
- `test_scan_deadcode_does_not_report_used_functions` in `pydevkit\tests\test_deadcode.py`: Assert functions called elsewhere are not reported as unused.
- `test_scan_deadcode_empty_folder` in `pydevkit\tests\test_deadcode.py`: Assert an empty folder returns no results.
- `test_scan_deadcode_folder_with_no_python_files` in `pydevkit\tests\test_deadcode.py`: Assert a folder without Python files returns no results.
- `test_scan_deadcode_does_not_report_local_variables` in `pydevkit\tests\test_deadcode.py`: Assert local variables are not reported as module-level dead code.
- `test_remove_unused_imports_removes_only_unused_alias` in `pydevkit\tests\test_deadcode.py`: Assert import fixing preserves used aliases on the same line.
- `test_scan_deadcode_skips_ignored_generated_folders` in `pydevkit\tests\test_deadcode.py`: Assert generated and ignored folders are skipped by default.
- `test_scan_deadcode_respects_min_confidence` in `pydevkit\tests\test_deadcode.py`: Assert confidence filtering can hide lower-confidence symbols.
- `test_scan_deadcode_respects_config_ignore_files` in `pydevkit\tests\test_deadcode.py`: Assert configured ignored file globs are not scanned.
- `test_scan_deadcode_treats_dunder_all_as_public_usage` in `pydevkit\tests\test_deadcode.py`: Assert exported public API symbols are not reported as unused.
- `test_scan_deadcode_treats_incremental_dunder_all_as_public_usage` in `pydevkit\tests\test_deadcode.py`: Assert simple __all__.append and __all__.extend exports are honored.
- `test_analyze_project_returns_expected_structure` in `pydevkit\tests\test_readme.py`: Assert project analysis returns README-ready metadata.
- `test_generate_readme_without_ai_creates_file` in `pydevkit\tests\test_readme.py`: Assert offline README generation writes markdown to disk.
- `test_analyze_project_uses_resolved_name_for_dot_path` in `pydevkit\tests\test_readme.py`: Assert project_name is not blank when analyzing the current directory.
- `test_compact_ai_context_limits_large_project_metadata` in `pydevkit\tests\test_readme.py`: Assert AI README prompts stay compact for larger projects.
- `test_generate_readme_falls_back_when_ai_prompt_is_too_large` in `pydevkit\tests\test_readme.py`: Assert token-limit errors fall back to offline README generation.
- `fail_with_token_limit` in `pydevkit\tests\test_readme.py`: No docstring
- `test_generate_html_report_contains_project_name` in `pydevkit\tests\test_report.py`: Assert the rendered HTML includes the project name.
- `test_generate_html_report_escapes_html_entities` in `pydevkit\tests\test_report.py`: Assert special characters are escaped in the report.
- `test_generate_report_writes_file_to_disk` in `pydevkit\tests\test_report.py`: Assert generate_report writes an HTML file to the specified path.
- `test_generate_report_defaults_to_project_dir` in `pydevkit\tests\test_report.py`: Assert generate_report writes to pydevkit-report.html by default.
- `test_generate_report_against_sample_project` in `pydevkit\tests\test_report.py`: Assert generate_report works against the real sample_project fixture.
- `test_extract_functions_finds_public_sample_functions` in `pydevkit\tests\test_testgen.py`: Assert public sample functions are extracted.
- `test_generate_tests_offline_creates_syntax_valid_file` in `pydevkit\tests\test_testgen.py`: Assert offline test generation works without a Groq API key.
- `test_generated_offline_tests_include_project_path` in `pydevkit\tests\test_testgen.py`: Assert generated tests can import source modules from custom output dirs.
- `test_generated_offline_tests_alias_test_prefixed_imports` in `pydevkit\tests\test_testgen.py`: Assert generated imports do not create pytest collection collisions.
- `test_generate_tests_falls_back_offline_for_transient_ai_errors` in `pydevkit\tests\test_testgen.py`: Assert transient provider failures still produce deterministic tests.
- `test_extract_functions_captures_args_and_docstrings` in `pydevkit\tests\test_testgen.py`: Assert function args, type hints, and docstrings are captured.
- `fail_with_timeout` in `pydevkit\tests\test_testgen.py`: No docstring
- `main` in `scripts\evaluate_rag.py`: Run the evaluation.
- `evaluate_retrieval` in `scripts\evaluate_rag.py`: Evaluate retrieval quality for a query.
- `evaluate_generation` in `scripts\evaluate_rag.py`: Evaluate generation quality for a response.
- `run_evaluation` in `scripts\evaluate_rag.py`: Run full evaluation on all test queries.
- `summarize` in `scripts\evaluate_rag.py`: Summarize all evaluation results.
- `index_quran` in `scripts\index_all.py`: Index the Holy Quran.
- `index_hadith` in `scripts\index_all.py`: Index all six authentic Hadith collections.
- `index_tafsir` in `scripts\index_all.py`: Index Tafsir Ibn Kathir.
- `main` in `scripts\index_all.py`: Run complete indexing pipeline.
- `load_hadith_collection` in `scripts\load_hadiths.py`: Load a Hadith collection from HadithAPI.com.

Args:
    collection_key: Collection key
        (bukhari, muslim, abudawud, tirmidhi, nasai, ibnmajah)

Returns:
    List of LangChain Document objects
- `load_quran_english_only` in `scripts\load_quran.py`: Load Quran English-only translation (Yusuf Ali) from AlQuran.cloud API.
Kept for backward compatibility.

Returns: List of LangChain Document objects
- `load_tafsir_from_json` in `scripts\load_tafsir.py`: Load Tafsir JSON and convert into LangChain Documents.
- `test_quran_loader` in `scripts\test.py`: No docstring
- `test_hadith_loader` in `scripts\test.py`: No docstring
- `test_citation_extraction` in `scripts\test_citation_engine.py`: No docstring
- `main` in `scripts\test_quran_query.py`: No docstring
- `classifier_node` in `src\agents\classifier.py`: Classifies user query into Islamic knowledge domains
and determines which collections to retrieve from.
Uses keyword-based routing (fast, no LLM call needed).
Falls back to LLM classification only if keywords don't match.
- `main` in `src\agents\final_test_query.py`: No docstring
- `translate_query_node` in `src\agents\islamic_graph.py`: Translates non-English queries to English for vector search.
The vector store has English content, so Urdu/Arabic queries must be translated first.
- `translate_response_node` in `src\agents\islamic_graph.py`: Translates the English response back to the user's selected language.
Preserves citations and Islamic terminology.
- `unified_retriever_node` in `src\agents\islamic_graph.py`: No docstring
- `synthesis_node` in `src\agents\islamic_graph.py`: No docstring
- `verification_node` in `src\agents\islamic_graph.py`: No docstring
- `fact_check_node` in `src\agents\islamic_graph.py`: Cross-references every citation in the response against the actual
retrieved context. Flags hallucinated citations.
- `suggest_followups_node` in `src\agents\islamic_graph.py`: Generates 3 relevant follow-up questions based on the Q&A.
Gracefully degrades to empty list on any failure.
NOTE: This node is skipped by default to reduce latency.
It runs only if state["include_followups"] is True.
- `finalization_node` in `src\agents\islamic_graph.py`: No docstring
- `build_islamic_graph` in `src\agents\islamic_graph.py`: No docstring
- `node` in `src\agents\islamic_graph.py`: No docstring
- `node` in `src\agents\islamic_graph.py`: No docstring
- `node` in `src\agents\islamic_graph.py`: No docstring
- `node` in `src\agents\islamic_graph.py`: No docstring
- `node` in `src\agents\islamic_graph.py`: No docstring
- `node` in `src\agents\islamic_graph.py`: No docstring
- `node` in `src\agents\islamic_graph.py`: No docstring
- `node` in `src\agents\islamic_graph.py`: No docstring
- `main` in `src\agents\test_classifier.py`: No docstring
- `invoke` in `src\agents\test_classifier.py`: No docstring
- `main` in `src\agents\test_islamic_graph.py`: No docstring
- `invoke` in `src\agents\test_islamic_graph.py`: No docstring
- `health_check` in `src\api\main.py`: Health check endpoint with collection info.
- `ask_islamic` in `src\api\main.py`: Main chat endpoint.
Uses the RAG pipeline if available, otherwise falls back to curated knowledge.
- `index_document` in `src\api\main.py`: Upload and index an Islamic text document (PDF or TXT).
- `verify_citation` in `src\api\main.py`: Verify a Quran citation and return Arabic + English text.
- `translate_verse` in `src\api\main.py`: Translate verse text to Urdu or Arabic using the LLM.
- `ws_ask` in `src\api\main.py`: WebSocket endpoint for streaming answers.
- `list_api_keys` in `src\api\v1\api_keys.py`: List all API keys for the authenticated tenant.
- `create_api_key` in `src\api\v1\api_keys.py`: Create a new API key. The full key is only returned once.
- `revoke_api_key` in `src\api\v1\api_keys.py`: Revoke (deactivate) an API key.
- `ask_v1` in `src\api\v1\ask.py`: Tenant-scoped query endpoint with auth support.
- `register` in `src\api\v1\auth.py`: Register a new user with a new organization.
- `login` in `src\api\v1\auth.py`: Login with email and password.
- `refresh_token` in `src\api\v1\auth.py`: Refresh an access token using a refresh token.
- `get_me` in `src\api\v1\auth.py`: Get current user info.
- `health_check` in `src\api\v1\health.py`: Deep health check with connectivity tests.
- `get_my_tenant` in `src\api\v1\tenants.py`: Get current tenant info.
- `update_tenant` in `src\api\v1\tenants.py`: Update tenant settings (owner/admin only).
- `list_tenant_users` in `src\api\v1\tenants.py`: List all users in the tenant.
- `generate_api_key` in `src\auth\api_keys.py`: Generate a new API key.

Returns:
    Tuple of (full_key, key_hash) — full_key is shown once to user,
    key_hash is stored in the database.
- `hash_api_key` in `src\auth\api_keys.py`: Hash an API key for storage.
- `verify_api_key` in `src\auth\api_keys.py`: Verify an API key against its stored hash.
- `get_auth_context` in `src\auth\dependencies.py`: Extract and validate auth context from JWT or API key.

Returns None if no credentials are provided (for backward compatibility).
- `require_auth` in `src\auth\dependencies.py`: Require authentication. Raises 401 if not authenticated.
- `require_role` in `src\auth\dependencies.py`: Dependency factory that requires specific roles.
- `is_admin` in `src\auth\dependencies.py`: No docstring
- `is_owner` in `src\auth\dependencies.py`: No docstring
- `create_access_token` in `src\auth\jwt.py`: Create a JWT access token.
- `create_refresh_token` in `src\auth\jwt.py`: Create a JWT refresh token.
- `decode_token` in `src\auth\jwt.py`: Decode and validate a JWT token. Raises JWTError on invalid token.
- `hash_password` in `src\auth\passwords.py`: Hash a password using bcrypt.
- `verify_password` in `src\auth\passwords.py`: Verify a password against its hash.
- `get_settings` in `src\config\settings.py`: Cached settings instance.
- `allowed_origins_list` in `src\config\settings.py`: No docstring
- `is_production` in `src\config\settings.py`: No docstring
- `get_quran_splitter` in `src\core\islamic_chunker.py`: Quran verses are already atomic units.
Each ayah should remain a separate document.
- `get_hadith_splitter` in `src\core\islamic_chunker.py`: Split lengthy hadith into smaller semantic chunks.
Hadith are typically short, so we use conservative chunking.
- `get_tafsir_splitter` in `src\core\islamic_chunker.py`: Split tafsir at paragraph boundaries while preserving context.
Tafsir entries can be lengthy, so we allow larger chunks.
- `split_with_metadata` in `src\core\islamic_chunker.py`: Split documents while preserving parent metadata.
Each chunk inherits all metadata from its parent document.
- `get_store` in `src\core\islamic_vectorDB.py`: Get or create a Chroma collection.
- `index_documents` in `src\core\islamic_vectorDB.py`: Index documents into a Chroma collection.
- `retrieve_with_scores` in `src\core\islamic_vectorDB.py`: Retrieve documents with relevance scores.
Returns list of (Document, score) tuples, filtered by threshold.
tenant_id: optional filter for per-tenant collections.
- `compute_retrieval_confidence` in `src\core\islamic_vectorDB.py`: Compute overall retrieval confidence across all collections.
Based on the number and quality of retrieved results.
- `list_collections` in `src\core\islamic_vectorDB.py`: Return all available collections.
- `get_collection_count` in `src\core\islamic_vectorDB.py`: Get the number of documents in a collection.
- `test_quran_splitter` in `src\core\test_chunker.py`: No docstring
- `test_hadith_splitter` in `src\core\test_chunker.py`: No docstring
- `test_tafsir_splitter` in `src\core\test_chunker.py`: No docstring
- `main` in `src\core\test_vectorDB.py`: No docstring
- `generate_id` in `src\db\base.py`: Generate a UUID4 string for document _id.
- `now` in `src\db\base.py`: Get current UTC datetime.
- `to_doc` in `src\db\base.py`: Convert a model to a MongoDB document dict.
- `get_database` in `src\db\database.py`: Get MongoDB database instance.
- `init_db` in `src\db\database.py`: Initialize database connection and create indexes.
- `close_db` in `src\db\database.py`: Close database connection on shutdown.
- `get_db` in `src\db\database.py`: FastAPI dependency that provides a database instance.
- `is_expired` in `src\db\models\api_key.py`: No docstring
- `max_sources` in `src\db\models\tenant.py`: No docstring
- `daily_request_limit` in `src\db\models\tenant.py`: No docstring
- `is_admin` in `src\db\models\user.py`: No docstring
- `is_owner` in `src\db\models\user.py`: No docstring
- `get_db` in `src\db\session.py`: FastAPI dependency that provides a database session.
- `init_db` in `src\db\session.py`: Create all database tables.
- `dispatch` in `src\middleware\error_handling.py`: No docstring
- `dispatch` in `src\middleware\security.py`: No docstring
- `dispatch` in `src\middleware\tenant.py`: No docstring
- `get_redis` in `src\services\cache_service.py`: Get or create Redis connection.
- `cache_get` in `src\services\cache_service.py`: Get cached response by key.
- `cache_set` in `src\services\cache_service.py`: Cache a response with TTL (default 5 minutes).
- `cache_delete` in `src\services\cache_service.py`: Delete a cached response.
- `rate_limit_check` in `src\services\cache_service.py`: Check if tenant is within rate limit. Returns True if allowed.
- `close_redis` in `src\services\cache_service.py`: Close Redis connection on shutdown.
- `get_conversation` in `src\services\conversation_service.py`: Get conversation messages if it exists, is active, and belongs to tenant.
- `save_conversation` in `src\services\conversation_service.py`: Save or update a conversation.
- `create_conversation` in `src\services\conversation_service.py`: Create a new conversation.
- `get_tenant` in `src\services\tenant_service.py`: Get tenant by ID.
- `get_tenant_by_slug` in `src\services\tenant_service.py`: Get tenant by slug.
- `create_tenant` in `src\services\tenant_service.py`: Create a new tenant.
- `get_default_tenant` in `src\services\tenant_service.py`: Get or create the default tenant for backward compatibility.
- `update_tenant` in `src\services\tenant_service.py`: Update tenant settings.
- `extract_citations` in `src\utils\citation_engine.py`: Extract all citations from a response text.
Returns a list of dicts with raw, source, reference, url, verified fields.
- `format_citation_cards` in `src\utils\citation_engine.py`: Format citations into cards suitable for the frontend sidebar.
- `verify_answer_grounding` in `src\utils\citation_engine.py`: Verify that the answer is grounded in the retrieved context.

Returns:
    (is_grounded, unsupported_claims, confidence_score)
- `check_islamic_safety` in `src\utils\citation_engine.py`: Check for Islamic-specific safety concerns.
Returns a list of safety flags.
- `enforce_citations` in `src\utils\citation_engine.py`: Enhanced validation node:
- Ensures response has citations
- Verifies answer grounding
- Checks Islamic safety
- Regenerates if missing
- `cross_reference_citations` in `src\utils\citation_engine.py`: Cross-reference each citation in the response against the actual retrieved
context.  A citation is 'verified' if its key components (surah name + verse
for Quran, collection name + number for Hadith) appear in the context text.

Returns:
    (citation_verdicts, hallucination_ratio, fact_check_passed)
- `build_verse_triplets` in `src\utils\citation_engine.py`: For each Quran citation, build a triplet of {arabic, english, urdu} verse data
by extracting from the retrieved context.

Returns a list of dicts:
    {citation_raw, surah, ayah, arabic, english, urdu, needs_urdu}
- `get_ui_string` in `src\utils\translator.py`: Get a UI string in the specified language.
- `translate_text` in `src\utils\translator.py`: Translate text from source_lang to target_lang using the LLM.

Args:
    text: The text to translate
    source_lang: Source language code (en, ar, ur)
    target_lang: Target language code (en, ar, ur)
    llm: The LLM instance to use for translation

Returns:
    Translated text, or original text if translation fails or langs are the same.
- `translate_query_to_english` in `src\utils\translator.py`: Translate a user's query to English for vector search.
The vector store has English content, so non-English queries must be translated first.
- `translate_response_to_language` in `src\utils\translator.py`: Translate an English response to the user's selected language.
Preserves citations and Islamic terminology.

## Public Classes

- `Definition` in `pydevkit\pydevkit\deadcode\scanner.py`: A symbol definition that can be reported as dead code.
- `ImportBinding` in `pydevkit\pydevkit\deadcode\scanner.py`: A single import alias binding found in a source file.
- `TestQuery` in `scripts\evaluate_rag.py`: No docstring
- `RetrievalMetrics` in `scripts\evaluate_rag.py`: No docstring
- `GenerationMetrics` in `scripts\evaluate_rag.py`: No docstring
- `EvaluationResult` in `scripts\evaluate_rag.py`: No docstring
- `RAGEvaluator` in `scripts\evaluate_rag.py`: Evaluates the RAG pipeline against test queries.
- `IslamicAgentState` in `src\agents\state.py`: No docstring
- `MockLLM` in `src\agents\test_classifier.py`: Fake LLM for testing without API calls.
- `MockLLM` in `src\agents\test_islamic_graph.py`: No docstring
- `QueryRequest` in `src\api\main.py`: No docstring
- `QueryResponse` in `src\api\main.py`: No docstring
- `HealthResponse` in `src\api\main.py`: No docstring
- `TranslateVerseRequest` in `src\api\main.py`: No docstring
- `CreateAPIKeyRequest` in `src\api\v1\api_keys.py`: No docstring
- `APIKeyResponse` in `src\api\v1\api_keys.py`: No docstring
- `AskRequest` in `src\api\v1\ask.py`: No docstring
- `AskResponse` in `src\api\v1\ask.py`: No docstring
- `RegisterRequest` in `src\api\v1\auth.py`: No docstring
- `LoginRequest` in `src\api\v1\auth.py`: No docstring
- `TokenResponse` in `src\api\v1\auth.py`: No docstring
- `UserResponse` in `src\api\v1\auth.py`: No docstring
- `HealthResponse` in `src\api\v1\health.py`: No docstring
- `TenantResponse` in `src\api\v1\tenants.py`: No docstring
- `TenantUpdateRequest` in `src\api\v1\tenants.py`: No docstring
- `AuthContext` in `src\auth\dependencies.py`: Authenticated context containing user, tenant, and permissions.
- `Settings` in `src\config\settings.py`: Application settings loaded from environment variables.
- `IslamicVectorStore` in `src\core\islamic_vectorDB.py`: Centralized vector store manager for all Islamic knowledge collections.
Features:
- Thread-safe embedding with EMBED_LOCK
- MMR retrieval for diverse results
- Relevance threshold filtering
- Retrieval confidence scoring
- Multi-tenant support via tenant_id parameter
- `DocumentMixin` in `src\db\base.py`: Mixin providing common document fields and methods.
- `APIKey` in `src\db\models\api_key.py`: API key for programmatic access to the RAG API.
- `Config` in `src\db\models\api_key.py`: No docstring
- `Conversation` in `src\db\models\conversation.py`: A conversation session within a tenant.
- `ConversationMessage` in `src\db\models\conversation.py`: Individual message within a conversation.
- `Config` in `src\db\models\conversation.py`: No docstring
- `Config` in `src\db\models\conversation.py`: No docstring
- `Document` in `src\db\models\document.py`: Tracks uploaded documents and their indexing status.
- `Config` in `src\db\models\document.py`: No docstring
- `Tenant` in `src\db\models\tenant.py`: Represents an organization/tenant in the SaaS platform.
- `Config` in `src\db\models\tenant.py`: No docstring
- `UsageRecord` in `src\db\models\usage_record.py`: Records each API request for billing and analytics.
- `Config` in `src\db\models\usage_record.py`: No docstring
- `UserRole` in `src\db\models\user.py`: No docstring
- `User` in `src\db\models\user.py`: User belonging to a tenant.
- `Config` in `src\db\models\user.py`: No docstring
- `ErrorHandlingMiddleware` in `src\middleware\error_handling.py`: Format all error responses consistently.
- `SecurityHeadersMiddleware` in `src\middleware\security.py`: Add security headers to all responses.
- `TenantMiddleware` in `src\middleware\tenant.py`: Resolve tenant from Authorization header and attach to request state.

For backward compatibility, this middleware does not enforce auth —
it only populates request.state.tenant_id if credentials are present.
Enforcement happens at the endpoint level via dependencies.

## Dependencies

- `fastapi>=0.110.0`
- `uvicorn[standard]>=0.27.0`
- `python-multipart>=0.0.9`
- `websockets>=12.0`
- `pydantic>=2.0.0`
- `pydantic-settings>=2.0.0`
- `python-dotenv>=1.0.0`
- `motor>=3.0.0`
- `redis[hiredis]>=5.0.0`
- `python-jose[cryptography]>=3.3.0`
- `passlib[bcrypt]>=1.7.4`
- `langchain>=0.1.0`
- `langchain-community>=0.0.10`
- `langchain-openai>=0.0.5`
- `langchain-ollama>=0.0.2`
- `langchain-groq>=0.1.0`
- `langchain-anthropic>=0.1.0`
- `langchain-google-genai>=0.1.0`
- `langchain-mistralai>=0.1.0`
- `langchain-huggingface>=0.0.1`
- `langchain-text-splitters>=0.0.1`
- `langgraph>=0.0.20`
- `langsmith>=0.0.70`
- `chromadb>=0.4.22`
- `sentence-transformers>=2.2.2`
- `pymupdf>=1.23.0`
- `beautifulsoup4>=4.12.0`
- `pypdf>=4.0.0`
- `requests>=2.31.0`
- `httpx>=0.27.0`
- `numpy>=1.24.0`
- `pandas>=2.0.0`
- `scikit-learn>=1.3.0`
- `tqdm>=4.66.0`
- `arabic-reshaper>=3.0.0`
- `python-bidi>=0.4.2`

## Contributing

Contributions are welcome. Create a branch, add focused tests, and open a pull request.

## License

MIT
