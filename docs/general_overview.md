# Setup and installation

# Installing a Python Package

This guide explains how to install a Python package using a `requirements.txt` file, set up a virtual environment, and install a package in editable mode.

## Step 1: Create and Activate a Virtual Environment

It's recommended to use a virtual environment to manage dependencies.

```sh
python -m venv venv
```

Activate the virtual environment:

- **Windows**:
  ```sh
  venv \scripts \activate
  ```
- **macOS/Linux**:
  ```sh
  source venv/bin/activate
  ```

## Step 2: Install Dependencies

Use `pip` to install dependencies from the `requirements.txt` file:

```sh
pip install -r requirements.txt
```

## Step 3: Install the Package in Editable Mode

If the package contains a `setup.py` and you want to install it in editable mode (for development purposes), run:

```sh
pip install -e .
```

This allows modifications to the package source code to take effect without reinstalling it.

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

