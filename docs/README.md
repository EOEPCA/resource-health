# Documentation

Documentation from here is published at https://eoepca.readthedocs.io/projects/resource-health/en/latest/.

## Development

To set this up locally, follow the steps:

1. Create a Python virtual environment

    ```sh
    python3 -m venv .venv
    ```

2. Activate the virtual environment

    ```sh
    source .venv/bin/activate
    ```

3. Install the dependencies

    ```sh
    pip install -r requirements.txt
    ```

4. Build the documentation

    ```sh
    mkdocs serve -f ../mkdocs.yml
    ```

5. Open http://127.0.0.1:8000 to view the documentation
