package web

import (
	"strconv"

	"github.com/Mahaveer86619/BMO/internal/config"
	"github.com/Mahaveer86619/BMO/internal/enums"
	"github.com/Mahaveer86619/BMO/internal/handlers"
	"github.com/Mahaveer86619/BMO/internal/services"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/labstack/echo/v4"
	"github.com/labstack/echo/v4/middleware"
	"github.com/redis/go-redis/v9"
)

type Server struct {
	AppConfig *config.AppConfig
	Router    *echo.Echo
	PG        *pgxpool.Pool
	Redis     *redis.Client
}

func NewServer(appConfig *config.AppConfig, pg *pgxpool.Pool, redisClient *redis.Client) *Server {
	return &Server{
		AppConfig: appConfig,
		Router:    echo.New(),
		PG:        pg,
		Redis:     redisClient,
	}
}

func (s *Server) Start() error {
	s.registerServicesAndHandlers()

	s.Router.Use(middleware.RequestLogger())
	s.Router.Use(middleware.Recover())
	s.Router.Use(middleware.Secure())
	s.Router.Use(middleware.Gzip())
	s.Router.Use(middleware.CORS())

	addr := ":" + strconv.Itoa(s.AppConfig.Port)

	return s.Router.Start(addr)
}

func (s *Server) registerServicesAndHandlers() {
	// Services
	healthService := services.NewHealthHealthService(s.PG, s.Redis)

	// API groups
	apiGroup := s.Router.Group(enums.ApiGroupV1.String())

	// Handlers
	handlers.NewHealthHandler(apiGroup, healthService)
}
