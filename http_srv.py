from flask import Flask, json
api = Flask(__name__)

@api.route("/", methods=["GET"])
def get_home():
    return "running"