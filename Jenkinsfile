
pipeline {

  agent none

  stages {

    stage('Unit Tests') {

        stage('Python 3.7') {

          agent {
            docker {
              image "python:3.7-alpine"
            }
          }

          steps {
            sh 'pip install tox'
            sh 'tox -e py37'
          }

        } // Python 3.7

    } // build & test

  } // stages

} // pipeline
