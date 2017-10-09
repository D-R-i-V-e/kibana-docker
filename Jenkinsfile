#!/usr/bin/env groovy

try {
    node('docker-lab-builder') {

        def ORIGINAL_REGISTRY = 'docker.elastic.co'
        def ORGANIZATION = 'my-organization'
        def RELEASE = '1.0-SNAPSHOT'
        def NAME = 'kibana'

        stage('Checkout') {
            checkout scm
        }

        def VERSION = sh(script: 'cat version.txt', returnStdout: true).trim()
        def REPOSITORY_AND_TAG = "${ORGANIZATION}/${NAME}:${VERSION}-${RELEASE}"
        def ORIGINAL_REPOSITORY_AND_TAG = "${ORIGINAL_REGISTRY}/${NAME}/${NAME}:${VERSION}"

        //Get docker agnostic repository that is defined in the build server
        //Use agnostic credentials ID to get from Jenkins Credentials
        docker.withRegistry("https://${env.DOCKER_REGISTRY_HOST_AND_PORT}", env.DOCKER_REGISTRY_CREDENTIALS_ID) {
            //Used pre-build image with all Python dependencies pre-installed in advance
            def pythonDockerImage = docker.image('${ORGANIZATION}/python-build-helper:elk-1.0')

            stage('Clean') {
                pythonDockerImage.inside('-u root') {
                    sh 'rm -rf tests/reports/'
                    sh 'rm -rf .cache/'
                }
            }

            stage('Pre-Build') {
                parallel(
                        'dockerfile': {
                            pythonDockerImage.inside {
                                sh "make dockerfile -W venv"
                            }
                        },
                        'docker-compose.yml': {
                            pythonDockerImage.inside {
                                sh "make docker-compose.yml -W venv"
                            }
                        }
                )
            }

            stage('Build') {
                sh "make build -W venv -W dockerfile"
            }

            def image = docker.image(ORIGINAL_REPOSITORY_AND_TAG)

            stage('Tests') {
                parallel(
                        'Pytest': {
                            try {
                                //attach Docker socket to allow running LS images from Python image
                                pythonDockerImage.inside("-u root -v /var/run/docker.sock:/var/run/docker.sock") {
                                    sh 'make test -W venv -W build -W dockerfile -W docker-compose.yml'
                                }
                            } finally {
                                //export test results to Jenkins
                                junit 'tests/reports/*.xml'
                            }
                        },
                        'Security':{
                            //FYI step to check if the images is aligned with CIS benchmark
                            //Clair scan executed before CD
                            docker.image('${ORGANIZATION}/docker-bench-security:1.3.3-1.0').inside('-u root' +
                                    ' --net host' +
                                    ' --pid host' +
                                    ' --cap-add audit_control' +
                                    ' -e DOCKER_CONTENT_TRUST=$DOCKER_CONTENT_TRUST' +
                                    ' -v /var/lib:/var/lib' +
                                    ' -v /var/run/docker.sock:/var/run/docker.sock' +
                                    ' -v /usr/lib/systemd:/usr/lib/systemd' +
                                    ' -v /etc:/etc' +
                                    ' --label docker_bench_security') {
                                sh "cd /usr/local/bin && docker-bench-security.sh -i ${image.id} -t 4"
                            }
                        }
                )

            }

            stage('Tag and Push') {
                //TODO: sign with Notary
                //ORIGINAL_REGISTRY is hardcoded in constants, so te-tagging is requiered
                sh "docker image tag ${ORIGINAL_REPOSITORY_AND_TAG} ${REPOSITORY_AND_TAG}"
                image = docker.image(REPOSITORY_AND_TAG)
                image.push()
            }

        }

        stage('Remove') {
            sh "docker image rm ${REPOSITORY_AND_TAG} ${env.DOCKER_REGISTRY_HOST_AND_PORT}/${REPOSITORY_AND_TAG}"
            sh "docker image rm ${ORIGINAL_REPOSITORY_AND_TAG}"
        }
    }
} catch (ex) {
    // If there was an exception thrown, the build failed
    if (currentBuild.result != "ABORTED") {
        // Send e-mail notifications for failed or unstable builds.
        // currentBuild.result must be non-null for this step to work.
        emailext(
                recipientProviders: [
                        [$class: 'DevelopersRecipientProvider'],
                        [$class: 'RequesterRecipientProvider']],
                subject: "Job '${env.JOB_NAME}' - Build ${env.BUILD_DISPLAY_NAME} - FAILED!",
                body: """<p>Job '${env.JOB_NAME}' - Build ${env.BUILD_DISPLAY_NAME} - FAILED:</p>
                        <p>Check console output &QUOT;<a href='${env.BUILD_URL}'>${env.BUILD_DISPLAY_NAME}</a>&QUOT;
                        to view the results.</p>"""
        )
    }

    // Must re-throw exception to propagate error:
    throw ex
}
