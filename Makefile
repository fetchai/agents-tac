clean: clean-build clean-pyc clean-test

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -fr {} +

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test:
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .hypothesis
	rm -fr .pytest_cache
	rm -fr .mypy_cache/
	find . -name 'log.txt' -exec rm -fr {} +
	find . -name 'log.*.txt' -exec rm -fr {} +

lint:
	black sandbox scripts setup.py simulation/v1 tac templates tests
	flake8 sandbox scripts setup.py simulation/v1 tac templates tests --exclude=tac/gui/static,tac/gui/templates,.md,tac/*_pb2.py,tac/gui/.visdom_env,tac/__init__.py,scripts/oef/launch.py --ignore=E501,E701,W503

static:
	mypy sandbox scripts setup.py simulation/v1 tac templates tests --config-file mypy.ini

test-all:
	tox

dist: clean
	python setup.py sdist
	python setup.py bdist_wheel
	ls -l dist

install: clean
	python3 setup.py install

.PHONY: new_env
new_env: clean
	if [ "$v" == "" ];\
	then\
		pipenv --rm;\
		pipenv --python 3.7;\
		echo "Enter clean virtual environment now: 'pipenv shell'.";\
	else\
		echo "In a virtual environment! Exit first: 'exit'.";\
	fi

.PHONY: install_env
install_env:
	pipenv install --dev
	pip install -e .
