install:
	pip install --upgrade pip
	pip install -r requirements.txt

install-dev:
	pip install --upgrade pip
	pip install -r requirements.dev.txt
	pre-commit install

format:
	black .

manual-release:
	python -m build
	python -m twine upload dist/*
