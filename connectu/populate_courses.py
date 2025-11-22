import json
from app import db, Course

# Path to your downloaded JSON file
JSON_FILE = "uw_courses.json"

def load_courses_from_json(json_file):
    with open(json_file, "r") as f:
        data = json.load(f)
    return data

def populate_database(course_data):
    for course_code, course_info in course_data.items():
        # Extract course reference
        course_ref = course_info.get("course_reference", {})
        subjects = course_ref.get("subjects", [])
        course_number = course_ref.get("course_number", "")

        # Create a unique identifier like "COMPSCI 300"
        course_identifier = " ".join(subjects) + f" {course_number}"

        # Extract title and description
        title = course_info.get("title", "No Title")
        description = course_info.get("description", "")

        # Check if the course already exists
        existing_course = Course.query.filter_by(course_identifier=course_identifier).first()
        if existing_course:
            continue  # Skip duplicates

        # Create Course object
        course = Course(
            course_identifier=course_identifier,
            title=title,
            description=description
        )

        # Add to session
        db.session.add(course)

    # Commit all courses to the database
    db.session.commit()
    print(f"Populated {len(course_data)} courses from {JSON_FILE}!")

if __name__ == "__main__":
    # Create tables if they don't exist
    db.create_all()

    # Load JSON and populate DB
    courses = load_courses_from_json(JSON_FILE)
    populate_database(courses)
