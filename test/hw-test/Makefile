.PHONY: build deploy clean

build:
	@echo "Building the project..."
	sudo docker build -t pico-sdk -f infra/Dockerfile .
	sudo docker run --rm -v $(PWD):/project pico-sdk

deploy:
	@echo "Deploying the project..."
	./scripts/deploy.sh

clean:
	@echo "Cleaning build artifacts..."
	sudo rm -rf $(PWD)/build