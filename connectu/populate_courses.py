import json
import os
from app import db, Course, app

# Path to your downloaded JSON file
JSON_FILE = "courses.json"  # replace with your actual file path

if not os.path.exists(JSON_FILE):
    print(f"Error: {JSON_FILE} not found!")
    exit(1)

# Load JSON data
with open(JSON_FILE, "r") as f:
    data = json.load(f)

# Make sure we're in the application context
with app.app_context():
    # Create tables if they don't exist
    db.create_all()

    # Optional: clear existing courses
    # db.session.query(Course).delete()
    # db.session.commit()

    count = 0
    for course_id, course_info in data.items():
        try:
            course_code = "_".join(course_info["course_reference"]["subjects"]) + f" {course_info['course_reference']['course_number']}"
            title = course_info.get("title", "")
            description = course_info.get("description", "")
            subjects = ",".join(course_info["course_reference"]["subjects"])
            prerequisites = course_info.get("prerequisites", {}).get("prerequisites_text", "")

            # Check if course already exists
            existing = Course.query.filter_by(course_code=course_code).first()
            if existing:
                continue

            course = Course(
                course_code=course_code,
                title=title,
                description=description,
                subjects=subjects,
                prerequisites=prerequisites
            )
            db.session.add(course)
            count += 1

        except KeyError as e:
            print(f"Skipping course {course_id} due to missing key: {e}")

    db.session.commit()
    print(f"Added {count} new courses to the database.")
