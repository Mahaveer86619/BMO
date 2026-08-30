// Package aiclient talks to the Python AI service (server/ai) over localhost.
// Both processes run in the same container, supervised together — see
// server/supervisord.conf and server/Dockerfile. The AI service is never
// reachable from outside the container; this client is its only caller.
package aiclient

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/Mahaveer86619/BMO/internal/config"
)

type Client struct {
	baseURL string
	http    *http.Client
}

func New(cfg *config.AppConfig) *Client {
	return &Client{
		baseURL: fmt.Sprintf("http://%s:%d", cfg.AIHost, cfg.AIPort),
		http:    &http.Client{Timeout: 30 * time.Second},
	}
}

type ChatMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type ChatRequest struct {
	Messages []ChatMessage `json:"messages"`
	Tier     string        `json:"tier,omitempty"`
}

type ChatResponse struct {
	Reply string `json:"reply"`
	Tier  string `json:"tier"`
}

type StatusResponse struct {
	ComputeMode   string `json:"compute_mode"`
	CloudEnabled  bool   `json:"cloud_enabled"`
	OllamaBaseURL string `json:"ollama_base_url"`
}

func (c *Client) Health(ctx context.Context) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.baseURL+"/internal/health", nil)
	if err != nil {
		return err
	}

	resp, err := c.http.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("ai service unhealthy: status %d", resp.StatusCode)
	}
	return nil
}

func (c *Client) Status(ctx context.Context) (*StatusResponse, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.baseURL+"/internal/status", nil)
	if err != nil {
		return nil, err
	}

	resp, err := c.http.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("ai service status check failed: status %d", resp.StatusCode)
	}

	var out StatusResponse
	if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
		return nil, err
	}
	return &out, nil
}

func (c *Client) Chat(ctx context.Context, req ChatRequest) (*ChatResponse, error) {
	body, err := json.Marshal(req)
	if err != nil {
		return nil, err
	}

	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+"/internal/chat", bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	httpReq.Header.Set("Content-Type", "application/json")

	resp, err := c.http.Do(httpReq)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		errBody, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("ai service chat failed: status %d: %s", resp.StatusCode, string(errBody))
	}

	var out ChatResponse
	if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
		return nil, err
	}
	return &out, nil
}
