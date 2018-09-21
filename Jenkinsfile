node {
    checkout scm

    stage('build docker image') {
        sh 'docker-compose build'
    }

    try {
        sh 'docker-compose up -d'
        sh 'sleep 3'

        stage('style') {
            sh 'docker-compose exec -T tango-test python3 -m flake8'
        }

        stage('test') {
            try {
                sh 'docker-compose exec -T tango-test python3 -m pytest --junitxml=build/results.xml'
            }
            finally {
                junit 'build/results.xml'
            }
        }
    }
    finally {
        sh 'docker-compose down --volume'
    }
}
