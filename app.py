from flask import Flask, jsonify

app = Flask(__name__)

@app.route("/onboarding/ariel", methods=["GET"])
def onboarding_ariel():
    return jsonify({
        "name": "Ariel",
        "self_intro": "Hi! I'm Ariel, part of the 8th Tech cohort, and I will be joining the TPET team as a backend developer. I enjoy listening to K-pop and playing the piano. Looking forward to working with everyone!"
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)


