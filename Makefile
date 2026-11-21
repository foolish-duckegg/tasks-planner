VERSION ?= $(shell python3 -c "import json; print(json.load(open('frontend/package.json'))['version'])")
NPM ?= npm

.PHONY: frontend build release clean

frontend:
	cd frontend && $(NPM) ci && $(NPM) run build

build: frontend

release: frontend
	rm -rf release
	mkdir -p release
	tar -czf release/tasks-planner-$(VERSION).tar.gz \
		--exclude='__pycache__' \
		--exclude='*.pyc' \
		--exclude='.venv' \
		--exclude='data' \
		--exclude='release' \
		--transform 's,^,tasks-planner-$(VERSION)/,' \
		backend cli docs README.md Makefile

clean:
	rm -rf backend/app/static release
