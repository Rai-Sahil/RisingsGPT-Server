#api_flask_server.py

import os
import openai
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from api_call_1_question_generation import gpt_response_1_question_generation
from api_call_2_answer_elaboration import gpt_response_2_answer_elaboration
from api_call_3_essay_generation import gpt_response_3_essay_generation
from api_call_4_modify_essay_quality import gpt_response_4_essay_modification


def load_env(file_path='.env'):
    try:
        with open(file_path, 'r') as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    except FileNotFoundError:
        pass  # .env file not found, continue without loading environment variables


# Load environment variables from .env file
load_env()

# Set OpenAI API key
openai.api_key = os.environ.get("OPEN_API")
gpt_model = "gpt-4"
# gpt_model = "gpt-3.5-turbo"

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Read prompts from essay_generation_prompts.txt
def load_content_from_file(filename):
    with open(filename, 'r') as file:
        content = file.read().strip().split("###")
        content = [item.strip() for item in content if item]

        # Create a dictionary for easier assignment
        content_dict = {}

        for item in content:
            if item.startswith("user_msg_content"):
                content_dict["user_msg_content"] = item.split("\n", 1)[1].strip()
            elif item.startswith("automated_prompt"):
                content_dict.setdefault("automated_prompts", []).append(item.split("\n", 1)[1].strip())

    return content_dict

# Read prompts from essay_quality_prompts.txt
def load_content_from_file_quality(filename):
    with open(filename, 'r') as file:
        content = file.read().strip().split("###")
        content = [item.strip() for item in content if item]

        # Initialize the dictionary
        quality_dict = {"8": {}, "7": {}, "5": {}}

        for item in content:
            if item.startswith("8_quality_user"):
                quality_dict["8"]["user"] = item.split("\n", 1)[1].strip()
            elif item.startswith("8_quality_assistant"):
                quality_dict["8"]["assistant"] = item.split("\n", 1)[1].strip()
            elif item.startswith("7_quality_user"):
                quality_dict["7"]["user"] = item.split("\n", 1)[1].strip()
            elif item.startswith("7_quality_assistant"):
                quality_dict["7"]["assistant"] = item.split("\n", 1)[1].strip()
            elif item.startswith("5_quality_user"):
                quality_dict["5"]["user"] = item.split("\n", 1)[1].strip()
            elif item.startswith("5_quality_assistant"):
                quality_dict["5"]["assistant"] = item.split("\n", 1)[1].strip()

    return quality_dict

# Flask route for question generation
@app.route("/question-generation", methods=["POST"])
def generate_questions_flask():
    try:
        data = request.json
        essay_length = data.get("essay_length")
        essay_question = data.get("essay_question")
        personal_summary_points = data.get("personal_summary_points")

        # Make sure necessary data is provided
        if not (essay_length and essay_question and personal_summary_points):
            raise ValueError('Missing required data')

        # Fetch the GPT response for the provided question and points
        gpt_response = gpt_response_1_question_generation(essay_question, personal_summary_points, essay_length)

        if not gpt_response:
            raise ValueError('Failed to generate questions')

        return jsonify({"questions": gpt_response})

    except Exception as e:
        # Log the exception (optional)
        app.logger.error(f'Error: {e}')

        # Return a 400 Bad Request error with a JSON error message
        return jsonify({'error': str(e)}), 400

@app.route("/answer-elaboration", methods=["POST"])
def answer_elaboration_flask():
    try:
        data = request.json
        essay_length = data.get("essay_length")
        essay_question = data.get("essay_question")
        answered_questions = data.get("answered_questions")

        # Make sure necessary data is provided
        if not (essay_length and essay_question and answered_questions):
            raise ValueError('Missing required data')

        # Fetch the GPT response for the provided question and answers
        gpt_response = gpt_response_2_answer_elaboration(essay_question, answered_questions, essay_length)

        if not gpt_response:
            raise ValueError('Failed to generate elaboration')

        return jsonify({"elaboration": gpt_response})

    except Exception as e:
        # Log the exception (optional)
        app.logger.error(f'Error: {e}')

        # Return a 400 Bad Request error with a JSON error message
        return jsonify({'error': str(e)}), 400

