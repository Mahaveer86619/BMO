package config

import (
	"os"
	"strconv"

	"github.com/joho/godotenv"
)

type AppConfig struct {
	Port int

	DBHost string
	DBPort int
	DBUser string
	DBPass string
	DBName string

	RedisHost string
	RedisPort int
	RedisPass string
	RedisDB   int
}

var Config *AppConfig

func LoadConfig() (*AppConfig, error) {
	_ = godotenv.Load()

	Config = &AppConfig{
		Port:   GetIntValue("APP_PORT", 4040),
		DBHost: GetStringValue("DB_HOST", "localhost"),
		DBPort: GetIntValue("DB_PORT", 5432),
		DBUser: GetStringValue("DB_USER", "postgres"),
		DBPass: GetStringValue("DB_PASS", "password"),
		DBName: GetStringValue("DB_NAME", "bmo"),

		RedisHost: GetStringValue("REDIS_HOST", "localhost"),
		RedisPort: GetIntValue("REDIS_PORT", 6379),
		RedisPass: GetStringValue("REDIS_PASS", ""),
		RedisDB:   GetIntValue("REDIS_DB", 0),
	}

	return Config, nil
}

func GetStringValue(key string, defaultValue string) string {
	if os.Getenv(key) == "" {
		return defaultValue
	}
	return os.Getenv(key)
}

func GetIntValue(key string, defaultValue int) int {
	valueStr := os.Getenv(key)
	if valueStr == "" {
		return defaultValue
	}
	value, err := strconv.Atoi(valueStr)
	if err != nil {
		return defaultValue
	}
	return value
}
