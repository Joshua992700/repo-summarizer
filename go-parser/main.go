package main

import (
	"log"
	"net/http"
	"os"

	"github.com/gin-gonic/gin"
	"github.com/repo-summarizer/go-parser/parser"
)

// ParseRequest represents the incoming request body
type ParseRequest struct {
	URL string `json:"url" binding:"required"`
}

// ErrorResponse represents an error response
type ErrorResponse struct {
	Error string `json:"error"`
}

func main() {
	// Set Gin mode
	if os.Getenv("GIN_MODE") == "" {
		gin.SetMode(gin.ReleaseMode)
	}

	r := gin.Default()

	// Enable CORS for local development
	r.Use(corsMiddleware())

	// Health check endpoint
	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok"})
	})

	// Main parse endpoint
	r.POST("/parse", handleParse)

	// Get port from environment or use default
	port := os.Getenv("GO_PARSER_PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("🚀 Go Parser Service starting on port %s", port)
	log.Printf("📍 POST /parse - Parse a GitHub repository")
	log.Printf("📍 GET /health - Health check")

	if err := r.Run(":" + port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}

// handleParse handles the /parse endpoint
func handleParse(c *gin.Context) {
	var req ParseRequest

	// Bind and validate JSON
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{
			Error: "Invalid request: 'url' field is required",
		})
		return
	}

	// Validate GitHub URL
	if !isValidGitHubURL(req.URL) {
		c.JSON(http.StatusBadRequest, ErrorResponse{
			Error: "Invalid GitHub URL. Please provide a valid GitHub repository URL.",
		})
		return
	}

	log.Printf("📦 Parsing repository: %s", req.URL)

	// Clone and parse the repository
	repoData, err := parser.CloneAndParse(req.URL)
	if err != nil {
		log.Printf("❌ Error parsing repository: %v", err)
		c.JSON(http.StatusInternalServerError, ErrorResponse{
			Error: "Failed to clone/parse repository: " + err.Error(),
		})
		return
	}

	log.Printf("✅ Successfully parsed %d files from %s", len(repoData.Files), repoData.RepoName)

	c.JSON(http.StatusOK, repoData)
}

// isValidGitHubURL performs basic validation of GitHub URLs
func isValidGitHubURL(url string) bool {
	// Accept various GitHub URL formats
	validPrefixes := []string{
		"https://github.com/",
		"http://github.com/",
		"git@github.com:",
		"https://www.github.com/",
	}

	for _, prefix := range validPrefixes {
		if len(url) > len(prefix) && url[:len(prefix)] == prefix {
			return true
		}
	}
	return false
}

// corsMiddleware adds CORS headers for local development
func corsMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Content-Type, Authorization")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}

		c.Next()
	}
}
