from flask import Flask

hello = Flask(__name__)

@app.route('/')
def home():
    return "Hello, Flask on Ubuntu Server!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

