# Algocoin


## Dependencies


* [nautilus](https://github.com/nautechsystems/nautilus_trader)
* [uv](https://docs.astral.sh/uv/)


## Setup

### Prerequisites
Install UV before starting: https://docs.astral.sh/uv/#installation

add to your .zshrc or .bashrc
```
export PATH="/home/henry/.venv/bin:$PATH"
```

### Makefile Commands

- `make activate` - Activate the virtual environment (if you choosed the home dir)
- `make install-nautilus` - Install nautilus_trader package





### Watch File Changes

```
# Install entr
sudo apt install entr

# Watch and auto-run when src/load.py changes
echo src/load.py | entr -r python src/load.py

# Watch multiple files
find . -name "*.py" | entr -r python src/load.py

# Run in virtual environment
echo src/load.py | entr -r ~/.venv/bin/python src/load.py

The -r flag restarts the command when files change.
```
