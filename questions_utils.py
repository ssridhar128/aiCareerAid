import json
from groq import Groq
import os

api_key = os.getenv("GROQ_API_KEY")
def mock_inter(res, job, industry, level):
    output_format = {
        "question1": [""],
        "question2": [""],
        "question3": [""],
        "question4": [""],
        "question5": [""],
        "question6": [""],
        "question7": [""],
        "question8": [""],
        "question9": [""],
        "question10": [""]
    }

    expected_output = json.dumps(output_format, indent=4)
    
    client = Groq(api_key=api_key)


    system_prompt ="""
    You are a mock interviewer. Use the below industry, job information, and level, as well as provided resume information of the user to generate 10 mock interview questions. Return only valid JSON with no extra text.
    """
    
    user_prompt = f"""
    ### Inputs
    Industry: {industry}
    level: {level}
    Applicant for: {job}
    User Relevant Resume Sections (in JSON format): {res}
    
    ### Instructions
    You are to help the user get a job in the mentioned industry, level and position.
    First, use these criteria to get information on the industry and job, like necessary skills, qualifications, and ideal candidate metrics
    Next, parse the Relevant resume info to find the user's strengths(stuff to talk more about in interviews) and weaknesses as per the above industry and job info
    Now, Using the metrics found and the strengths and weaknesses, generate a list of mock interview questions that ensure that the user can capitalize on their strenghts and shield their weaknesses and be prepared for an interview.
    Ensure question difficulty and relevance is based on levels (intern, junior, etc is lower level, vs senior, manager, etc is higher)

    Make Sure to get 10 Questions, 60-70 percent of which should be role and industry specific, rest should be behavioral or other type questions that hiring managers would want
    Behavioral questions are where the candidate must describe past experiences or situations, and how that impacts their skills, abilities, and character. These are not always industry specific.
    An example of a behavioral question is: Tell me about a time when you realized you needed a deeper level of subject matter expertise to do your job well. What did you do about it? What was the outcome? Is there anything you would have done differently?

    Remember to place this exactly in the specified format, with no other text whatsoever. Remember to get 10 full questions

    ### Context
    "Industry" is usually the broader field in which the applicant is applying in 
    "Job" is the specific position in the industry they want
    "Level" is the type of job and amount of experience needed

    ### Expected Output(exactly as specified below, no other text whatsoever)
    {expected_output}
    
    """
    messages=[
        { "role": "system", "content": system_prompt },
        { "role": "user", "content": user_prompt }
    ]

    chat_completion = client.chat.completions.create(
        messages= messages,
        model="gemma2-9b-it", 
        temperature=0.2,         # deterministic output
        max_tokens=7000,
        stop=["###"],            # optional: stops after expected output
        seed=700,                 # optional: makes output repeatable
        response_format={ "type": "json_object", "json_object": expected_output }  # ensures output is in JSON format
    )

    messages.append({ "role": "assistant", "content": chat_completion.choices[0].message.content})
    print("User prompt:\n", user_prompt) #debug to remove
    print("Model reply:\n", chat_completion.choices[0].message.content)
    return chat_completion.choices[0].message.content
