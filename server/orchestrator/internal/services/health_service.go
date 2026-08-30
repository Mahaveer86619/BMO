package services

import (
	"context"
	"time"

	"github.com/Mahaveer86619/BMO/internal/aiclient"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
)

type Status struct {
	Status   string            `json:"status"`
	Services map[string]string `json:"services"`
	// Loaded lists which of brain's models have finished warming up
	// (whisper, piper/xtts/kokoro/cosyvoice, fillers) — empty until brain
	// reports "ready". See aiclient.ReadyStatus.
	Loaded []string `json:"loaded,omitempty"`
	// UptimeSeconds is the orchestrator process's own uptime — the Pico
	// polls this to show alongside its own uptime on the OLED.
	UptimeSeconds int64 `json:"uptime_seconds"`
}

type HealthService struct {
	pg        *pgxpool.Pool
	redis     *redis.Client
	ai        *aiclient.Client
	startTime time.Time
}

func NewHealthHealthService(pg *pgxpool.Pool, redis *redis.Client, ai *aiclient.Client, startTime time.Time) *HealthService {
	return &HealthService{pg: pg, redis: redis, ai: ai, startTime: startTime}
}

func (s *HealthService) Check(ctx context.Context) Status {
	Services := make(map[string]string)
	overall := "healthy"

	if err := s.pg.Ping(ctx); err != nil {
		Services["postgres"] = "unhealthy"
		overall = "unhealthy"
	} else {
		Services["postgres"] = "healthy"
	}

	if err := s.redis.Ping(ctx).Err(); err != nil {
		Services["redis"] = "unhealthy"
		overall = "unhealthy"
	} else {
		Services["redis"] = "healthy"
	}

	// brain/'s /health is mere liveness (200 even while models are still
	// loading) — /ready is the meaningful check for "can it actually serve
	// a request", so that's what /api/v1/health reports as "brain" here.
	var loaded []string
	ready, err := s.ai.Ready(ctx)
	switch {
	case err != nil:
		Services["brain"] = "unreachable"
		overall = "unhealthy"
	case ready.Status != "ready":
		Services["brain"] = ready.Status // "loading" or "error"
		overall = "unhealthy"
	default:
		Services["brain"] = "healthy"
		loaded = ready.Loaded
	}

	return Status{
		Status:        overall,
		Services:      Services,
		Loaded:        loaded,
		UptimeSeconds: int64(time.Since(s.startTime).Seconds()),
	}
}
