import os
import subprocess
import secrets
import tempfile

def run_command(command, check=True, use_venv=False):
    """Run a shell command."""
    if use_venv:
        command = f"venv/bin/{command}"  # Use venv's Python or pip explicitly
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0 and check:
        print(f"Error: {result.stderr}")
        exit(result.returncode)
    print(result.stdout)

def generate_secret_key():
    """Generate a random secret key."""
    return secrets.token_urlsafe(32)

def create_env_file():
    """Create or append to the .env file and secure it."""
    db_user = input("Enter the MySQL username for your Flask app: ")
    db_password = input("Enter the password for this MySQL user: ")
    db_name = input("Enter the name of the database: ")
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

    # Write the configuration file with elevated privileges
    temp_file_path = "flask_app_nginx"
    with open(temp_file_path, "w") as temp_file:
        temp_file.write(nginx_config)

    run_command(f"sudo mv {temp_file_path} {nginx_config_path}")
    run_command(f"sudo ln -sf {nginx_config_path} {symlink_path}")
    run_command("sudo nginx -t")
    run_command("sudo systemctl restart nginx")

    print(f"Nginx configured for domain/IP: {domain_or_ip}")

def configure_ufw():
    """Configure UFW to allow necessary ports."""
    print("Configuring UFW firewall...")
    try:
        # Allow common ports
        run_command("sudo ufw allow 22")  # SSH
        run_command("sudo ufw allow 80")  # HTTP
        run_command("sudo ufw allow 443")  # HTTPS
        run_command("sudo ufw allow 3306")  # MySQL
        run_command("sudo ufw allow 5000")  # Flask
        
        # Enable UFW without interactive prompts
        run_command("sudo ufw --force enable")

        print("UFW configured and enabled.")
    except RuntimeError as e:
        print(f"Error configuring UFW: {e}")

def run_mysql_secure_installation():
    """Automate the mysql_secure_installation process."""
    print("Running MySQL secure installation...")

    # Install the expect package if not already installed
    run_command("sudo apt install -y expect")

    # Define the expect script for mysql_secure_installation
    expect_script = """
    spawn sudo mysql_secure_installation
    expect "Press y|Y for Yes, any other key for No" { send "y\\r" }
    expect "Please enter 0 = LOW, 1 = MEDIUM and 2 = STRONG:" { send "0\\r" }
    expect "Press y|Y for Yes, any other key for No" { send "y\\r" }
    expect "Press y|Y for Yes, any other key for No" { send "y\\r" }
    expect "Press y|Y for Yes, any other key for No" { send "y\\r" }
    expect "Press y|Y for Yes, any other key for No" { send "y\\r" }
    interact
    """

    # Save the expect script to a temporary file
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(expect_script.encode())
        temp_file_path = temp_file.name

    # Run the expect script
    run_command(f"expect {temp_file_path}")

    # Clean up the temporary file
    os.remove(temp_file_path)

    print("MySQL secure installation complete.")

def load_env_variables():
    """Manually load environment variables from the .env file."""
    env_file_path = ".env"
    env_vars = {}

    try:
        with open(env_file_path, "r") as env_file:
            for line in env_file:
                # Ignore comments and empty lines
                if line.strip() and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    env_vars[key] = value
                    # Set the environment variable for later use
                    os.environ[key] = value
    except FileNotFoundError:
        print(f"Error: {env_file_path} not found.")
        exit(1)

    return env_vars

def setup_mysql():
    """Configure MySQL, create a user, and populate the database using .env variables."""
    # Load the environment variables from the .env file
    env_vars = load_env_variables()

    # Ensure the necessary environment variables are loaded
    db_name = env_vars.get("DB_NAME")
    db_user = env_vars.get("DB_USER")
    db_password = env_vars.get("DB_PASSWORD")

    if not db_name or not db_user or not db_password:
        print("Error: Missing database configuration in .env file.")
        exit(1)

    run_mysql_secure_installation()

    try:
        # Create database and user commands using the environment variables
        commands = [
            f"CREATE DATABASE IF NOT EXISTS {db_name};",
            f"CREATE USER IF NOT EXISTS '{db_user}'@'localhost' IDENTIFIED BY '{db_password}';",
            f"GRANT ALL PRIVILEGES ON {db_name}.* TO '{db_user}'@'localhost';",
            "FLUSH PRIVILEGES;"
        ]

        for command in commands:
            run_command(f"sudo mysql -u root -e \"{command}\"")

        # Populate the database with SQL.txt if it exists
        if os.path.exists("SQL.txt"):
            print("Populating the database with SQL.txt...")
            run_command(f"sudo mysql -u root {db_name} < SQL.txt")
        
        print("MySQL setup complete.")
    except Exception as e:
        print(f"Error during MySQL setup: {e}")
        exit(1)

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

    # Set up virtual environment
    run_command("python3 -m venv venv")
    print("Virtual environment created.")

    # Install Python dependencies using venv's pip
    run_command("pip install -r requirements.txt", use_venv=True)

    # Configure UFW
    configure_ufw()

    # Configure Nginx
    configure_nginx()

    # Create the .env file
    create_env_file()

    # Set up MySQL
    setup_mysql()

    # Start Flask app
    run_command("python3 hello.py", use_venv=True)

if __name__ == "__main__":
    main()