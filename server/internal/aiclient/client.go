// Package aiclient talks to the Python "brain" service (../../brain) over
// localhost. Both processes run in the same container, supervised together —
// see server/supervisord.conf and server/Dockerfile. brain is never reachable
// from outside the container; this client is its only caller.
package aiclient

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
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

type ChatResponse struct {
	Input  string `json:"input"`
	Reply  string `json:"reply"`
	Source string `json:"source"`
}

// ReadyStatus mirrors brain's app/core/state.py Status.as_dict() — status is
// "loading" | "ready" | "error", loaded lists which models have finished
// warming up (whisper, piper/xtts/kokoro/cosyvoice, fillers).
type ReadyStatus struct {
	Status string   `json:"status"`
	Loaded []string `json:"loaded"`
	Error  string   `json:"error,omitempty"`
}

// Health is brain's liveness check — GET /health, always 200 if the process
// is up at all, even before models finish loading. Use Ready for "can this
// actually serve a request right now".
func (c *Client) Health(ctx context.Context) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.baseURL+"/health", nil)
	if err != nil {
		return err
	}

	resp, err := c.http.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("brain unhealthy: status %d", resp.StatusCode)
	}
	return nil
}

// Ready is brain's readiness check — GET /ready — 503 while Whisper/TTS/fillers
// are still loading (can take minutes on first boot, longer if XTTS has to
// download ~1.8GB), 200 once everything is warm.
func (c *Client) Ready(ctx context.Context) (*ReadyStatus, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.baseURL+"/ready", nil)
	if err != nil {
		return nil, err
	}

	resp, err := c.http.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var out ReadyStatus
	if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
		return nil, err
	}

	// 503 is a normal "still loading" response, not a transport error —
	// the decoded body already says so via Status; only a genuinely
	// unexpected code is an error here.
	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusServiceUnavailable {
		return &out, fmt.Errorf("brain ready-check failed: status %d", resp.StatusCode)
	}
	return &out, nil
}

// Chat calls brain's text-only debug endpoint — POST /api/v1/chat.
// No STT/TTS involved; this exercises the NLP/command layer + Ollama only.
func (c *Client) Chat(ctx context.Context, text string) (*ChatResponse, error) {
	body, err := json.Marshal(map[string]string{"text": text})
	if err != nil {
		return nil, err
	}

	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+"/api/v1/chat", bytes.NewReader(body))
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
		return nil, fmt.Errorf("brain chat failed: status %d: %s", resp.StatusCode, string(errBody))
	}

	var out ChatResponse
	if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
		return nil, err
	}
	return &out, nil
}

// Talk calls brain's one-shot audio endpoint — POST /api/v1/talk.
// audioWAV is a full WAV file; the response body is a WAV file too.
// This is the HTTP fallback — the real streaming path once /ws/talk is
// fronted by Go is WebSocket, not this.
func (c *Client) Talk(ctx context.Context, audioWAV []byte) ([]byte, error) {
	var buf bytes.Buffer
	writer := multipart.NewWriter(&buf)

	part, err := writer.CreateFormFile("audio", "audio.wav")
	if err != nil {
		return nil, err
	}
	if _, err := part.Write(audioWAV); err != nil {
		return nil, err
	}
	if err := writer.Close(); err != nil {
		return nil, err
	}

	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+"/api/v1/talk", &buf)
	if err != nil {
		return nil, err
	}
	httpReq.Header.Set("Content-Type", writer.FormDataContentType())

	resp, err := c.http.Do(httpReq)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		errBody, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("brain talk failed: status %d: %s", resp.StatusCode, string(errBody))
	}

	return io.ReadAll(resp.Body)
}
