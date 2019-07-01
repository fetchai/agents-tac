
node {

    checkout scm

    docker.image('gcr.io/organic-storm-201412/docker-tac-develop:latest').inside("--network host") {

        stage('Unit Tests') {

            sh 'pip install tox'
            sh 'tox -e py37 -- --no-oef'

        }

    }

}
