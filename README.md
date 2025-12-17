# 🤖 Doc Agent - AI-Powered API Documentation Generator

Automatically generate and maintain API documentation for FastAPI applications using AI. Perfect for CI/CD pipelines on GitLab and GitHub.

## ✨ Features

- 🔍 **Smart Code Analysis** - Automatically extracts endpoints, parameters, and models from FastAPI code
- 🤖 **AI-Powered Generation** - Uses Groq's LLMs to create comprehensive, developer-friendly documentation
- 🔄 **Intelligent Updates** - Only updates changed endpoints, preserves manual edits
- 🐳 **Docker Ready** - Fully containerized with Docker and docker-compose
- ⚡ **Fast Dependencies** - Uses `uv` for blazing-fast dependency management
- 🔗 **CI/CD Integration** - Pre-configured for GitLab CI and GitHub Actions
- 📝 **Rich CLI** - Beautiful command-line interface with progress indicators

## 🚀 Quick Start

### Using Docker (Recommended)

1. **Clone the repository**
```bash
cd /Users/ghifari/Ngoding/otherproject/doc-agent
```

2. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

3. **Run with Docker Compose**
```bash
docker-compose up
```

### Local Installation with uv

1. **Install uv** (if not already installed)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. **Install dependencies**
```bash
uv pip install -e .
```

3. **Run the CLI**
```bash
python -m src.main generate --path ./examples/sample_api --output ./docs/API.md
```

## 📖 Usage

### Generate Documentation

```bash
# Basic usage
python -m src.main generate --path /path/to/fastapi/project

# With options
python -m src.main generate \
  --path ./my-api \
  --output ./docs/API.md \
  --name "My Awesome API" \
  --api-key your_groq_key \
  --model llama-3.3-70b-versatile \
  --auto-commit
```

### Analyze Endpoints Only

```bash
python -m src.main analyze --path ./my-api --output ./analysis.json
```

### Docker Usage

```bash
# Using Docker directly
docker build -t doc-agent .
docker run -e GROQ_API_KEY=your_key \
  -v $(pwd)/my-api:/app/project:ro \
  -v $(pwd)/docs:/app/docs \
  doc-agent generate --path /app/project --output /app/docs/API.md

# Using docker-compose (edit docker-compose.yml first)
docker-compose up
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GROQ_API_KEY` | Your Groq API key (required) | - |
| `GROQ_MODEL` | Groq model to use | `llama-3.3-70b-versatile` |
| `DOC_OUTPUT_PATH` | Default output path | `./docs` |
| `GIT_DEFAULT_BRANCH` | Default Git branch | `main` |

### CLI Options

```
Options:
  --path, -p        Path to FastAPI project directory (default: .)
  --output, -o      Output path for documentation file (default: ./docs/API.md)
  --name, -n        Project name for documentation (default: API)
  --api-key, -k     Groq API key (or set GROQ_API_KEY env var)
  --model, -m       Groq model to use (default: llama-3.3-70b-versatile)
  --save-analysis   Save endpoint analysis to JSON file
  --auto-commit     Automatically commit generated documentation
```

## 🔗 CI/CD Integration

### GitLab CI

Add to your `.gitlab-ci.yml`:

```yaml
include:
  - local: 'pipelines/.gitlab-ci.yml'

variables:
  GROQ_API_KEY: ${GROQ_API_KEY}  # Set in GitLab CI/CD variables
```

Or copy the complete configuration from [`pipelines/.gitlab-ci.yml`](pipelines/.gitlab-ci.yml).

### GitHub Actions

Copy [`pipelines/github-actions.yml`](pipelines/github-actions.yml) to `.github/workflows/doc-agent.yml` in your repository.

Don't forget to add `GROQ_API_KEY` to your repository secrets!

## 🏗️ Project Structure

```
doc-agent/
├── src/
│   ├── analyzer.py       # FastAPI code analysis
│   ├── groq_service.py   # Groq API integration
│   ├── doc_manager.py    # Documentation generation/updates
│   ├── git_helper.py     # Git operations
│   └── main.py           # CLI application
├── examples/
│   └── sample_api/       # Sample FastAPI app for testing
├── pipelines/
│   ├── .gitlab-ci.yml    # GitLab CI configuration
│   └── github-actions.yml # GitHub Actions workflow
├── Dockerfile            # Docker container definition
├── docker-compose.yml    # Docker Compose configuration
├── pyproject.toml        # Project configuration (uv)
└── README.md
```

## 🧪 Testing

Test with the included sample API:

```bash
# Run the sample API
cd examples/sample_api
python main.py

# In another terminal, generate docs
python -m src.main generate \
  --path ./examples/sample_api \
  --output ./docs/sample-api.md \
  --name "Sample E-commerce API"
```

## 🎯 How It Works

1. **Code Analysis** - Scans your FastAPI codebase using Python AST to extract:
   - Endpoint paths and HTTP methods
   - Request/response models
   - Parameters (path, query, body)
   - Docstrings and descriptions
   - Tags and status codes

2. **AI Generation** - Sends extracted information to Groq API with carefully crafted prompts to generate:
   - Comprehensive endpoint documentation
   - Realistic usage examples
   - Error response documentation
   - Best practices and notes

3. **Smart Updates** - When documentation exists:
   - Detects which endpoints changed
   - Updates only modified sections
   - Preserves manual edits outside AI-managed sections
   - Maintains version history via metadata

4. **CI/CD Integration** - In your pipeline:
   - Triggers on pull requests/merge requests
   - Analyzes code changes
   - Generates/updates documentation
   - Commits changes back to branch
   - Comments on PR with summary

## 🔑 Getting a Groq API Key

1. Go to [https://console.groq.com](https://console.groq.com)
2. Sign up or log in
3. Navigate to API Keys
4. Create a new API key
5. Copy and add to your `.env` file

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

## 📄 License

MIT License - feel free to use this in your projects!

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Powered by [Groq](https://groq.com/)
- Dependency management by [uv](https://github.com/astral-sh/uv)

---
