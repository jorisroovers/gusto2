When adding python dependencies, do so in `pyproject.toml`. Always pin the dependencies.

The app runs in docker compose, so when adding new backend dependencies, we need to rebuild the backend container. You cannot use pip to install new dependencies, instead add them to `pyproject.toml` and rebuild the backend container.

You do not need to restart the app when making python code changes, the app is running in developer mode by default which will do hot reloading on code changes.

In case there's still a need for application restart, like when adding new dependencies, you can run the `just dev` command. Note that this does **NOT** run the containers daemon mode, so this command won't finish but will be displaying the logs of the app.