# TAC Documentation

## Build

- Activate the virtual environment:

      pipenv shell

- Enter in `docs`:
    
      cd docs

- Run:

      make html
      sphinx-apidoc -o reference/api/ ../tac/
   
To display the documentation in your browser, e.g. Firefox, open the `index.html` file in `./_build/html/index.html`.

**NOTICE**: run this command outside the Docker image.

    firefox _build/html/index.html

