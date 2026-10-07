pipeline {
  agent {
    label 'k8s-jenkins-agent' // adjust to your Jenkins agent label
  }

  environment {
    ACR_NAME = 'acr4llm'                       // e.g., myacr.azurecr.io
    IMAGE_REPO = "${env.ACR_NAME}.azurecr.io/litellm-router"
    K8S_NAMESPACE = 'llm-proxy'
    ACR_SP_CLIENT_ID = '93a69b84-9fe0-4b6c-97df-067abe9da25c'
    ACR_SP_TENANT_ID = 'd391996a-90c3-4732-8d2d-5203c94f2995'
    ACR_SP_SECRET_NAME = 'acr-push-sp'
    ACR_SP_SECRET_KEY = 'client-secret'
    GIT_PUSH_CRED = 'gitea-git-write'
    GIT_BRANCH_NAME = 'master'
    VALUES_FILE = 'chart/litellm-router/values.yaml'
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

    stage('Build & Push Image') {
      steps {
        // Jenkins runs in AKS, so use the agent pod's service-account token.
        sh '''
          KUBE_TOKEN="$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)"
          KUBE_CA="/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
          kube() {
            kubectl --server="https://${KUBERNETES_SERVICE_HOST}:443" \
              --certificate-authority="$KUBE_CA" \
              --token="$KUBE_TOKEN" "$@"
          }
          ACR_SP_SECRET="$(kube get secret "${ACR_SP_SECRET_NAME}" -n "${K8S_NAMESPACE}" -o jsonpath="{.data['${ACR_SP_SECRET_KEY}']}" | base64 --decode)"
          test -n "$ACR_SP_SECRET" || { echo "ACR service-principal Secret is empty or missing" >&2; exit 1; }
          az login --service-principal \
            --username "$ACR_SP_CLIENT_ID" \
            --password "$ACR_SP_SECRET" \
            --tenant "$ACR_SP_TENANT_ID" \
            --output none
          az acr login --name "$ACR_NAME"
          docker build -t ${IMAGE_REPO}:${IMAGE_TAG} .
          docker push ${IMAGE_REPO}:${IMAGE_TAG}
        '''
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

            steps {
              sh "helm upgrade --install litellm-router charts/litellm-router --namespace ${K8S_NAMESPACE} --set image.repository=${IMAGE_REPO} --set image.tag=${IMAGE_TAG} --create-namespace"
            }
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
