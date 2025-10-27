import os
from pathlib import Path

# Define the project structure
PROJECT_NAME = "ai-software-assistant"
PROJECT_STRUCTURE = {
    "backend": {
        "api": {
            "routes": [
                "__init__.py",
                "review.py",
                "document.py",
                "bugs.py",
                "generate.py",
                "health.py"
            ],
            "middleware": [
                "__init__.py",
                "rate_limiter.py",
                "error_handler.py",
                "auth.py"
            ],
            "__init__.py": None,
        },
        "core": {
            "models": [
                "__init__.py",
                "model_router.py",
                "groq_client.py",
                "cerebras_client.py",
                "bytez_client.py",
                "azure_client.py"
            ],
            "rag": [
                "__init__.py",
                "embeddings.py",
                "vector_store.py",
                "retriever.py",
                "reranker.py",
                "chunker.py"
            ],
            "processors": [
                "__init__.py",
                "code_analyzer.py",
                "documentation_generator.py",
                "bug_predictor.py",
                "code_generator.py"
            ],
            "__init__.py": None,
        },
        "utils": [
            "__init__.py",
            "config.py",
            "logger.py",
            "cache.py",
            "validators.py",
            "prompts.py",
            "exceptions.py"
        ],
        "database": [
            "__init__.py",
            "models.py",
            "connection.py",
            "migrations.py"
        ],
        "schemas": [
            "__init__.py",
            "request_schemas.py",
            "response_schemas.py",
            "model_schemas.py"
        ],
        "tests": {
            "unit": [
                "__init__.py",
                "test_model_router.py",
                "test_processors.py",
                "test_rag.py"
            ],
            "integration": [
                "__init__.py",
                "test_api_endpoints.py",
                "test_rate_limits.py"
            ],
            "__init__.py": None,
            "conftest.py": None
        },
        "main.py": None,
        "requirements.txt": None,
        ".env.example": None,
        "Dockerfile": None,
        ".dockerignore": None
    },
    "vscode-extension": {
        "src": [
            "extension.ts",
            "commands.ts",
            "provider.ts",
            "api-client.ts",
            "config.ts",
            "utils.ts"
        ],
        "package.json": None,
        "tsconfig.json": None,
        ".vscodeignore": None,
        "README.md": None
    },
    "frontend": {
        "public": [
            "index.html",
            "favicon.ico"
        ],
        "src": {
            "components": [
                "CodeReview.jsx",
                "Documentation.jsx",
                "BugPredictor.jsx",
                "CodeGenerator.jsx",
                "Layout.jsx"
            ],
            "services": [
                "api.js",
                "auth.js",
                "websocket.js"
            ],
            "utils": [
                "constants.js",
                "helpers.js",
                "formatters.js"
            ],
            "styles": [
                "index.css",
                "components.css"
            ],
            "App.jsx": None,
            "index.js": None
        },
        "package.json": None,
        ".env.example": None
    },
    "config": [
        "nginx.conf",
        "docker-compose.yml",
        "prometheus.yml",
        ".gitignore",
        ".prettierrc",
        ".eslintrc.json"
    ],
    "scripts": [
        "deploy.sh",
        "start_dev.sh",
        "run_tests.sh",
        "setup_env.sh",
        "backup.sh"
    ],
    "data": {
        "prompts": [
            "review_prompts.json",
            "documentation_prompts.json",
            "bug_prompts.json",
            "generation_prompts.json"
        ],
        "knowledge_base": [
            "best_practices.json",
            "bug_patterns.json",
            "code_templates.json"
        ],
        ".gitkeep": None
    },
    "logs": [
        ".gitkeep"
    ],
    "docs": [
        "API.md",
        "SETUP.md",
        "ARCHITECTURE.md",
        "DEPLOYMENT.md",
        "CONTRIBUTING.md"
    ],
    "README.md": None,
    "LICENSE": None,
    ".env.example": None,
    ".gitignore": None,
    "requirements.txt": None,
    "package.json": None
}

def create_structure(base_path, structure):
    """Recursively create directory structure with empty files"""
    for name, content in structure.items():
        path = base_path / name
        
        if isinstance(content, dict):
            path.mkdir(exist_ok=True)
            create_structure(path, content)
            print(f"Created directory: {path}")
        elif isinstance(content, list):
            path.mkdir(exist_ok=True)
            for file_name in content:
                file_path = path / file_name
                file_path.touch()
                print(f"Created file: {file_path}")
        elif content is None:
            path.touch()
            print(f"Created file: {path}")

def create_gitignore_content():
    content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv
*.egg-info/
dist/
build/

# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Environment
.env
.env.local
*.env

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Logs
logs/
*.log

# Database
*.db
*.sqlite
*.sqlite3

# Cache
.cache/
*.cache

# Testing
.coverage
.pytest_cache/
htmlcov/

# Build
dist/
build/
"""
    return content

def create_readme_content():
    content = """# AI-Driven Software Engineering Assistant

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
"""
    return content

def create_env_example():
    content = """# API Keys
GROQ_API_KEY=your_groq_api_key_here
CEREBRAS_API_KEY=your_cerebras_api_key_here
BYTEZ_API_KEY=your_bytez_api_key_here
AZURE_AI_KEY=your_azure_ai_key_here
VOYAGE_API_KEY=your_voyage_api_key_here

# Vector Database
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key_here

# Cache
REDIS_URL=redis://localhost:6379

# Application
APP_ENV=development
APP_PORT=8000
LOG_LEVEL=INFO
"""
    return content

def main():
    print("=" * 60)
    print("AI-DRIVEN SOFTWARE ENGINEERING ASSISTANT - PROJECT SETUP")
    print("=" * 60)
    print(f"\nCreating project: {PROJECT_NAME}\n")
    
    base_path = Path(PROJECT_NAME)
    base_path.mkdir(exist_ok=True)
    print(f"Created base directory: {base_path}\n")
    
    print("Creating project structure...\n")
    create_structure(base_path, PROJECT_STRUCTURE)
    
    print("\nCreating configuration files...\n")
    
    gitignore_path = base_path / ".gitignore"
    gitignore_path.write_text(create_gitignore_content(), encoding='utf-8')
    print(f"Created: {gitignore_path}")
    
    readme_path = base_path / "README.md"
    readme_path.write_text(create_readme_content(), encoding='utf-8')
    print(f"Created: {readme_path}")
    
    env_example_path = base_path / ".env.example"
    env_example_path.write_text(create_env_example(), encoding='utf-8')
    print(f"Created: {env_example_path}")
    
    print("\n" + "=" * 60)
    print("PROJECT CREATED SUCCESSFULLY!")
    print("=" * 60)
    print(f"\nProject location: {base_path.absolute()}")
    print("\nNext steps:")
    print(f"  1. cd {PROJECT_NAME}")
    print("  2. Copy .env.example to .env and add your API keys")
    print("  3. Install dependencies: pip install -r requirements.txt")
    print("  4. Start development!")
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()