# Flask route for essay generation
@app.route("/essay-generation", methods=["POST"])
def generate_essay_flask():
    
    try:
    
        data = request.json
        essay_question = data.get("essay_question")
        answered_gpt_questions = data.get("answered_gpt_questions")
        essay_length = data.get("essay_length")

        # Load content
        loaded_content = load_content_from_file('essay_generation_prompts.txt')

        # Assigning variables
        user_msg_content = loaded_content["user_msg_content"]
        automated_prompts = loaded_content["automated_prompts"]

        # Format message with variables
        user_msg_content = user_msg_content.format(
            essay_length=essay_length,
            essay_question=essay_question,
            answered_personal_questions=answered_gpt_questions
        )

        formatted_automated_prompts = []

        # Format prompts with variables
        for prompt in automated_prompts:
            formatted_prompt = prompt.format(
                essay_length=essay_length,
                essay_question=essay_question,
                answered_personal_questions=answered_gpt_questions
            )
            formatted_automated_prompts.append(formatted_prompt)


        # Initial system message
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant."
            },
            {
                "role": "user",
                "content": user_msg_content
            }
        ]



        # Get the initial response
        print(messages)
        initial_response = gpt_response_3_essay_generation(messages)
        user_prompts = [user_msg_content]
        responses = [initial_response]

        # Iterate over each automated prompt, send it to the API, and append the response to the responses list
        for prompt in formatted_automated_prompts:
            messages.append({"role": "user", "content": prompt})
            user_prompts.append(prompt)
            response = gpt_response_3_essay_generation(messages)
            messages.append({"role": "assistant", "content": response})
            responses.append(response)
            messages = messages[-10:]

        return jsonify({"GPTResponses": responses, "UserPrompts": user_prompts})
    
    except Exception as e:
        # Log the exception (optional)
        app.logger.error(f'Error: {e}')

        # Return a 400 Bad Request error with a JSON error message
        return jsonify({'error': str(e)}), 400

# Flask route for quality modification
@app.route("/essay-quality-modifier", methods=["POST"])
def modify_essay_flask():
    
    try:
        data = request.json
        current_essay = data.get("current_essay")
        essay_quality = data.get("essay_quality")
        essay_rating = ""

        # Load content
        loaded_content = load_content_from_file_quality('essay_quality_prompts.txt')

        # Assigning variables
        user_msg_content = ""
        automated_prompts = ""

        # Load prompts based on user essay quality choice
        if essay_quality == "Good":
            print("Good.")

            user_msg_content = loaded_content["8"]["user"]
            automated_prompts = loaded_content["8"]["assistant"]
        if essay_quality == "Decent":
            print("Decent.")

            user_msg_content = loaded_content["7"]["user"]
            automated_prompts = loaded_content["7"]["assistant"]
        if essay_quality == "Poor":
            print("Poor.")

            user_msg_content = loaded_content["5"]["user"]
            automated_prompts = loaded_content["5"]["assistant"]

        print(user_msg_content)
        print(automated_prompts)

        # Initial system message
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant."
            },
            {
                "role": "user",
                "content": user_msg_content
            },
            {
                "role": "assistant",
                "content": automated_prompts
            },
            {
                "role": "user",
                "content": current_essay
            },
        ]

        # Get the initial response
        print(messages)
        initial_response = gpt_response_4_essay_modification(messages)

        print(initial_response)

        return jsonify({"GPTResponse": initial_response})
    
    except Exception as e:
        # Log the exception (optional)
        app.logger.error(f'Error: {e}')

        # Return a 400 Bad Request error with a JSON error message
        return jsonify({'error': str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True, port=5000)
