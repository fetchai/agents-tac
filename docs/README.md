# TAC Documentation


## Requirements

- ensure you have activated and installed the development packages specified in the `Pipfile`:
    
      pipenv shell  # if the environment is not activated yet
      
  then:
  
      pipenv install --dev  # to install all the development packages (including Sphinx)

- Install PlantUML:
    - Mac OSX: http://macappstore.org/plantuml/
    - Linux: `sudo apt install plantuml`

## Build

Run:

    make html
    
    
To display the documentation in your browser, e.g. Firefox, open the `index.html` file in `./_build/html/index.html`.

    firefox _build/html/index.html