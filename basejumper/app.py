from flask import Flask
app = Flask(__name__)

@app.route("/")
def main():
	return "Nothing to see here..."


if __name__ == "__main__":
	app.debug = True
	app.run()
