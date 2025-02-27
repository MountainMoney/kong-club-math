# Setup and installation

# Installing the Carrot MathEngine

This guide details the recommended process for installing the Carrot-MathEngine and all required packages using the _setuptools_ standard package.

## Step 1: Create and Activate a Virtual Environment

It's recommended to use a virtual environment to manage dependencies. Using the Virtual Environment manager (_venv_), install Python version >=3.12 using:

```sh
python3.12 -m venv env
```

Activate the virtual environment:

- **Windows**:
  ```sh
  venv \\scripts \\activate
  ```
- **macOS/Linux**:
  ```sh
  source env/bin/activate
  ```

## Step 2: Install Dependencies

Use `pip` to install dependencies from the `requirements.txt` file:

```sh
pip install -r requirements.txt
```

## Step 3: Install the Package in Editable Mode

Using the `setup.py` file, the package should be installed it in editable mode (for development purposes) with the command:

```sh
pip install -e .
```

This allows modifications to the package source code to take effect without reinstallation. 

## Step 4: Verify Installation

You can check that the package is installed by running:

```sh
pip list
```

or testing the package import in Python:

```sh
python
>>> import your_package_name
```

## Deactivating the Virtual Environment

When finished, deactivate the virtual environment with:

```sh
deactivate
```

