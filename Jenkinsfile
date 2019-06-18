
pipeline {

  agent {
    docker {
      image 'gcr.io/organic-storm-201412/docker-tac-develop:latest'
    }
  }

  stages {

    stage('Prebuild'){

        steps {
            sh 'apk update'
            //cryptography dependencies
            sh 'apk add gcc g++ gfortran python3-dev musl-dev libffi-dev openssl-dev  freetype-dev libpng-dev openblas-dev'
        }

    }

    stage('Unit Tests') {

        steps {
            sh 'pipenv run tox -e py37 -- --ci'
        }

    } // build & test

  } // stages

} // pipeline
