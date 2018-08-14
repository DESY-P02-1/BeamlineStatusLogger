node {
    checkout scm
    
    def pythonImage
    stage('build docker image') {
        pythonImage = docker.build("tango-test", ".ci/debian9")
    }
        
    stage('test') {
        pythonImage.inside("--hostname tango-test") {
            sh 'python3 -m flake8'
            try {
                sh 'python3 -m pytest --junitxml=build/results.xml'
            }
            finally {
                junit 'build/results.xml'
            }
        }
    }
}
