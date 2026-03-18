package main

import (
	"context"
	"net/http"
	"os/signal"
	"syscall"
	"time"

	"github.com/Mahaveer86619/BMO/internal/config"
	"github.com/Mahaveer86619/BMO/internal/db"
	"github.com/Mahaveer86619/BMO/internal/web"
	"github.com/charmbracelet/log"
)

func main() {
	log.Info("BMO server warming up...")

	cfg, err := config.LoadConfig()
	if err != nil {
		log.Fatal("failed to load config", "error", err)
	}

	ctx := context.Background()

	pgPool, err := db.NewPostgresPool(ctx, cfg)
	if err != nil {
		log.Fatal("failed to connect to postgres", "error", err)
	}
	defer pgPool.Close()
	log.Info("connected to postgres")

	redisClient, err := db.NewRedisClient(ctx, cfg)
	if err != nil {
		log.Fatal("failed to connect to redis", "error", err)
	}
	defer redisClient.Close()
	log.Info("connected to redis")

	server := web.NewServer(cfg, pgPool, redisClient)

	// Graceful shutdown
	shutdownCtx, stop := signal.NotifyContext(ctx, syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	go func() {
		if err := server.Start(); err != nil && err != http.ErrServerClosed {
			log.Fatal("server crashed", "error", err)
		}
	}()

	log.Info("BMO server started successfully")

	<-shutdownCtx.Done()
	log.Info("shutting down...")

	timeoutCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := server.Router.Shutdown(timeoutCtx); err != nil {
		log.Fatal("forced shutdown", "error", err)
	}

	log.Info("BMO server shut down gracefully")
}
