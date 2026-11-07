IMAGE ?= uptime-probe:dev
CLUSTER ?= uptime-probe

.PHONY: install lint test run image kind-up deploy smoke kind-down

install:            ## install dev dependencies
	pip install -r requirements-dev.txt

lint:               ## ruff lint + format check
	ruff check . && ruff format --check .

test:               ## unit tests
	pytest -q

run:                ## run locally on :8080
	PROBE_INITIAL_TARGETS=https://kubernetes.io uvicorn app.main:app --reload --port 8080

image:              ## build the container image
	docker build -t $(IMAGE) .

kind-up:            ## create a local Kubernetes cluster
	kind create cluster --name $(CLUSTER)

deploy: image       ## load the image into kind and install the chart
	kind load docker-image $(IMAGE) --name $(CLUSTER)
	helm upgrade --install probe charts/uptime-probe \
	  --set image.repository=uptime-probe --set image.tag=dev --set image.pullPolicy=Never --wait

smoke:              ## port-forward and hit the API
	kubectl port-forward svc/probe-uptime-probe 8080:80 & sleep 3; \
	curl -s localhost:8080/targets; curl -s localhost:8080/metrics | grep probe_target_up; kill %1

kind-down:
	kind delete cluster --name $(CLUSTER)
