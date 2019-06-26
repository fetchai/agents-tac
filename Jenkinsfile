
node {

    checkout scm

    //sh('python ./oef_search_pluto_scripts/launch.py -c oef_search_pluto_scripts/launch_config_ci.json')

    docker.image('gcr.io/organic-storm-201412/docker-tac-develop:latest').inside("--network host") {

        stage('Unit Tests') {

            sh 'pip install tox'
            sh 'tox -e py37 -- --no-oef'

        } // unit tests

    }

}

//docker.image('fetchai/oef-search:latest')
//    .withRun('-v ${WORKSPACE}/oef_search_pluto_scripts:/config:ro --network host',
//             'node no_sh --config_file /config/node_config.json') { c ->
