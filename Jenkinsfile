pipeline {
  agent {
    label 'k8s-jenkins-agent' // adjust to your Jenkins agent label
  }

  environment {
    ACR_NAME = 'acr4llm'                       // e.g., myacr.azurecr.io
    IMAGE_REPO = "${env.ACR_NAME}.azurecr.io/litellm-router"
    K8S_NAMESPACE = 'llm-proxy'
    ACR_SP_TENANT_ID = 'd391996a-90c3-4732-8d2d-5203c94f2995'
    ACR_CREDENTIALS_ID = 'acr-sp-credentials'
    GIT_PUSH_CRED = 'gitea-git-write'
    GIT_BRANCH_NAME = 'master'
    CHART_DIR = 'charts/litellm-router'
    VALUES_FILE = 'charts/litellm-router/values.yaml'
  }

  stages {
    stage('Checkout') {
      steps {
        script {
          checkout scm  // configured to use Gitea repository
          env.IMAGE_TAG = "${env.BUILD_NUMBER}-${env.GIT_COMMIT.substring(0, 8)}"
        }
      }
    }

    stage('Run unit tests') {
      steps {
        sh 'python -m pip install --upgrade pip'
        sh 'pip install -r requirements.txt -r requirements-dev.txt'
        sh 'pytest -q'
      }
    }

    stage('Validate Helm chart') {
      steps {
        sh '''
          set -eu
          helm lint "${CHART_DIR}"
          helm template litellm-router "${CHART_DIR}" \
            --namespace "${K8S_NAMESPACE}" \
            --set image.repository="${IMAGE_REPO}" \
            --set image.tag="${IMAGE_TAG}" \
            >/tmp/litellm-router-rendered.yaml
        '''
      }
    }

    stage('Build & Push Image') {
      steps {
        // Jenkins credential type: Username with password.
        // Username is the service-principal client ID; password is its client secret.
        withCredentials([usernamePassword(credentialsId: env.ACR_CREDENTIALS_ID, usernameVariable: 'ACR_CLIENT_ID', passwordVariable: 'ACR_CLIENT_SECRET')]) {
          sh '''
            set -eu
            az login --service-principal \
              --username "$ACR_CLIENT_ID" \
              --password "$ACR_CLIENT_SECRET" \
              --tenant "$ACR_SP_TENANT_ID" \
              --output none
            az acr login --name "$ACR_NAME"
            docker build -t "${IMAGE_REPO}:${IMAGE_TAG}" .
            docker push "${IMAGE_REPO}:${IMAGE_TAG}"
          '''
        }
      }
    }

    stage('Smoke tests (in-cluster)') {
      steps {
        // Jenkins is running in AKS so it can access ClusterIP services by DNS unless network policy blocks.
        // If it cannot, use kubectl port-forward to the service or run tests as a pod.
        sh '''
          export ROUTER_URL="http://litellm-router.${K8S_NAMESPACE}.svc.cluster.local"
          pytest router/tests/test_smoke.py::test_smoke_chat --maxfail=1 -q
        '''
      }
    }

    stage('Update GitOps image tag') {
      steps {
        withCredentials([gitUsernamePassword(credentialsId: env.GIT_PUSH_CRED, gitToolName: 'Default')]) {
          sh '''
            set -eu
            sed -i \
              -e "s|^  repository:.*|  repository: ${IMAGE_REPO}|" \
              -e "s|^  tag:.*|  tag: ${IMAGE_TAG}|" \
              "${VALUES_FILE}"

              git diff --check
              if git diff --quiet -- "${VALUES_FILE}"; then
                echo "${VALUES_FILE} already references ${IMAGE_REPO}:${IMAGE_TAG}"
                exit 0
            }

              git config user.name 'Jenkins'
              git config user.email 'jenkins@localhost'
              git add "${VALUES_FILE}"
              git commit -m "Update LiteLLM image to ${IMAGE_TAG} [skip ci]"
              git push origin "HEAD:${GIT_BRANCH_NAME}"
          '''
        }
      }
    }
  }

  post {
    success {
      echo "Build & deploy succeeded: ${IMAGE_REPO}:${IMAGE_TAG}"
    }
    failure {
      echo "Pipeline failed"
    }
  }
}
