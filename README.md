# flask_app
A Python Flask app that runs a bookstore website using Nginx proxy and gUnicorn web server gateway interface.

The process to set up this flask app is as follows:

1. Using the .yaml template from the Github repository, create a stack in the AWS CloudFormation.

2. SSH into Ec2 Ubuntu server using provided ssh .pem key

3. $ git clone https://github.com/jwsnyder3/flask_app

4. $ cd flask_app

5. $ python3 setup_flask_app.py
   Follow along with the prompts

6. Nginx and gUnicorn configuration

7. $ source venv/bin/activate

8. $ sudo nano /etc/nginx/sites-available/flask_app

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

9. $ sudo nano /etc/nginx/nginx.conf
    
    include /etc/nginx/modules-enabled/*;

10. $ sudo nano /etc/hosts

    127.0.0.1   54.242.66.13

11. $ sudo ln -s /etc/nginx/sites-available/flask_app /etc/nginx/sites-enabled
    $ sudo nginx -t
    $ sudo systemctl reload nginx
    
12. sudo systemctl reload nginx

13. Test localhost for server:
    $ python3 app.py

14. gunicorn --bind 0.0.0.0:5000 wsgi:app

15. Make sure the static folder is uploaded to the S3 bucket.
