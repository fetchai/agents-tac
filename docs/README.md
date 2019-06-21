# TAC Documentation

## Build

- Before getting started, check that:

  - [x] You have followed the steps under 'Dependencies' and 'Preliminaries' on root readme.

- Activate the virtual environment:

      pipenv shell

- Enter `docs`:
    
      cd docs

- Run:

      sphinx-apidoc -o reference/api/ ../tac/
      make html

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
