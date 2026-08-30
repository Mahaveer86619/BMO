# Standalone Go-only image — used by docker-compose.multi.yml, where server,
# brain, and Ollama are three separate containers/images instead of one
# supervised monolith. For the single-image setup see ../Dockerfile.

FROM golang:alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY cmd ./cmd
COPY internal ./internal

RUN CGO_ENABLED=0 GOOS=linux go build -o bmo-server ./cmd/main.go

FROM alpine:latest

WORKDIR /app

RUN apk --no-cache add ca-certificates tzdata

COPY --from=builder /app/bmo-server .

EXPOSE 4040

CMD ["./bmo-server"]
