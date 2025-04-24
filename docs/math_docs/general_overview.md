# Setup and installation

## Makefile (recommended)

Assuming [Make](https://www.gnu.org/software/make/) and a recent version of [Python3](https://www.python.org/download/releases/3.0/) is installed on your machine, the easiest method of setting up the SDK is using the terminal to invoke:
```sh
  make setup
```
This will setup and activate a Python virtual environment, installing all necessary packages as defined within ***requirements.txt***, and install an editable math-sdk module.


## Manual installation


### Create and Activate a Virtual Environment

It's recommended to use a virtual environment to manage dependencies. Using the Virtual Environment manager (_venv_), install Python version >=3.12 using:

```sh
python -m venv env
```

- **macOS/Linux**:

```sh
source env/bin/activate
```

- **Windows**:

```sh
venv \\scripts \\activate
```


### Install Dependencies

Use `pip` to install dependencies from the `requirements.txt` file:

```sh
pip install -r requirements.txt
```


### Install the Package in Editable Mode

Using the `setup.py` file, the package should be installed it in editable mode (for development purposes) with the command:

```sh
pip install -e .
```

This allows modifications to the package source code to take effect without reinstallation. 


### Verify Installation

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

## Installing Cargo (Only if using Optimization Algorithm)

If the optimization algorithm is being utilized, [**Rust**](https://www.rust-lang.org/) and **Cargo** should be [installed](https://doc.rust-lang.org/cargo/getting-started/installation.html). 

```sh
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```
