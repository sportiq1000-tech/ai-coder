# Documentation: New Embeddings Strategy

**Project:** AI Software Engineering Assistant  
**Date:** January 2025  

## 1. Overview

This document outlines the migration from OpenAI's `text-embedding-ada-002` model to a new, more efficient, multi-provider embeddings strategy.

### Goals
- ✅ **Reduce Cost**: Eliminate API costs for primary usage.
- ✅ **Improve Efficiency**: Optimize for 4GB RAM laptops.
- ✅ **Increase Reliability**: Implement automatic fallback.
- ✅ **Maintain Quality**: Use high-quality, code-aware models.
- ✅ **Simplify Setup**: Remove API key requirement for primary use.

## 2. New Architecture

The new system uses a `SmartEmbedder` to orchestrate multiple embedding providers in a specific fallback order.

### Fallback Priority
1. 🥇 **Jina AI (`jina-embeddings-v2-base-en`)**
   - **Why?** 10M free tokens, no API key, no rate limits.
   - **Dimensions:** 768

2. 🥈 **HuggingFace Inference API (`sentence-transformers/all-MiniLM-L6-v2`)**
   - **Why?** Generous free tier (30K requests/month).
   - **Dimensions:** 384 (padded to 768)
   - **Requires:** `HF_API_KEY`

3. 🥉 **Google Gemini (`models/text-embedding-004`)**
   - **Why?** Unlimited free tier (with rate limits).
   - **Dimensions:** 768
   - **Requires:** `GEMINI_API_KEY`

4. 🏅 **Local Sentence Transformers (`paraphrase-MiniLM-L3-v2`)**
   - **Why?** Always works, even offline.
   - **Dimensions:** 384 (padded to 768)
   - **RAM Usage:** ~500MB when loaded.

## 3. Configuration

All settings are managed in `backend/.env`.

### Primary Settings
- `EMBEDDING_PROVIDER`: Set to `smart` to use the fallback chain.
- `EMBEDDING_DIMENSION`: Changed from **1536** to **768**.

### API Keys (Optional)
- `HF_API_KEY`: For HuggingFace fallback.
- `GEMINI_API_KEY`: For Gemini fallback.

### Cache Settings
- `EMBEDDING_CACHE_ENABLED`: Enable/disable caching.
- `EMBEDDING_CACHE_COMPRESSION`: Enable/disable msgpack compression.
- `EMBEDDING_CACHE_TTL_DAYS`: How long to keep cached embeddings (default: 30).
- `EMBEDDING_CACHE_MAX_SIZE_GB`: Max cache size (default: 1.0).

## 4. Migration Steps

### Step 1: Update Dependencies
Run `pip install -r backend/requirements.txt` to install the new libraries (`sentence-transformers`, `torch`, `google-generativeai`, etc.) and remove old ones (`openai`, `tiktoken`).

### Step 2: Update Qdrant Collections
Since the embedding dimension has changed from **1536 to 768**, you must **delete your old Qdrant data**.

1. **Stop Docker Compose:**
   ```bash
   docker-compose -f docker-compose.rag.yml down