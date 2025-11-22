import xml.etree.ElementTree as ET
from app import app, db
from models import Course
import os

# Path to the database
db_path = os.path.join(os.path.dirname(__file__), 'instance', 'connectu.db')

# Make sure app is configured correctly
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Path to your XML file
xml_file = os.path.join(os.path.dirname(__file__), 'courses_sitemap.xml')

def load_courses_from_xml(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    courses_data = []
    ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

    for url in root.findall('ns:url', ns):
        loc = url.find('ns:loc', ns).text
        course_code = loc.split('/')[-1]  # get last part of URL
        courses_data.append({
            'course_code': course_code,
            'title': '',         # Fill in if you have titles
            'description': ''    # Fill in if you have descriptions
        })
    return courses_data

def populate_courses():
    courses_data = load_courses_from_xml(xml_file)

    with app.app_context():
        # Clear old courses
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

if __name__ == "__main__":
    populate_courses()
