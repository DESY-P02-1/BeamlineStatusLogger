pipeline {
    agent any
    stages {
        stage('build docker image') {
            steps {
                sh 'docker-compose build'
                sh 'docker-compose up -d'
                sh 'sleep 3'
            }
        }
        stage('style') {
            steps {
                sh 'docker-compose exec -T tango-test python3 -m flake8'
            }
        }
        stage('test') {
            steps {
                sh 'docker-compose exec -T tango-test python3 -m pytest --junitxml=build/results.xml'
            }
            post {
                always {
                    junit 'build/results.xml'
                }
            }
        }
    }
    post {
        always {
            sh 'docker-compose down --volume'
        }
    }
}
