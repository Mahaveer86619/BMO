package services

import (
	"context"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/redis/go-redis/v9"
)

type Status struct {
	Status   string            `json:"status"`
	Services map[string]string `json:"services"`
}

type HealthService struct {
	pg    *pgxpool.Pool
	redis *redis.Client
}

func NewHealthHealthService(pg *pgxpool.Pool, redis *redis.Client) *HealthService {
	return &HealthService{pg: pg, redis: redis}
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

	return Status{
		Status:   overall,
		Services: Services,
	}
}
