ifeq ($(OS), Windows_NT)
	PYTHON = python 
else
	PYTHON = python3 
endif 

.PHONY: setup test clean


setup:
	$(PYTHON) -m venv env
	source env/bin/activate && pip install --upgrade pip
	pip install -r requirements.txt 
	pip install -e .

test:
	cd $(CURDIR)
	pytest tests/

clean:
	rm -rf env __pycache__ *.pyc