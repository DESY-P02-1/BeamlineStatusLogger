node {
    checkout scm
    
    def pythonImage
    stage('build docker image') {
        pythonImage = docker.build("tango-test", ".ci/debian9")
    }
        
    stage('test') {
        pythonImage.withRun("--hostname tango-test") { c ->
            pythonImage.inside("--link ${c.id}:tango-test") {  
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
}
