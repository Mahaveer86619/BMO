package handlers

import (
	"net/http"

	"github.com/Mahaveer86619/BMO/internal/services"
	"github.com/labstack/echo/v4"
)

type HealthHandler struct {
	service *services.HealthService
}

func NewHealthHandler(g *echo.Group, service *services.HealthService) *HealthHandler {
	h := &HealthHandler{service: service}

	g.GET("/health", h.HealthCheck)

	return h
}

func (h *HealthHandler) HealthCheck(c echo.Context) error {
	status := h.service.Check(c.Request().Context())

	code := http.StatusOK
	if status.Status != "healthy" {
		code = http.StatusServiceUnavailable
	}

	return c.JSON(code, status)
}
