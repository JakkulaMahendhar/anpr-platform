#!/bin/sh
# Starts a single-node SeaweedFS with its S3 gateway.
# Credentials come from the environment, so no secret is stored in the repo.
set -eu
: "${S3_ACCESS_KEY:?S3_ACCESS_KEY must be set}"
: "${S3_SECRET_KEY:?S3_SECRET_KEY must be set}"

mkdir -p /etc/seaweedfs
cat > /etc/seaweedfs/s3.json <<JSON
{
  "identities": [
    {
      "name": "anpr",
      "credentials": [{"accessKey": "${S3_ACCESS_KEY}", "secretKey": "${S3_SECRET_KEY}"}],
      "actions": ["Admin", "Read", "Write", "List", "Tagging"]
    }
  ]
}
JSON
chmod 600 /etc/seaweedfs/s3.json

exec weed server -dir=/data -s3 -s3.port=8333 -s3.config=/etc/seaweedfs/s3.json \
  -master.volumeSizeLimitMB=1024 -volume.max=0
