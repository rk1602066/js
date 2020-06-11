import time

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route('/posts',methods=["POST"])
def posts():
    start = int(request.form.get('start') or 0)
    end = int(request.form.get('end') or start+9)
    posts = []
    for i in range(start,end+1,1):
        posts.append(f'post # {i}')
    time.sleep(1)
    return jsonify(posts)


if __name__ == "__main__":
    app.run(debug=True)
