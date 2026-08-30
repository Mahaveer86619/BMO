package handlers

import (
	"net/http"

	"github.com/Mahaveer86619/BMO/internal/services"
	"github.com/labstack/echo/v4"
)

type ChatHandler struct {
	service *services.ChatService
}

type chatRequestBody struct {
	Text string `json:"text"`
	Tier string `json:"tier,omitempty"`
}

func NewChatHandler(g *echo.Group, service *services.ChatService) *ChatHandler {
	h := &ChatHandler{service: service}

	g.POST("/chat", h.Chat)

	return h
}

func (h *ChatHandler) Chat(c echo.Context) error {
	var body chatRequestBody
	if err := c.Bind(&body); err != nil {
		return c.JSON(http.StatusBadRequest, echo.Map{"error": "invalid request body"})
	}
	if body.Text == "" {
		return c.JSON(http.StatusBadRequest, echo.Map{"error": "text is required"})
	}

	tier := body.Tier
	if tier == "" {
		tier = "fast"
	}

	reply, err := h.service.Chat(c.Request().Context(), body.Text, tier)
	if err != nil {
		return c.JSON(http.StatusBadGateway, echo.Map{"error": err.Error()})
	}

	return c.JSON(http.StatusOK, echo.Map{"reply": reply})
}
