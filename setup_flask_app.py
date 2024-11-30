import os
import subprocess
import mysql.connector
import secrets

def run_command(command, check=True):
    """Run a shell command."""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0 and check:
        print(f"Error: {result.stderr}")
        exit(result.returncode)
    print(result.stdout)

def setup_mysql(root_password):
    """Configure MySQL, create a user, and populate the database."""
    db_user = input("Enter the MySQL username for your Flask app: ")
    db_password = input("Enter the password for this MySQL user: ")
    db_name = input("Enter the name of the database to create: ")

    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password=root_password
        )
        cursor = connection.cursor()

        # Create user, database, and grant privileges
        cursor.execute(f"CREATE USER '{db_user}'@'localhost' IDENTIFIED BY '{db_password}';")
        cursor.execute(f"CREATE DATABASE {db_name};")
        cursor.execute(f"GRANT ALL PRIVILEGES ON {db_name}.* TO '{db_user}'@'localhost';")
        cursor.execute("FLUSH PRIVILEGES;")

        # Populate the database with SQL.txt
        if os.path.exists("SQL.txt"):
            with open("SQL.txt", "r") as sql_file:
                sql_commands = sql_file.read()
                for statement in sql_commands.split(";"):
                    if statement.strip():
                        cursor.execute(statement)
        print("MySQL setup complete.")
    except mysql.connector.Error as err:
        print(f"MySQL Error: {err}")
        exit(1)
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

    return db_user, db_password, db_name

def generate_secret_key():
    """Generate a random secret key."""
    return secrets.token_urlsafe(32)

def create_env_file(root_password, db_user, db_password, db_name):
    """Create or append to the .env file and secure it."""
    aws_access_key_id = input("Enter your AWS Access Key ID: ")
    aws_secret_access_key = input("Enter your AWS Secret Access Key: ")
    aws_region = input("Enter your AWS Region: ")
    s3_bucket_name = input("Enter your S3 Bucket Name: ")

    secret_key = generate_secret_key()

    env_content = f"""
SECRET_KEY={secret_key}
DB_HOST=localhost
DB_USER={db_user}
DB_PASSWORD={db_password}
DB_NAME={db_name}
AWS_ACCESS_KEY_ID={aws_access_key_id}
AWS_SECRET_ACCESS_KEY={aws_secret_access_key}
AWS_REGION={aws_region}
S3_BUCKET_NAME={s3_bucket_name}
"""

    env_file_path = ".env"
    with open(env_file_path, "w") as env_file:
        env_file.write(env_content.strip())

    # Set file permissions to 600
    subprocess.run(["chmod", "600", env_file_path])

    print("Generated .env file with secure permissions:")
    print(env_content)

def configure_nginx():
    """Configure Nginx to proxy requests to the Flask app."""
    domain_or_ip = input("Enter your EC2 server's domain or public IP address: ")

    nginx_config = f"""
server {{
    listen 80;
    server_name {domain_or_ip};

    location / {{
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""

    nginx_config_path = "/etc/nginx/sites-available/flask_app"
    symlink_path = "/etc/nginx/sites-enabled/flask_app"

    # Write the configuration file
    with open(nginx_config_path, "w") as nginx_file:
        nginx_file.write(nginx_config)

    # Enable the site and restart Nginx
    run_command(f"sudo ln -sf {nginx_config_path} {symlink_path}")
    run_command("sudo nginx -t")
    run_command("sudo systemctl restart nginx")

    print(f"Nginx configured for domain/IP: {domain_or_ip}")

def main():
    """Main automation script."""
    # Update and upgrade system
    run_command("sudo apt update && sudo apt upgrade -y")

    # Install required packages
    packages = [
        "python3", "python3-venv", "python3-pip",
        "build-essential", "libssl-dev", "libffi-dev", "python3-dev",
        "mysql-server", "libmysqlclient-dev", "ufw", "nginx"
    ]
    run_command(f"sudo apt install -y {' '.join(packages)}")

    # Upgrade pip and set up virtual environment
    run_command("pip3 install --upgrade pip")
    run_command("python3 -m venv venv")
    run_command("source venv/bin/activate")

    # Install Python dependencies
    run_command("pip install -r requirements.txt")

    # Configure MySQL
    print("Please set the MySQL root password during installation.")
    run_command("sudo mysql_secure_installation", check=False)
    root_password = input("Enter the MySQL root password: ")
    db_user, db_password, db_name = setup_mysql(root_password)

    # Configure UFW
    ufw_rules = ["5000", "http", "https", "ssh", "3306"]
    for rule in ufw_rules:
        run_command(f"sudo ufw allow {rule}")
    run_command("sudo ufw enable")

    # Configure Nginx
    configure_nginx()

    # Create the .env file
    create_env_file(root_password, db_user, db_password, db_name)

    # Run Flask app
    run_command("python hello.py")

if __name__ == "__main__":
    main()

