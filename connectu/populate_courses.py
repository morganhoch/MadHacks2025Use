# populate_courses.py
import xml.etree.ElementTree as ET
from models import Course, db
import os

def populate_courses(app, xml_file):
    """
    Populate the database with courses from an XML sitemap.
    Requires the Flask app context to be passed in.
    """
    tree = ET.parse(xml_file)
    root = tree.getroot()
    courses_data = []
    ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

    # Extract course codes from XML
    for url in root.findall('ns:url', ns):
        loc = url.find('ns:loc', ns).text
        course_code = loc.split('/')[-1]  # get last part of URL
        courses_data.append({
            'course_code': course_code,
            'title': '',         # optional: fill in if you have titles
            'description': ''    # optional: fill in if you have descriptions
        })

    # Use Flask app context for database operations
    with app.app_context():
        # Delete old courses
        print("Deleting existing courses...")
        db.session.query(Course).delete()
        db.session.commit()

        # Add new courses
        print(f"Adding {len(courses_data)} courses...")
        for c in courses_data:
            course = Course(
                course_code=c['course_code'],
                title=c.get('title', ''),
                description=c.get('description', '')
            )
            db.session.add(course)

        db.session.commit()
        print("Courses repopulated successfully!")
