# ==========================================
# Stage 1: Build the Go binary
# ==========================================
FROM golang:alpine AS builder

# Set the working directory inside the container
WORKDIR /app

# Copy the dependency files first to leverage Docker layer caching
COPY go.mod go.sum ./
RUN go mod download

# Copy the rest of the application source code
COPY . .

# Build the binary
# CGO_ENABLED=0 ensures a static binary, which is safer and more portable
# GOOS=linux targets the correct operating system for the runner stage
RUN CGO_ENABLED=0 GOOS=linux go build -o bmo-server ./cmd/main.go

# ==========================================
# Stage 2: Create the minimal runner image
# ==========================================
FROM alpine:latest

WORKDIR /app

# Install root certificates (required if your server makes HTTPS calls) and tzdata for timezones
RUN apk --no-cache add ca-certificates tzdata

# Copy only the compiled binary from the builder stage
COPY --from=builder /app/bmo-server .

# Expose the default port your app uses
EXPOSE 4040

# Run the executable
CMD ["./bmo-server"]
