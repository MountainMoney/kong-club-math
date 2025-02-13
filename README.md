# zuck-math

# Python venv usage
Windows: python -m venv env 
Mac: python3 -m venv env
'python3.x -m venv env' (version specific)

Windows: env\Scripts\activate.bat
Mac: source env/bin/activate/

deactivate 
rm -r env (if virtual env is not needed)

# Setup python package module
pip install -e .
<!-- Consider using the pdm install instead (using pyproject.toml files) -->
<!-- python setup.py sdist bdist_wheel    (for distribution to PyPI)--> 
<!-- pdm build is a more modern alternaitve -->

# Package management
install packages: pip install -r requirements.txt

