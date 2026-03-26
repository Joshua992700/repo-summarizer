# Repo Summarizer

A readymade tool that summarizes GitHub repositories using Go for fast parsing and Python for AI-powered summarization.

## Architecture

```
repo-summarizer/
├── go-parser/           # Go service - clones and parses repos
│   ├── main.go          # REST API endpoint
│   ├── parser/parse.go  # File parsing logic
│   ├── go.mod
│   └── go.sum
├── python-backend/      # Python CLI + AI summarization
│   ├── main.py          # CLI entry point
│   ├── api_client.py    # Calls Go parser API
│   ├── summarizer.py    # AI/heuristic summarization
│   ├── utils.py         # Helper functions
│   └── requirements.txt
├── README.md
└── .gitignore
```

## Quick Start

### 1. Start the Go Parser Service

```bash
cd go-parser
go mod tidy
go run main.go
```

The Go service will start on `http://localhost:8080`.

### 2. Run the Python CLI

```bash
cd python-backend
pip install -r requirements.txt
python main.py
```

Enter a GitHub repo URL when prompted and get an instant summary!

## Features

- **Fast Parsing**: Go service uses goroutines for concurrent file reading
- **Smart Filtering**: Automatically skips `.git`, `node_modules`, `build`, `dist`
- **Tech Stack Detection**: Identifies languages and frameworks from config files
- **AI Summarization**: Uses OpenAI GPT (with fallback heuristics)
- **Rich CLI Output**: Beautiful terminal formatting with `rich`
- **In-Memory Operations**: No disk writes, all processing in memory

## API Reference

### Go Parser API

**POST /parse**

Request:
```json
{
  "url": "https://github.com/user/repo"
}
```

Response:
```json
{
  "repo_name": "repo",
  "files": [
    {"path": "README.md", "content": "..."},
    {"path": "src/main.py", "content": "..."}
  ]
}
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GO_PARSER_PORT` | Go service port | `8080` |
| `GO_PARSER_URL` | Go parser API URL | `http://localhost:8080` |
| `OPENAI_API_KEY` | OpenAI API key for AI summaries | None (uses heuristics) |

## Tech Stack

- **Go**: gin-gonic, go-git
- **Python**: requests, rich, openai

## License

MIT - Built for hackathons!
