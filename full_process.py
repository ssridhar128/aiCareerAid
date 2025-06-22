import os
import json
from flask import Flask, Blueprint, app, request, jsonify, redirect
from werkzeug.utils import secure_filename
from utils.post_audio import feedback, follow_up_thread
from utils.resume_utils import extract_text, res_sum
from utils.questions_utils import mock_inter
from utils.audio import record, audio_features, groqInput, audio_to_text
from flask import session

app.secret_key = os.getenv("SESSION_SECRET_KEY")

full_process_bp = Blueprint("full", __name__)
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf", "wav"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
   
    
@full_process_bp.route("/resume", methods=["POST"])
def resume():
    file = request.files.get("resume")
    job = request.form.get("job")
    industry = request.form.get("industry")
    level = request.form.get("level")

    if not file or not allowed_file(file.filename):
        return jsonify({"error": "Invalid or missing resume file."}), 400
    if not job or not industry or not level:
        return jsonify({"error": "Missing job, industry, or level."}), 400

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    resume_text = extract_text(file_path)
    summary_json = res_sum(job, resume_text)
    
    session["resume"] = summary_json
    session["job"] = job
    session["industry"] = industry
    session["level"] = level
    
    return jsonify({"message": "Resume processed successfully"})

@full_process_bp.route("/question", methods=["GET"])
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

    return jsonify(questions_json)

@full_process_bp.route("/record", methods=["POST"])
def audio_recording(): 
    file_path = record()
    zcr = session.get("zcr", [])
    energy = session.get("energy", [])
    entropy = session.get("entropy", [])

    store = audio_features(file_path)
    zcr.append(store[0])
    energy.append(store[1])
    entropy.append(store[2])
    session["zcr"] =zcr
    session["energy"] = energy
    session["entropy"] =entropy
    responses = session.get("responses")
    q_key = f"question{session.get('curr_index')}"
    responses.setdefault(q_key, []).append(audio_to_text(file_path))
    session["responses"] = responses

    return jsonify({"message": "Audio processed successfully"})

@full_process_bp.route("/followupfeedback", methods=["GET"])
def post_quest():
    questions = session.get("questions")
    q_thread = questions[f"question{session.get('curr_index')}"]
    responses = session.get("responses")
    r_thread = responses[f"question{session.get('curr_index')}"]
    question = follow_up_thread(q_thread,r_thread, session.get("resume"), session.get("job"), session.get("industry"), session.get("level"))["new_q"]
    if(question != ""):
        q_thread.append(question)
        questions[f"question{session.get('curr_index')}"] = q_thread
        session["questions"] = questions
        return redirect("/record")
    else:
        fback = feedback(q_thread, r_thread, 
                session.get("energy"), session.get("entropy"), session.get("zcr"), session.get("resume"))
        feedbacks = session.get("feedbacks")
        feedbacks[f"question{session.get('curr_index')}"] = fback
        session["feedbacks"] = feedbacks
        return jsonify({
            f"Message": "Feedback saved for question {session.get('curr_index')}. Click next to continue.",
            f"question{session.get('curr_index')} feedback": fback
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