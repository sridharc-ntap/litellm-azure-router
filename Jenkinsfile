pipeline {
  agent { label 'k8s-jenkins-agent' }

  environment {
    ACR_NAME = 'acr4llm'
    IMAGE_REPO = "${env.ACR_NAME}.azurecr.io/litellm-router"
    K8S_NAMESPACE = 'llm-proxy'
    CHART_DIR = 'charts/litellm-router'
    ACR_CREDENTIALS_ID = 'acr-sp-credentials'
    GIT_PUSH_CRED = 'gitea-git-write'
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
        script { env.IMAGE_TAG = "${env.BUILD_NUMBER}-${env.GIT_COMMIT.substring(0,8)}" }
      }
    }

    stage('Run unit tests') {
      when {
        expression { false }
      }
      steps {
        container('python') {
          sh '''
            python -m pip install --upgrade pip
            pip install -r requirements.txt -r requirements-dev.txt
            pytest -q
          '''
        }
      }
    }

    stage('Validate Helm chart') {
      steps {
        container('helm') {
          sh """
            helm lint ${CHART_DIR}
            helm template litellm-router ${CHART_DIR} \
              --namespace ${K8S_NAMESPACE} \
              --set image.repository=${IMAGE_REPO} \
              --set image.tag=${IMAGE_TAG} \
              > /tmp/litellm-router-rendered.yaml
          """
        }
      }
    }

    stage('Build & Push Image') {
      steps {
        // run kaniko executor (it uses mounted /kaniko/.docker from pod secret)
        container('kaniko') {
          withCredentials([usernamePassword(credentialsId: env.ACR_CREDENTIALS_ID, usernameVariable: 'ACR_CLIENT_ID', passwordVariable: 'ACR_CLIENT_SECRET')]) {
            sh '''
              set -eu
              DOCKER_CONFIG_DIR="${WORKSPACE}/.kaniko-docker-config"
              mkdir -p "$DOCKER_CONFIG_DIR"
              trap 'rm -rf "$DOCKER_CONFIG_DIR"' EXIT
              ACR_AUTH="$(printf '%s' "$ACR_CLIENT_ID:$ACR_CLIENT_SECRET" | base64 | tr -d '\\n')"
              printf '{"auths":{"%s":{"auth":"%s"}}}\n' \
                "${ACR_NAME}.azurecr.io" "$ACR_AUTH" > "$DOCKER_CONFIG_DIR/config.json"
              export DOCKER_CONFIG="$DOCKER_CONFIG_DIR"
              /kaniko/executor \
                --context ${WORKSPACE} \
                --dockerfile ${WORKSPACE}/Dockerfile \
                --destination ${IMAGE_REPO}:${IMAGE_TAG} \
                --cache=true
            '''
          }
        }
      }
    }

    stage('Deploy (Helm)') {
      steps {
        // Helm waits for the deployed resources to become ready.
        container('helm') {
          sh """
            helm upgrade --install litellm-router ${CHART_DIR} \
              --namespace ${K8S_NAMESPACE} \
              --set image.repository=${IMAGE_REPO} \
              --set image.tag=${IMAGE_TAG} \
              --wait --timeout 120s
          """
        }
      }
    }

    stage('Smoke tests (in-cluster)') {
      steps {
        container('python') {
          sh '''
            pip install requests pytest
            export ROUTER_URL="http://litellm-router.${K8S_NAMESPACE}.svc.cluster.local"
            pytest router/tests/test_smoke.py::test_smoke_chat --maxfail=1 -q
          '''
        }
      }
    }
  }

  post {
    success { echo "Deployed ${IMAGE_REPO}:${IMAGE_TAG}" }
    failure { echo "Pipeline failed" }
    always { cleanWs() }
  }
}