#!/bin/bash
# LocalStack init for Project 1 — Log Anomaly Detective
# Creates CloudWatch log groups used by the 3 microservices

echo "=== Project 1 LocalStack Init ==="
sleep 3

export AWS_DEFAULT_REGION=us-east-1
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_ENDPOINT_URL=http://localhost:4566

echo "Waiting for EC2 to be ready..."
for i in $(seq 1 10); do
  awslocal ec2 describe-instances &>/dev/null && echo "EC2 ready" && break
  echo "EC2 not ready yet, retrying in 3s... ($i/10)"
  sleep 3
done

echo "Creating CloudWatch log groups..."
awslocal logs create-log-group  --log-group-name /aiops/services 2>/dev/null || true
awslocal logs create-log-stream --log-group-name /aiops/services --log-stream-name auth-service      2>/dev/null || true
awslocal logs create-log-stream --log-group-name /aiops/services --log-stream-name payment-service   2>/dev/null || true
awslocal logs create-log-stream --log-group-name /aiops/services --log-stream-name inventory-api     2>/dev/null || true

echo "Creating mock EC2 instances..."
awslocal ec2 run-instances \
  --image-id ami-00000001 \
  --instance-type t2.micro \
  --count 1 \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=auth-node-1},{Key=Service,Value=auth}]' \
  2>/dev/null || true

awslocal ec2 run-instances \
  --image-id ami-00000001 \
  --instance-type t2.micro \
  --count 1 \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=payment-node-1},{Key=Service,Value=payment}]' \
  2>/dev/null || true

awslocal ec2 run-instances \
  --image-id ami-00000001 \
  --instance-type t2.micro \
  --count 1 \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=inventory-node-1},{Key=Service,Value=inventory}]' \
  2>/dev/null || true

echo "Verifying EC2 instances..."
awslocal ec2 describe-instances --query 'Reservations[*].Instances[*].{ID:InstanceId,State:State.Name,Name:Tags[?Key==`Name`]|[0].Value}' --output table 2>/dev/null || true

echo "=== Project 1 Init Complete ==="