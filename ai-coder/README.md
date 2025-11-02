# AI-Driven Software Engineering Assistant

## MVP Features
- Intelligent Code Review
- Automated Documentation Generation
- Bug Prediction
- Code Generation from Natural Language

## Tech Stack
- Models: Groq, Cerebras, Bytez, Azure AI (Phi-3)
- RAG: Voyage AI, Qdrant
- Backend: FastAPI (Python)
- Frontend: React (Optional)
- Extension: VSCode Extension

## Project Structure

ai-software-assistant/
- backend/           (FastAPI backend)
- vscode-extension/  (VSCode extension)
- frontend/          (React web UI - optional)
- config/           (Configuration files)
- scripts/          (Utility scripts)
- data/            (Prompts and knowledge base)
- docs/            (Documentation)
- logs/            (Application logs)

## Getting Started

1. Set up environment variables
   copy .env.example to .env

2. Install dependencies
   pip install -r requirements.txt

3. Run the development server
   python backend/main.py

## Environment Variables
- GROQ_API_KEY
- CEREBRAS_API_KEY
- BYTEZ_API_KEY
- AZURE_AI_KEY
- VOYAGE_API_KEY
- QDRANT_URL
- QDRANT_API_KEY

## Documentation
- API Documentation: docs/API.md
- Setup Guide: docs/SETUP.md
- Architecture: docs/ARCHITECTURE.md
- Deployment: docs/DEPLOYMENT.md

## License
MIT License
# AI Software Engineering Assistant

![Tests](https://github.com/sportiq1000-tech/ai-coder/workflows/Test%20Suite/badge.svg)
[![Coverage](https://codecov.io/gh/sportiq1000-tech/ai-coder/branch/main/graph/badge.svg)](https://codecov.io/gh/sportiq1000-tech/ai-coder)

Production-ready AI assistant with automated testing and CI/CD.

## Status
- ✅ Tests: Passing
- ✅ Coverage: 59%
- ✅ Security: Hardened