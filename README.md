# Carrot Engine Installation

# Open and read documentation

Documentation is written as Markdown files with the `docs/` folder, using the `MkDocs` package. When the repositiory is publicly avaliable documentation will be on GitHub Pages. For the meantime, they can be read through a *localhost*.
```sh
 mkdocs serve
```

# Python venv usage
Windows: python -m venv env 
Mac: python3 -m venv env

'python3.12 -m venv env' (version specific)

Windows: env\Scripts\activate.bat
Mac: source env/bin/activate/


# Package management
install packages: pip install -r requirements.txt


# Setup python package module
pip install -e .


# Removing instancres

deactivate 

rm -r env (if virtual env is not needed)



