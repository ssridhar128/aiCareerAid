import PyPDF2
import os
from groq import Groq
import json
import re

def extract_text(pdf_path):
    with open(pdf_path, 'rb') as pdf:
        reader = PyPDF2.PdfReader(pdf, strict=False)
        pdf_text = []

        for i,page in enumerate(reader.pages):
            content = page.extract_text()
            if content:
                cleaned_lines = []
                lines = content.splitlines()
                for line in lines:
                    stripped_line = line.strip()
                    if stripped_line:
                        cleaned_lines.append(stripped_line)

                cleaned = '\n'.join(cleaned_lines)
                pdf_text.append(f"--- Page {i+1} ---\n{cleaned}")

        return '\n\n'.join(pdf_text)
    
def res_sum(job, resume_text):
    client = Groq(api_key='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')

    system_prompt = """
    You are a resume parsing assistant. Extract structured data from resumes that is most relevant to the job they are applying for. Return only valid JSON with no extra text.
    """

    user_prompt = f"""
    ### Instructions
    Applicant for: {job}
    Parse the below resume in its entirety. Identify which skills are most relevant to the above job. 
    Also scan through the full descriptions of each job experience mentioned and condense it to the parts that are most relevant.
    Put this below in the requested format and specfications)
    - full_name (string)
    - skills (list of strings)
    - job_experience (list of relevant experiences based on the job they are applying to)
        - company (string)
        - title (string)
        - duration (string)
        - description (string, 2 sentence summarizing what the person did after reading the entire experience)

    ### Context
    "Skills" often appear in bullet points or after section headers like "Technical Skills".
    "Job Experience" includes company names, job titles, durations of employment, and what they did.

    ### Input
    {resume_text}

    ### Expected Output
    {{{{  
        "full_name": "",
        "skills": [],
        "job_experience": []
     }}}}
    ###
    """

    chat_completion = client.chat.completions.create(
        messages=[
            { "role": "system", "content": system_prompt },
            { "role": "user", "content": user_prompt }
        ],
        model="gemma2-9b-it", 
        temperature=0.2,         # deterministic output
        max_tokens=700,
        stop=["###"],            # optional: stops after expected output
        seed=700                 # optional: makes output repeatable
    )
    
    raw_output = chat_completion.choices[0].message.content
    return raw_output