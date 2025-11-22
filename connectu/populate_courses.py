import json
import os
from app import db, Course, app

# Path to your downloaded JSON file
JSON_FILE = os.path.join(os.path.dirname(__file__), "courses.json")

def extract_course_code(course_reference):
    """
    Convert CourseReference object into a string code, e.g., COMPSCI_300.
    """
    subjects = course_reference.get("subjects", [])
    course_number = course_reference.get("course_number", "")
    return "_".join(subjects) + f"_{course_number}"

def extract_subjects(course_reference):
    """
    Return comma-separated subjects from CourseReference.
    """
    return ", ".join(course_reference.get("subjects", []))

def populate_courses():
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # The actual course data might be nested differently; adjust here if needed.
    # We'll assume top-level 'courses' key contains a list of courses.
    courses_list = data.get("courses", [])
    if not courses_list:
        print("No courses found in JSON.")
        return

    for course_info in courses_list:
        try:
            ref = course_info["course_reference"]
            course_code = extract_course_code(ref)
            subjects = extract_subjects(ref)
            title = course_info.get("title", "")
            description = course_info.get("description", "")

            # Avoid duplicates
            existing = Course.query.filter_by(course_code=course_code).first()
            if existing:
                continue

            course = Course(
                course_code=course_code,
                title=title,
                description=description,
                subjects=subjects,
                prerequisites=""  # optional, fill if you want
            )
            db.session.add(course)
        except Exception as e:
            print(f"Failed to process course: {course_info}. Error: {e}")

    db.session.commit()
    print("Courses populated successfully!")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        populate_courses()
