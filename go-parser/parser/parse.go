package parser

import (
	"io"
	"path/filepath"
	"strings"
	"sync"

	"github.com/go-git/go-billy/v5"
	"github.com/go-git/go-billy/v5/memfs"
	"github.com/go-git/go-git/v5"
	"github.com/go-git/go-git/v5/storage/memory"
)

// FileContent represents a single file with its path and content
type FileContent struct {
	Path    string `json:"path"`
	Content string `json:"content"`
}

// RepoData represents the parsed repository data
type RepoData struct {
	RepoName string        `json:"repo_name"`
	Files    []FileContent `json:"files"`
	Error    string        `json:"error,omitempty"`
}

// Directories and files to skip during parsing
var skipDirs = map[string]bool{
	".git":         true,
	"node_modules": true,
	"build":        true,
	"dist":         true,
	"vendor":       true,
	"__pycache__":  true,
	".venv":        true,
	"venv":         true,
	".idea":        true,
	".vscode":      true,
	"target":       true, // Rust/Java build dir
	"bin":          true,
	"obj":          true,
	".next":        true, // Next.js
	"coverage":     true,
}

// Binary file extensions to skip
var skipExtensions = map[string]bool{
	".exe": true, ".dll": true, ".so": true, ".dylib": true,
	".png": true, ".jpg": true, ".jpeg": true, ".gif": true, ".ico": true, ".svg": true,
	".pdf": true, ".doc": true, ".docx": true,
	".zip": true, ".tar": true, ".gz": true, ".rar": true,
	".mp3": true, ".mp4": true, ".avi": true, ".mov": true,
	".ttf": true, ".woff": true, ".woff2": true, ".eot": true,
	".pyc": true, ".pyo": true,
	".class": true,
	".o": true, ".a": true,
	".lock": true, // Often large and not useful for summarization
}

// MaxFileSize is the maximum file size to read (1MB)
const MaxFileSize = 1 * 1024 * 1024

// ExtractRepoName extracts the repository name from a GitHub URL
func ExtractRepoName(url string) string {
	// Handle various GitHub URL formats
	url = strings.TrimSuffix(url, ".git")
	url = strings.TrimSuffix(url, "/")
	
	parts := strings.Split(url, "/")
	if len(parts) > 0 {
		return parts[len(parts)-1]
	}
	return "unknown"
}

// CloneAndParse clones a repository in-memory and parses all files
func CloneAndParse(repoURL string) (*RepoData, error) {
	// Create in-memory filesystem and storage
	fs := memfs.New()
	storer := memory.NewStorage()

	// Clone the repository
	_, err := git.Clone(storer, fs, &git.CloneOptions{
		URL:          repoURL,
		Depth:        1, // Shallow clone for speed
		SingleBranch: true,
	})
	if err != nil {
		return &RepoData{
			RepoName: ExtractRepoName(repoURL),
			Error:    err.Error(),
		}, err
	}

	// Parse files concurrently
	files := parseFilesRecursive(fs, "/")

	return &RepoData{
		RepoName: ExtractRepoName(repoURL),
		Files:    files,
	}, nil
}

// parseFilesRecursive walks the filesystem and reads all files concurrently
func parseFilesRecursive(fs billy.Filesystem, root string) []FileContent {
	var (
		files   []FileContent
		mutex   sync.Mutex
		wg      sync.WaitGroup
		fileCh  = make(chan string, 100)
	)

	// Worker pool for concurrent file reading
	numWorkers := 10
	for i := 0; i < numWorkers; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for path := range fileCh {
				content, err := readFile(fs, path)
				if err == nil && content != "" {
					mutex.Lock()
					files = append(files, FileContent{
						Path:    strings.TrimPrefix(path, "/"),
						Content: content,
					})
					mutex.Unlock()
				}
			}
		}()
	}

	// Walk the directory tree
	walkDir(fs, root, fileCh)
	close(fileCh)
	wg.Wait()

	return files
}

// walkDir recursively walks directories and sends file paths to the channel
func walkDir(fs billy.Filesystem, dir string, fileCh chan<- string) {
	entries, err := fs.ReadDir(dir)
	if err != nil {
		return
	}

	for _, entry := range entries {
		name := entry.Name()
		path := filepath.Join(dir, name)

		if entry.IsDir() {
			// Skip excluded directories
			if skipDirs[name] {
				continue
			}
			walkDir(fs, path, fileCh)
		} else {
			// Skip binary and excluded files
			ext := strings.ToLower(filepath.Ext(name))
			if skipExtensions[ext] {
				continue
			}
			// Skip hidden files (except important ones)
			if strings.HasPrefix(name, ".") && !isImportantDotFile(name) {
				continue
			}
			fileCh <- path
		}
	}
}

// isImportantDotFile returns true for dotfiles that are useful for summarization
func isImportantDotFile(name string) bool {
	important := map[string]bool{
		".gitignore":    true,
		".env.example":  true,
		".dockerignore": true,
		".eslintrc":     true,
		".prettierrc":   true,
		".babelrc":      true,
		".editorconfig": true,
	}
	return important[name] || strings.HasPrefix(name, ".eslintrc") || strings.HasPrefix(name, ".prettierrc")
}

// readFile reads a file from the in-memory filesystem
func readFile(fs billy.Filesystem, path string) (string, error) {
	info, err := fs.Stat(path)
	if err != nil {
		return "", err
	}

	// Skip files that are too large
	if info.Size() > MaxFileSize {
		return "", nil
	}

	file, err := fs.Open(path)
	if err != nil {
		return "", err
	}
	defer file.Close()

	content, err := io.ReadAll(file)
	if err != nil {
		return "", err
	}

	// Skip binary content (simple heuristic: check for null bytes)
	if isBinaryContent(content) {
		return "", nil
	}

	return string(content), nil
}

// isBinaryContent checks if content appears to be binary
func isBinaryContent(content []byte) bool {
	// Check first 512 bytes for null bytes (common in binary files)
	checkLen := len(content)
	if checkLen > 512 {
		checkLen = 512
	}
	for i := 0; i < checkLen; i++ {
		if content[i] == 0 {
			return true
		}
	}
	return false
}
