When adding python dependencies, do so in `pyproject.toml`. Always pin the dependencies.

The app runs in docker compose, so when adding new backend dependencies, we need to rebuild the backend container. You cannot use pip to install new dependencies, instead add them to `pyproject.toml` and rebuild the backend container.