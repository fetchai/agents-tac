# TAC Documentation

## Build

- Activate the virtual environment:

      pipenv shell

- Enter `docs`:
    
      cd docs

- Run:

      make html
      sphinx-apidoc -o reference/api/ ../tac/

## Display

To display the documentation in your browser, open the `index.html` file in `./_build/html/index.html`.

- From terminal do
```
firefox _build/html/index.html
```
- or
```
open _build/html/index.html
```

## Dependencies

To generate `plantuml` files you need to install it:

- On mac:

```
brew install plantuml
```

- On ubuntu:

```
apt install plantuml -y
```
