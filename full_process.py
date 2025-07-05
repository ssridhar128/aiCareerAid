import os
import json
import fitz
from io import BytesIO
import firebase_admin
from firebase_admin import credentials, firestore, auth as fb_auth, storage
from flask import Flask, Blueprint, app, request, jsonify, redirect, render_template
from werkzeug.utils import secure_filename
from utils.post_audio import feedback, follow_up_thread
from utils.resume_utils import extract_text, res_sum
from utils.questions_utils import mock_inter
from utils.audio import record, audio_features, groqInput, audio_to_text
from flask import session
import subprocess

app.secret_key = os.getenv("SESSION_SECRET_KEY")

full_process_bp = Blueprint("full", __name__)
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf", "wav"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(pdf_file):
    text = ""
    with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text.strip()

@full_process_bp.route("/resume", methods=["POST"])
def resume():
    user_email = session["user_email"]
    db = firestore.client()
    doc = db.collection("users").document(user_email).get()
    job = request.form.get("job")
    industry = request.form.get("industry")
    level = request.form.get("level")
    if not doc.exists or "resume_filename" not in doc.to_dict():
        return redirect("/resume-upload")
    if not job or not industry or not level:
        return jsonify({"error": "Missing job, industry, or level."}), 400
    user_data = doc.to_dict()
    filename = user_data["resume_filename"]
    bucket = storage.bucket()
    blob = bucket.blob(f"resumes/{user_email}/{filename}")
    resume_bytes = blob.download_as_bytes()
    
    resume_text = extract_text_from_pdf(BytesIO(resume_bytes))
    summary_json = res_sum(job, resume_text)
    
    session["resume"] = summary_json
    session["job"] = job
    session["industry"] = industry
    session["level"] = level

    return redirect("/full/questions-loading")

@full_process_bp.route("/generate-questions")
def questions():
    summary_json = session.get("resume")
    job = session.get("job")
    industry = session.get("industry")
    level = session.get("level")

    summary_str = json.dumps(summary_json)
    question_str = mock_inter(summary_str, job, industry, level)
    questions_json = json.loads(question_str)
    session["questions"] = questions_json
    session["responses"] = {}
    session["feedbacks"] = {}
    session["curr_index"] = 1
    session["zcr"] = []
    session["entropy"] = []
    session["energy"] = []

    return redirect("/full/questions")

@full_process_bp.route("/record", methods=["POST"])
def audio_recording():
    audio_file = request.files.get("audio")
    if not audio_file:
        console.log("NO AUDIO FILE")
        return jsonify({"error": "No audio uploaded"}), 400

    
    webm_path = os.path.join(UPLOAD_FOLDER, "temp.webm")
    wav_path = os.path.join(UPLOAD_FOLDER, "temp.wav")
    audio_file.save(webm_path)

    zcr = session.get("zcr", [])
    energy = session.get("energy", [])
    entropy = session.get("entropy", [])

    subprocess.run(["ffmpeg", "-i", webm_path, wav_path, "-y"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    store = audio_features(wav_path)
    zcr.append(store[0])
    energy.append(store[1])
    entropy.append(store[2])
    session["zcr"] = zcr
    session["energy"] = energy
    session["entropy"] = entropy

    responses = session.get("responses")
    q_key = f"question{session.get('curr_index')}"
    answer = audio_to_text(wav_path).text
    print(f"AHHHHH q NAME: {answer}")
    
    responses.setdefault(q_key, []).append(answer)
    session["responses"] = responses

    return jsonify({"message": "Audio processed successfully"})

@full_process_bp.route("/followupfeedback", methods=["GET"])
def post_quest():
    index = session.get("curr_index")
    questions = session.get("questions")
    responses = session.get("responses")

    q_key = f"question{index}"
    q_thread = questions.get(q_key, [])
    r_thread = responses.get(q_key, [])

    if len(q_thread) == 1:
        # Only original question so far → generate follow-up
        raw = follow_up_thread(q_thread, r_thread,
                                 session.get("resume"),
                                 session.get("job"),
                                 session.get("industry"),
                                 session.get("level"))
        parsed = json.loads(raw) if isinstance(raw, str) else raw
        new_q = parsed["new_q"]
        if new_q:
            q_thread.append(new_q)
            questions[q_key] = q_thread
            session["questions"] = questions
            return redirect("/full/questions")  # go back to UI for follow-up recording

    # Otherwise, it's time for feedback
    fback = feedback(q_thread, r_thread,
                     session.get("energy"),
                     session.get("entropy"),
                     session.get("zcr"),
                     session.get("resume"))
    feedbacks = session.get("feedbacks", {})
    feedbacks[q_key] = fback
    session["feedbacks"] = feedbacks

    return jsonify({
        "Message": f"Feedback saved for question {index}. Click next to continue.",
        f"{q_key} feedback": fback
    })

@full_process_bp.route("/current_question", methods=["POST"])
def get_q():
    index = session.get("curr_index")

    if (index < 1 or index > 10):
        return jsonify({"error": "No more questions"}), 404
    
    quest = session.get("questions")[f"question{index}"]
    return quest

@full_process_bp.route("/next_question", methods=["GET"])
def next_q():
    index = session.get("curr_index")

    if (index+1 > 10):
        return jsonify({"error": "No more questions"}), 404
    
    session["curr_index"] = index +1

    session["zcr"] = []
    session["energy"] = []
    session["entropy"] = []
    return jsonify({"message": f"Moved to question {index + 1}"})

@full_process_bp.route("/summary")
def summary_page():
    return render_template("summary.html")

@full_process_bp.route("/summary_data")
def summary_data():
    return jsonify({
        "questions": session.get("questions", {}),
        "responses": session.get("responses", {}),
        "feedbacks": session.get("feedbacks", {})
    })






    
    
# @app.route("/main")
# def main():
#     job_position = "Software Engineer"
#     resume = extract_text("Unnati_resume.pdf")
#     resume_info = res_sum(job_position, resume)
#     resume_info = shorten(resume_info, [], [])
#     print(resume_info)
#     industry_type = "Tech"
#     experience_level = "Intern"

#     questions = eval(mock_inter(resume_info, job_position, industry_type, experience_level))
#     responses={}
#     feedbacks = {}
    
#     print(questions)
#     for i in range(1, 3):
#         zcr = [-1,-1]
#         energy = [-1,-1]
#         entropy = [-1,-1]

#         question_key = f"question{i}"
#         if question_key in questions:
#             question_text = questions[question_key][0]
#             print(f"Question {i}: {question_text}")
#             record()
#             zcr[0], energy[0] , entropy[0]  = audio_features("answer.wav")
#             responses[question_key] = [audio_to_text("answer.wav")]
#             questions[question_key].append(eval(follow_up_thread(questions[question_key], responses[question_key], resume_info, job_position, industry_type, experience_level))["new_q"])
#             print(questions[question_key][-1])
#             record()
#             zcr[1], energy[1] , entropy[1]  = audio_features("answer.wav")
#             responses[question_key].append(audio_to_text("answer.wav"))
#             feedbacks[question_key] = feedback(questions[question_key], responses[question_key], zcr, energy, entropy, resume_info)  # Example values for energy, entropy, zcr
#             print(feedbacks[question_key])
#     return feedbacks, 200
