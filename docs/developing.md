# Developing
Use [pipenv](https://github.com/pypa/pipenv) to setup the local environment:

```sh
pipenv install --dev 
```

## Running tests

```sh
pipenv run python setup.py test
```

## Linting

```sh
pipenv run black nessclient nessclient_tests
pipenv run flake8 nessclient nessclient_tests
```

## Type Checking

```sh
pipenv run mypy --strict nessclient
```
