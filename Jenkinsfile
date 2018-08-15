node {
    checkout scm
    
    def pythonImage
    stage('build docker image') {
        pythonImage = docker.build("tango-test", ".ci/debian9")
    }
        
    stage('style') {
        pythonImage.inside {
            sh 'python3 -m flake8'
        }
    }
    
    withEnv(['INFLUXDB_HOST=influxdb-test']) {    
        stage('test') {
            docker.image('influxdb').withRun("--hostname influxdb-test") { c1 ->     
                sh 'echo influx: $INFLUXDB_HOST'
                pythonImage.withRun("--hostname tango-test") { c2 ->
                    sh 'echo tango: $INFLUXDB_HOST'
                    pythonImage.inside("--link ${c2.id}:tango-test --link ${c1.id}:influxdb-test") {
                        sh 'echo python: $INFLUXDB_HOST'
                        sh 'python3 -c "import os; print(os.environ[\'INFLUXDB_HOST\'])"'
                        try {
                            sh 'python3 -m pytest --junitxml=build/results.xml'
                        }
                        finally {
                            junit 'build/results.xml'
                        }
                    }
                }
            }
        }
    }
}
