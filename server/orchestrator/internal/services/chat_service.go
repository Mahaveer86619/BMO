package services

import (
	"context"

	"github.com/Mahaveer86619/BMO/internal/aiclient"
)

// ChatService backs POST /api/v1/chat — text in, text out, the debug/test
// endpoint. Forwards straight to brain's own /api/v1/chat, which exercises
// the NLP/command layer + Ollama without any audio involved.
type ChatService struct {
	ai *aiclient.Client
}

func NewChatService(ai *aiclient.Client) *ChatService {
	return &ChatService{ai: ai}
}

func (s *ChatService) Chat(ctx context.Context, text string) (*aiclient.ChatResponse, error) {
	return s.ai.Chat(ctx, text)
}
