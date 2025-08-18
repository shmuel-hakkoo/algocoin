.PHONY: activate


# Install UV before [https://docs.astral.sh/uv/#installation]

activate:
	@zsh -c "source ~/.venv/bin/activate && exec zsh"

install-nautilus:
	uv pip install -U nautilus_trader --index-url=https://packages.nautechsystems.io/simple


jupyter:
	docker run -p 8888:8888 ghcr.io/nautechsystems/jupyterlab:nightly

