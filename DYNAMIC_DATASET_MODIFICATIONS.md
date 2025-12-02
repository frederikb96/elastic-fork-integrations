# Dynamic Dataset Modifications Tracking

This file tracks all Elastic integrations that have been modified by SVA to remove `dynamic_dataset` and `dynamic_namespace` flags for multi-tenant namespace isolation.

**What this is:** Upstream Elastic integrations sometimes use dynamic_dataset/dynamic_namespace flags that grant wildcard API key permissions (logs-*-*), breaking tenant isolation. This automated system removes those flags and marks affected integrations with warnings in Kibana Fleet UI.

**How it works:** Daily merge pipeline from upstream Elastic integrations triggers automatic detection and removal of dynamic flags. Python script modifies integration manifests, updates this tracking file, and commits changes. If any flags remain after cleanup, pipeline fails for manual SE investigation.

**Pipeline trigger:**
- Scheduled daily merge from upstream Elastic integrations repository
- Scans packages/ directory for dynamic_dataset and dynamic_namespace flags
- Invokes auto-fix script if flags detected
- Commits changes and triggers deploy pipeline
- Generates this YAML tracking data automatically

**Using restricted integrations:** If you need to use an integration marked as "SVA RESTRICTED" in Fleet UI, be aware it has been modified for namespace isolation. For production use with routing or special requirements, manual package cloning and testing is required. Contact SE team for assistance.

**Data stream status indicators:**
- ✅ (green checkmark) = Namespace-scoped, no dynamic flags. **Note:** This doesn't guarantee the data stream will work correctly - some depend on specific configurations or other data streams. Always test integrations before production use.
- ⚠️ (warning) = Had dynamic flags, now removed for namespace isolation. Review before use.

---

<!-- AUTO-GENERATED SECTION BELOW - DO NOT MODIFY YAML STRUCTURE -->
<!-- Only edit 'comment' fields - all other fields are auto-managed by ci/remove-dynamic-flags.py -->

