# TAC Documentation



## Build

- [build the `docker-tac-develop` Docker image](../docker-tac-develop/README.md#build).
- [run the `docker-tac-develop` Docker image](../docker-tac-develop/README.md#run).
- Activate the virtual environment:

      pipenv shell

- Enter in `docs`:
    
      cd docs

- Run:

      make html
    
    
   
To display the documentation in your browser, e.g. Firefox, open the `index.html` file in `./_build/html/index.html`.

**NOTICE**: run this command outside the Docker image.

    firefox _build/html/index.html

