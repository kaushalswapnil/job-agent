aws_region      = "us-east-1"
environment     = "prod"
project_name    = "job-agent"
candidate_email = "your.email@example.com"   # Replace before deploying
ecr_image_uri   = ""                          # Set after building Docker image
# db_password   = set via: export TF_VAR_db_password="your-secure-password"
