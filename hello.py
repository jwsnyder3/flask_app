from flask import Flask

hello = Flask(__name__)

@app.route('/')
def home():
    return "Hello, Flask on Ubuntu Server!"

if __name__ == "__main__":
    hello.run(host="0.0.0.0")

