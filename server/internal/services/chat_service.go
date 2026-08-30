package services

import (
	"context"

	"github.com/Mahaveer86619/BMO/internal/aiclient"
)

// ChatService backs POST /api/v1/chat — text in, text out, the debug/test
// endpoint from notes/Software.md's "Current Endpoints" table. It forwards
// straight to the AI service's fast tier; the NLP fast-path and full
// STT->router->memory->TTS pipeline described in the notes don't exist yet.
type ChatService struct {
	ai *aiclient.Client
}

func NewChatService(ai *aiclient.Client) *ChatService {
	return &ChatService{ai: ai}
}

func (s *ChatService) Chat(ctx context.Context, text string, tier string) (string, error) {
	resp, err := s.ai.Chat(ctx, aiclient.ChatRequest{
		Messages: []aiclient.ChatMessage{{Role: "user", Content: text}},
		Tier:     tier,
	})
	if err != nil {
		return "", err
	}
	return resp.Reply, nil
}
