terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

variable "aws_region" {
  description = "AWS region for the help desk demo infrastructure."
  type        = string
  default     = "us-east-2"
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "intelligent-it-help-desk"
      ManagedBy = "Terraform"
    }
  }
}

resource "aws_vpc" "demo" {
  cidr_block           = "10.42.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
}

resource "aws_subnet" "demo" {
  vpc_id     = aws_vpc.demo.id
  cidr_block = "10.42.1.0/24"
}

resource "aws_internet_gateway" "demo" {
  vpc_id = aws_vpc.demo.id
}

resource "aws_route_table" "demo" {
  vpc_id = aws_vpc.demo.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.demo.id
  }
}

resource "aws_route_table_association" "demo" {
  subnet_id      = aws_subnet.demo.id
  route_table_id = aws_route_table.demo.id
}

resource "aws_security_group" "demo" {
  name_prefix = "helpdesk-demo-"
  description = "Help desk demo host managed through Session Manager"
  vpc_id      = aws_vpc.demo.id
}

resource "aws_vpc_security_group_egress_rule" "https" {
  security_group_id = aws_security_group.demo.id
  description       = "HTTPS to Systems Manager, S3, and package repositories"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "0.0.0.0/0"
}

data "aws_ssm_parameter" "al2023" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

resource "aws_iam_role" "demo" {
  name_prefix = "helpdesk-demo-"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.demo.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "demo" {
  name_prefix = "helpdesk-demo-"
  role        = aws_iam_role.demo.name
}

resource "aws_instance" "demo" {
  ami                         = data.aws_ssm_parameter.al2023.value
  instance_type               = "t3.small"
  subnet_id                   = aws_subnet.demo.id
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.demo.id]
  iam_instance_profile        = aws_iam_instance_profile.demo.name

  credit_specification {
    cpu_credits = "standard"
  }

  metadata_options {
    http_tokens = "required"
  }

  root_block_device {
    encrypted   = true
    volume_type = "gp3"
    volume_size = 20
  }

  tags = {
    Name = "helpdesk-demo"
  }

  depends_on = [
    aws_iam_role_policy_attachment.ssm,
    aws_route_table_association.demo,
    aws_vpc_security_group_egress_rule.https,
  ]
}

output "aws_region" {
  description = "AWS region used by the demo stack."
  value       = var.aws_region
}

output "instance_id" {
  description = "EC2 instance ID for AWS Systems Manager Session Manager."
  value       = aws_instance.demo.id
}
