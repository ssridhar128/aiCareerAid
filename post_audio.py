import json
import os
from groq import Groq

api_key = os.getenv("GROQ_API_KEY")

def feedback(question, response, energy, entropy, zcr, resume_info):
    client = Groq(api_key=api_key)
    expected_output = {
        "feedback": ""
    }
    system_prompt = """
    You are a mock interviewer giving feedback. Use the text translation and information about candidates audio response, like their energy and confidence, to create response. Also the question they answered is provided. 
    Return this in a PARAGRAPH only in valid JSON format!
    """

    user_prompt = f"""
    ### Input
    resume: {resume_info}
    Question thread: {question}
    Response thread: {response}
    Energy levels of candidate(energy): {energy}
    Randomness of the persons tone(entropy): {entropy}
    Clearity of voice(zcr): {zcr}
    
    ### Context
    resume has the user's resume information
    Question thread has either one or two questions asked (base questions and its follow up)
    Response thread has the answer to these  questions in order
    the energy, entropy, and zcr values are also lists that are in the same order as the question thread. i.e first zcr value is mea zcr for first response, etc.
    Energy, entropy, and zcr are all lists as they have 2 inputs (one for each question) 
    IMPORTANT: if there was only one question in the question thread, then only use the first index for each of ZCR, entropy, and energy lists


    ### Instructions
    First, read through the entire response. Then, write detailed feedback on the response using the topics below as guidance. 
    Be sure to include **specific suggestions** on how the response could be improved (e.g., rephrasing, providing examples, elaborating further).
    If this is not the first response in the full conversation, be sure to give feedback with that context in mind. 

    Topics to cover in your feedback:
    1) Was the response directed toward the question, or did the candidate go off-topic?
    2) Was the explanation clear and easy to follow?
    3) Did the response go beyond surface-level ideas?
    4) Were the best examples or reasoning from resume used to support claims?
    5) Was there anything specifc resume they could have used? 

    Next, assess the candidate's **demeanor** based on the tone of their response:
    - Was the energy level appropriate?
    - Did the tone feel too random or inconsistent?
    - Was the communication clear and professional?

    Offer advice on any adjustments they should make to their tone, clarity, or energy level.
    Compile all of this into 2 or 3 sentences of feedback.
    

    ### 
    #Output it exactly as in the below format, all as the value for the key "feedback", do not create any other keys.
    ### Expected Output
    {expected_output}
    ###
    """
    chat_completion = client.chat.completions.create(
        messages=[
        { "role": "system", "content": system_prompt },
        { "role": "user", "content": user_prompt }],
        model="llama-3.1-8b-instant", 
        temperature=0.2,        
        max_tokens=2000,
        stop=["###"],           
        seed=700,
        response_format={ "type": "json_object", "json_object": expected_output }             
    )
    return chat_completion.choices[0].message.content

def follow_up_thread(question, response, res, job, industry, level):
    client = Groq(api_key=api_key)
    system_prompt = """
    You are a mock interviewer who wants to test if the user is a good candidate for the job. Use the context and the user's interview response to assess if they are to be selected.
    Return this only in valid JSON format!
    """

    expected_output = { "new_q": ""}

    user_prompt = f"""
    ### Input
    Resume: {res}
    Job: {job}
    Industry: {industry}
    level: {level}
    Question thread: {question}
    Response thread: {response}

    ### Context
    First, use these criteria to get information on the industry, job and level, like necessary skills, qualifications, and ideal candidate metrics
    Next, parse the Relevant resume info to find the user's strengths(stuff to talk more about in interviews) and weaknesses as per the above industry and job info
    In this interview, You want to address the user's strengths and weaknesses, and ensure they are a good candidate for the job. 
    None of these metrics or strengths, weaknesses, etc should be returned in the output, just used as context.

    "Question thread" is the list of questions in this question thread
    "Response thread" is the list of responses to the question thread, in order.
    
    
    ### Instructions
    Read through the question and response thread. If the user has not sufficiently answered the question, 
    generate a follow-up question that digs deeper into the topic, or clarifies the user's response. Otherwise, 
    return an EMPTY string.

    REMEMBER: You only get one follow-up question, so if you ask one, make sure it is a good one that will help the user improve their response
    and that it is detailed enough to not need multiple more follow-up questions.

    ### Expected Output
        {expected_output}
    ###
    """
    chat_completion = client.chat.completions.create(
        messages=[
        { "role": "system", "content": system_prompt },
        { "role": "user", "content": user_prompt }],
        model="llama-3.1-8b-instant", 
        temperature=0.2,         # deterministic output
        max_tokens=700,
        stop=["###"],            # optional: stops after expected output
        seed=700,
        response_format={ "type": "json_object", "json_object": expected_output }                 # optional: makes output repeatable
    )

    return chat_completion.choices[0].message.content

def shorten(res, questions, responses):
    client = Groq(api_key=api_key)
    system_prompt = """
    You are a summarizer. You are to shorten information about a resume and interview questions and responses as much as possible, while still retaining the most important information.
    Return this only in valid JSON format!
    """

    expected_output = { 
        "resume": "",
        "questions": [""],
        "responses": [""] 
    }

    user_prompt = f"""
    ### Input
    Resume: {res}
    Question thread: {questions}
    Response thread: {responses}

    ### Context
    Reduce the size of resume as much as possible, while still retaining the most important information.
    Remove any unnecessary information text, like dates, locations, contact information, etc. Get rid of full sentences, only keeping
    bullet points and key phrases. HOWEVER, VERY IMPORTANT: Do not remove any of the core information. When choosing what to keep, act as a hiring manager
    and keep only the most relevant information that would be useful in an interview.

    For both question and response threads, do not change the size of the lists. However, for each question and each response,
    shorten the text by removing uneccesary words and getting rid of full sentences, only keeping a few key phrases that convey
    the same information.

    ### Expected Output
        {expected_output}
    ###
    """