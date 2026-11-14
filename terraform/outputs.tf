output "elastic_ip" {
  description = "Permanent Static Public IPv4 Address of AWS EC2 server"
  value       = aws_eip.web_eip.public_ip
}

output "instance_id" {
  description = "AWS EC2 Instance ID"
  value       = aws_instance.web_server.id
}

output "ssh_command" {
  description = "Command to SSH directly into the AWS EC2 server"
  value       = "ssh -i ec2_key.pem ubuntu@${aws_eip.web_eip.public_ip}"
}

output "s3_bucket_name" {
  description = "AWS S3 Bucket name for research PDF storage"
  value       = aws_s3_bucket.pdf_storage.id
}
