# Flask Bookstore App

This is a Python Flask application that runs a dynamic bookstore website, leveraging **Nginx** as a reverse proxy and **gUnicorn** as the web server gateway interface (WSGI). The app is designed to run on an AWS EC2 Ubuntu server with an integrated S3 bucket for static file storage.

---

## **Setup Instructions**

Follow the steps below to set up and deploy the Flask bookstore app.

### **1. Create the AWS CloudFormation Stack**
1. Use the `.yaml` template from the [GitHub repository](https://github.com/jwsnyder3/flask_app).
2. Create a stack in AWS CloudFormation using this template.
3. Note the EC2 public IP or domain name once the stack is created.

---

### **2. Access the EC2 Instance**
   1. SSH into the EC2 Ubuntu server:
   ```bash
   ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP>
   ```
   2. Clone the repository:
   ```bash
   git clone https://github.com/jwsnyder3/flask_app
   cd flask_app
   ```
### **3. Configure the Flask App**
   1. Run the setup script and follow any prompts:
      ```bash
      python3 setup_flask_app.py
   3. Activate the Python virtual environment:
      ```bash
      source venv/in/activate

### **4. Nginx and gUnicorn configuration**
   ***Nginx Reverse Proxy***
   1. Create and edit the Nginx site configuration file:
      ```bash
      sudo nano /etc/nginx/sites-available/flask_app
      ```
   2. Add the following content (replace IP_OR_DOMAIN_NAME with your EC2 public IP or domain name):
      ```nginx
      server {
         listen 80;
         server_name IP_OR_DOMAIN_NAME;

         location / {
            proxy_pass http://127.0.0.1:5000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
         }
      }
      ```
   3. Enable the site and reload Nginx:
      ```bash
      sudo ln -s /etc/nginx/sites-available/flask_app /etc/nginx/sites-enabled
      sudo nginx -t
      sudo systemctl reload nginx
      ```

   **Host Configuration**
   1. Update /etc/hosts:
      ```bash
      sudo nano /etc/hosts
      ```
   2. Add/Change the following line
      ```text
      127.0.0.1 <YOUR_EC2_PUBLIC_IP>
      ```

### **5. Start Flask App**
   1. Test the app locally:
      ```bash
      python3 app.py
      ```
   2. Start the app with gUnicorn:
      ```bash
      gunicorn --bind 0.0.0.0:5000 wsgi:app
      ```

### **6. Upload Static Files**
   Ensure that the ***static*** folder in the Flask app is uploaded to the S3 bucket configured in your AWS CloudFormation stack.
