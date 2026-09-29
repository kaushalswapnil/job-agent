variable "aws_region"       { default = "us-east-1" }
variable "environment"      { default = "prod" }
variable "project_name"     { default = "job-agent" }
variable "db_password"      { sensitive = true }
variable "candidate_email"  { description = "Email address for notifications" }
variable "ecr_image_uri"    { description = "ECR image URI for agent container" }
