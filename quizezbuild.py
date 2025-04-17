import streamlit as st
import openai
import requests
from datetime import datetime


# ----- Streamlit UI -----
st.title("AI Quiz Generator and Publisher")

# User Inputs
openai_api_key = st.text_input("Enter your OpenAI API Key", type="password")
canvas_api_key = st.text_input("Enter your Canvas API Token", type="password")
canvas_course_id = st.text_input("Enter your Canvas Course ID")
quiz_title = st.text_input("Enter Quiz Title", value="Auto-generated Quiz")
quiz_instructions = st.text_area("Enter Quiz Instructions (supports Markdown)", height=200)
due_date = st.date_input("Due Date")
due_time = st.time_input("Due Time")

num_questions = st.number_input("Number of Questions", min_value=1, max_value=50, value=10)
num_choices = st.number_input("Choices per Question", min_value=2, max_value=6, value=4)
allowed_attempts = st.number_input("Allowed Attempts", min_value=1, value=1)
time_limit = st.number_input("Time Limit (minutes)", min_value=1, value=60)
quiz_content = st.text_area("Quiz Content Prompt")

if st.button("Generate and Publish Quiz"):
    if not (openai_api_key and canvas_api_key and canvas_course_id and quiz_content):
        st.error("Please fill in all required fields.")
    else:
        openai.api_key = openai_api_key
        model_id = 'gpt-4o'

        # Combine date and time into Canvas-compatible timestamp
        due_at = datetime.combine(due_date, due_time).isoformat()

        # Generate quiz questions
        conversation = []
        prompt = (
            f"Based on {quiz_content}, generate {num_questions} multiple choice questions with exactly {num_choices} choices each. "
            f"Each question and each choice should appear on its own line. Use [correct] to mark the right choice. "
            f"For example:\n\n1. What is 2 + 2?\na) 3\nb) [correct]4\nc) 5\nd) 6\n\nDon't put all content in one line."
        )
        conversation.append({"role": "user", "content": prompt})
        response = openai.ChatCompletion.create(model=model_id, messages=conversation)
        output = response.choices[0].message.content.strip()

        # Create Canvas quiz
        headers_canvas = {
            'Authorization': f'Bearer {canvas_api_key}',
            'Content-Type': 'application/json'
        }

        quiz_data = {
            "quiz": {
                "title": quiz_title,
                "description": quiz_instructions,
                "quiz_type": "assignment",
                "allowed_attempts": allowed_attempts,
                "question_count": num_questions,
                "time_limit": time_limit,
                "due_at": due_at,
                "published": True
            }
        }
        quiz_res = requests.post(f'https://canvas.instructure.com/api/v1/courses/{canvas_course_id}/quizzes', headers=headers_canvas, json=quiz_data)
        if quiz_res.status_code != 200:
            st.error("Failed to create quiz on Canvas.")
        else:
            quiz_id = quiz_res.json()['id']

            # Parse questions
            questions = output.split('\n\n')
            if questions[0].startswith("assistant: "):
                questions[0] = questions[0].replace("assistant: ", "")

            parsed_questions = []
            for q in questions:
                lines = q.strip().split('\n')
                if not lines:
                    continue
                q_text = lines[0]
                q_options = lines[1:]
                parsed_questions.append({'text': q_text, 'options': q_options})
# Extract the question part and the choices

            # Add questions to Canvas
            for q in parsed_questions:
                q_text = q['text']
                options = q['options']
                answers = []
                for opt in options:
                    weight = 100 if '[correct]' in opt else 0
                    opt = opt.replace('[correct]', '').strip()
                    if ') ' not in opt:
                        continue
                    _, ans_text = opt.split(') ', 1)
                    answers.append({"answer_text": ans_text, "weight": weight})

                q_payload = {
                    "question": {
                        "question_name": q_text[:50],
                        "question_text": q_text,
                        "question_type": "multiple_choice_question",
                        "points_possible": 1,
                        "answers": answers
                    }
                }
                requests.post(f'https://canvas.instructure.com/api/v1/courses/{canvas_course_id}/quizzes/{quiz_id}/questions', headers=headers_canvas, json=q_payload)

            st.success("Quiz created and published to Canvas!")