```yaml
integrations:
  amazon_security_lake:
    title: Amazon Security Lake
    comment: ''
    data_streams:
      application_activity:
        namespaced: ⚠️
        comment: ''
      discovery:
        namespaced: ⚠️
        comment: ''
      event:
        namespaced: ⚠️
        comment: ''
      findings:
        namespaced: ⚠️
        comment: ''
      iam:
        namespaced: ⚠️
        comment: ''
      network_activity:
        namespaced: ⚠️
        comment: ''
      system_activity:
        namespaced: ⚠️
        comment: ''
  aws:
    title: AWS
    comment: ''
    data_streams:
      apigateway_logs:
        namespaced: ✅
        comment: ''
      apigateway_metrics:
        namespaced: ✅
        comment: ''
      awshealth:
        namespaced: ✅
        comment: ''
      billing:
        namespaced: ✅
        comment: ''
      cloudfront_logs:
        namespaced: ✅
        comment: ''
      cloudtrail:
        namespaced: ✅
        comment: ''
      cloudwatch_logs:
        namespaced: ⚠️
        comment: ''
      cloudwatch_metrics:
        namespaced: ✅
        comment: ''
      config:
        namespaced: ✅
        comment: ''
      dynamodb:
        namespaced: ✅
        comment: ''
      ebs:
        namespaced: ✅
        comment: ''
      ec2_logs:
        namespaced: ⚠️
        comment: ''
      ec2_metrics:
        namespaced: ✅
        comment: ''
      ecs_metrics:
        namespaced: ✅
        comment: ''
      elb_logs:
        namespaced: ✅
        comment: ''
      elb_metrics:
        namespaced: ✅
        comment: ''
      emr_logs:
        namespaced: ⚠️
        comment: ''
      emr_metrics:
        namespaced: ✅
        comment: ''
      firewall_logs:
        namespaced: ✅
        comment: ''
      firewall_metrics:
        namespaced: ✅
        comment: ''
      guardduty:
        namespaced: ✅
        comment: ''
      inspector:
        namespaced: ✅
        comment: ''
      kafka_metrics:
        namespaced: ✅
        comment: ''
      kinesis:
        namespaced: ✅
        comment: ''
      lambda:
        namespaced: ✅
        comment: ''
      lambda_logs:
        namespaced: ✅
        comment: ''
      natgateway:
        namespaced: ✅
        comment: ''
      rds:
        namespaced: ✅
        comment: ''
      redshift:
        namespaced: ✅
        comment: ''
      route53_public_logs:
        namespaced: ✅
        comment: ''
      route53_resolver_logs:
        namespaced: ✅
        comment: ''
      s3_daily_storage:
        namespaced: ✅
        comment: ''
      s3_request:
        namespaced: ✅
        comment: ''
      s3_storage_lens:
        namespaced: ✅
        comment: ''
      s3access:
        namespaced: ✅
        comment: ''
      securityhub_findings:
        namespaced: ✅
        comment: ''
      securityhub_findings_full_posture:
        namespaced: ✅
        comment: ''
      securityhub_insights:
        namespaced: ✅
        comment: ''
      sns:
        namespaced: ✅
        comment: ''
      sqs:
        namespaced: ✅
        comment: ''
      transitgateway:
        namespaced: ✅
        comment: ''
      usage:
        namespaced: ✅
        comment: ''
      vpcflow:
        namespaced: ✅
        comment: ''
      vpn:
        namespaced: ✅
        comment: ''
      waf:
        namespaced: ✅
        comment: ''
  aws_logs:
    title: Custom AWS Logs
    comment: ''
    data_streams:
      generic:
        namespaced: ⚠️
        comment: ''
  awsfirehose:
    title: Amazon Data Firehose
    comment: ''
    data_streams:
      logs:
        namespaced: ⚠️
        comment: ''
      metrics:
        namespaced: ⚠️
        comment: ''
  azure:
    title: Azure Logs
    comment: ''
    data_streams:
      activitylogs:
        namespaced: ⚠️
        comment: ''
      application_gateway:
        namespaced: ⚠️
        comment: ''
      auditlogs:
        namespaced: ⚠️
        comment: ''
      eventhub:
        namespaced: ⚠️
        comment: ''
      events:
        namespaced: ⚠️
        comment: ''
      firewall_logs:
        namespaced: ⚠️
        comment: ''
      graphactivitylogs:
        namespaced: ⚠️
        comment: ''
      identity_protection:
        namespaced: ⚠️
        comment: ''
      platformlogs:
        namespaced: ⚠️
        comment: ''
      provisioning:
        namespaced: ⚠️
        comment: ''
      signinlogs:
        namespaced: ⚠️
        comment: ''
      springcloudlogs:
        namespaced: ⚠️
        comment: ''
  azure_ai_foundry:
    title: Azure AI Foundry
    comment: ''
    data_streams:
      logs:
        namespaced: ✅
        comment: ''
      metrics:
        namespaced: ⚠️
        comment: ''
  azure_metrics:
    title: Azure Resource Metrics
    comment: ''
    data_streams:
      compute_vm:
        namespaced: ⚠️
        comment: ''
      compute_vm_scaleset:
        namespaced: ⚠️
        comment: ''
      container_instance:
        namespaced: ⚠️
        comment: ''
      container_registry:
        namespaced: ⚠️
        comment: ''
      container_service:
        namespaced: ⚠️
        comment: ''
      database_account:
        namespaced: ⚠️
        comment: ''
      monitor:
        namespaced: ⚠️
        comment: ''
      storage_account:
        namespaced: ⚠️
        comment: ''
  azure_openai:
    title: Azure OpenAI
    comment: ''
    data_streams:
      logs:
        namespaced: ✅
        comment: ''
      metrics:
        namespaced: ⚠️
        comment: ''
  cloud_asset_inventory:
    title: Cloud Asset Discovery
    comment: ''
    data_streams:
      asset_inventory:
        namespaced: ⚠️
        comment: ''
  cribl:
    title: Cribl
    comment: ''
    data_streams:
      logs:
        namespaced: ⚠️
        comment: ''
      metrics:
        namespaced: ⚠️
        comment: ''
  cyberarkpas:
    title: CyberArk Privileged Access Security
    comment: ''
    data_streams:
      audit:
        namespaced: ⚠️
        comment: ''
      monitor:
        namespaced: ✅
        comment: ''
  docker:
    title: Docker
    comment: ''
    data_streams:
      container:
        namespaced: ✅
        comment: ''
      container_logs:
        namespaced: ⚠️
        comment: ''
      cpu:
        namespaced: ✅
        comment: ''
      diskio:
        namespaced: ✅
        comment: ''
      event:
        namespaced: ✅
        comment: ''
      healthcheck:
        namespaced: ✅
        comment: ''
      image:
        namespaced: ✅
        comment: ''
      info:
        namespaced: ✅
        comment: ''
      memory:
        namespaced: ✅
        comment: ''
      network:
        namespaced: ✅
        comment: ''
  entityanalytics_entra_id:
    title: Microsoft Entra ID Entity Analytics
    comment: ''
    data_streams:
      device:
        namespaced: ✅
        comment: ''
      entity:
        namespaced: ⚠️
        comment: ''
      user:
        namespaced: ✅
        comment: ''
  entityanalytics_okta:
    title: Okta Entity Analytics
    comment: ''
    data_streams:
      device:
        namespaced: ✅
        comment: ''
      entity:
        namespaced: ⚠️
        comment: ''
      user:
        namespaced: ✅
        comment: ''
  falco:
    title: Falco
    comment: ''
    data_streams:
      alerts:
        namespaced: ⚠️
        comment: ''
      alerts_agent:
        namespaced: ⚠️
        comment: ''
  kafka:
    title: Kafka
    comment: ''
    data_streams:
      broker:
        namespaced: ✅
        comment: ''
      consumer:
        namespaced: ✅
        comment: ''
      consumergroup:
        namespaced: ✅
        comment: ''
      controller:
        namespaced: ✅
        comment: ''
      jvm:
        namespaced: ✅
        comment: ''
      log:
        namespaced: ⚠️
        comment: ''
      log_manager:
        namespaced: ✅
        comment: ''
      network:
        namespaced: ✅
        comment: ''
      partition:
        namespaced: ✅
        comment: ''
      producer:
        namespaced: ✅
        comment: ''
      raft:
        namespaced: ✅
        comment: ''
      replica_manager:
        namespaced: ✅
        comment: ''
      topic:
        namespaced: ✅
        comment: ''
  kafka_log:
    title: Custom Kafka Logs
    comment: ''
    data_streams:
      generic:
        namespaced: ⚠️
        comment: ''
  netskope:
    title: Netskope
    comment: ''
    data_streams:
      alerts:
        namespaced: ✅
        comment: ''
      alerts_events_v2:
        namespaced: ⚠️
        comment: ''
      alerts_v2:
        namespaced: ✅
        comment: ''
      events:
        namespaced: ✅
        comment: ''
      events_v2:
        namespaced: ✅
        comment: ''
      transaction:
        namespaced: ✅
        comment: ''
  prometheus:
    title: Prometheus
    comment: ''
    data_streams:
      collector:
        namespaced: ⚠️
        comment: ''
      query:
        namespaced: ⚠️
        comment: ''
      remote_write:
        namespaced: ⚠️
        comment: ''
  syslog_router:
    title: Syslog Router
    comment: ''
    data_streams:
      log:
        namespaced: ⚠️
        comment: ''
  kubernetes:
    title: Kubernetes
    comment: ''
    data_streams:
      apiserver:
        namespaced: ✅
        comment: ''
      audit_logs:
        namespaced: ✅
        comment: ''
      container:
        namespaced: ✅
        comment: ''
      container_logs:
        namespaced: ⚠️
        comment: ''
      controllermanager:
        namespaced: ✅
        comment: ''
      event:
        namespaced: ✅
        comment: ''
      node:
        namespaced: ✅
        comment: ''
      pod:
        namespaced: ✅
        comment: ''
      proxy:
        namespaced: ✅
        comment: ''
      scheduler:
        namespaced: ✅
        comment: ''
      state_container:
        namespaced: ✅
        comment: ''
      state_cronjob:
        namespaced: ✅
        comment: ''
      state_daemonset:
        namespaced: ✅
        comment: ''
      state_deployment:
        namespaced: ✅
        comment: ''
      state_job:
        namespaced: ✅
        comment: ''
      state_namespace:
        namespaced: ✅
        comment: ''
      state_node:
        namespaced: ✅
        comment: ''
      state_persistentvolume:
        namespaced: ✅
        comment: ''
      state_persistentvolumeclaim:
        namespaced: ✅
        comment: ''
      state_pod:
        namespaced: ✅
        comment: ''
      state_replicaset:
        namespaced: ✅
        comment: ''
      state_resourcequota:
        namespaced: ✅
        comment: ''
      state_service:
        namespaced: ✅
        comment: ''
      state_statefulset:
        namespaced: ✅
        comment: ''
      state_storageclass:
        namespaced: ✅
        comment: ''
      system:
        namespaced: ✅
        comment: ''
      volume:
        namespaced: ✅
        comment: ''
  entityanalytics_ad:
    title: Active Directory Entity Analytics
    comment: ''
    data_streams:
      device:
        namespaced: ✅
        comment: ''
      entity:
        namespaced: ⚠️
        comment: ''
      user:
        namespaced: ✅
        comment: ''
  proofpoint_essentials:
    title: Proofpoint Essentials
    comment: ''
    data_streams:
      clicks_blocked:
        namespaced: ⚠️
        comment: ''
      clicks_permitted:
        namespaced: ⚠️
        comment: ''
      message_blocked:
        namespaced: ⚠️
        comment: ''
      message_delivered:
        namespaced: ⚠️
        comment: ''
      threat:
        namespaced: ⚠️
        comment: ''
```
