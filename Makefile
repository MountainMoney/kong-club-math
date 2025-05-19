ifeq ($(OS), Windows_NT)
	PYTHON = python 
else
	PYTHON = python3 
endif 

.PHONY: setup test clean virtual activate pipInstall packInstall 


virtual:
	$(PYTHON) -m venv env 
	
activate: virtual
	./env/bin/pip install --upgrade pip

pipInstall: activate
	./env/bin/pip install -r requirements.txt 

packInstall: pipInstall
	./env/bin/pip install -e .

setup: packInstall

test:
	cd $(CURDIR)
	pytest tests/

clean:
	rm -rf env __pycache__ *.pyc