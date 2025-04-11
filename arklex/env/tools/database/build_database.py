import sqlite3
import argparse
from pathlib import Path
import os
from arklex.env.tools.tools import register_tool

description = "After the user answers an interview question, create an sqlite database recording the candidate's id, question asked and their response."

slots = [
    {
        "name": "candidate_id",
        "type": "string",
        "description": "The email of the candidate, such as 'something@example.com'.",
        "prompt": "In order to proceed, please provide the email you used to apply for the role",
        "required": True
    },
    {
        "name": "applied_role",
        "type": "string",
        "description": "The role the candidate applied for.",
        "prompt": "What role did you apply for?",
        "required": True

    },
    {
        "name": "question_text",
        "type": "string",
        "description": "The interview question that was asked, which was gotten using the role_question_worker.",
        "prompt": "",
        "required": True

    },
    {
        "name": "response_text",
        "type": "string",
        "description": "The response of the candidate to the question asked.",
        "prompt": "",
        "required": True

    },
    {
        "name": "score",
        "type": "int",
        "description": "The score of the candidate's response based on accuracy, clarity, Relevance, Structure and Completeness. Each criteria is over 10, sum to over 50.",
        "prompt": "",
        "required": True

    }
]

errors = [
    "Error"
]

outputs = []

@register_tool(description, slots, outputs, lambda x: x not in errors)
def build_database(candidate_id: str, applied_role: str, question_text: str, response_text: str, score: int) -> str:
    try:
        base_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        db_path = base_dir / "interview_db.sqlite"
        # if os.path.exists(db_path):
            # os.remove(db_path)
        # Creating the database with a .sqlite extension
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create tables based on the provided schema
        cursor.execute('''
            CREATE TABLE interview_log (
                candidate_id TEXT,
                applied_role TEXT,
                question_text TEXT,
                response_text TEXT,
                score INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (candidate_id, question_text)
            )
        ''')

        cursor.execute("""
                            INSERT INTO interview_log (candidate_id, applied_role, question_text, response_text, score, timestamp)
                            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """,(candidate_id, applied_role, question_text, response_text, score)
        )
        conn.commit()
        conn.close()

    except Exception as e:
        return f"Error: {e}"
    
    return "Success"
"""
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder_path", required=True, type=str, help="location to save the documents")
    args = parser.parse_args()

    if not os.path.exists(args.folder_path):
        os.makedirs(args.folder_path)

    build_database(args.folder_path)
"""