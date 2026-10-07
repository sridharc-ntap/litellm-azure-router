{{- define "litellm-router.name" -}}
litellm-router
{{- end -}}

{{- define "litellm-router.fullname" -}}
{{ include "litellm-router.name" . }}
{{- end -}}