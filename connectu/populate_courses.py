import json
import requests
from app import app, db, Course

STATIC_URL = "https://static.uwcourses.com/courses.json"

def populate_courses():
    # Fetch the full course dump
    resp = requests.get(STATIC_URL)
    if resp.status_code != 200:
        print("Failed to download course data")
        return

    courses_data = resp.json()
    print(f"Fetched {len(courses_data)} courses.")

    with app.app_context():
        db.create_all()
        for course_code, data in courses_data.items():
            # course_code example: COMPSCI_300
            subjects = "/".join(data["course_reference"]["subjects"])
            prerequisites = str(data.get("prerequisites", {}))
            course = Course(
                course_code=course_code,
                title=data.get("title", ""),
                description=data.get("description", ""),
                subjects=subjects,
                prerequisites=prerequisites
            )
            db.session.add(course)

        db.session.commit()
        print("All courses added to the database!")

if __name__ == "__main__":
    populate_courses()
