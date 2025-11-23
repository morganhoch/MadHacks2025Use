import xml.etree.ElementTree as ET
import os
import requests
from dotenv import load_dotenv
from app import app
from models import db, Course

# Load environment variables
load_dotenv()
MADGRADES_API_TOKEN = os.getenv("MADGRADES_API_TOKEN")
BASE_URL = "https://api.madgrades.com/v1"

# Path to XML sitemap
xml_file = os.path.join(os.path.dirname(__file__), 'courses_sitemap.xml')

# Function to parse course codes from XML
def load_courses_from_xml(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    courses_data = []
    ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

    for url in root.findall('ns:url', ns):
        loc = url.find('ns:loc', ns).text
        course_code = loc.split('/')[-1]  # last part of URL
        courses_data.append({'course_code': course_code})
    return courses_data

# Function to get Madgrades UUID and info for a course code
def get_madgrades_info(course_code):
    headers = {"Authorization": f"Token token={MADGRADES_API_TOKEN}"}
    params = {"query": course_code}
    response = requests.get(f"{BASE_URL}/courses", headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        if data.get("data"):
            course_data = data["data"][0]  # take first match
            return {
                "uuid": course_data.get("uuid"),
                "title": course_data.get("name", ""),
                "description": course_data.get("description", "")
            }
    return {"uuid": None, "title": "", "description": ""}

# Main function to populate courses
def populate_courses():
    courses_data = load_courses_from_xml(xml_file)

    with app.app_context():
        # Delete existing courses
        print("Deleting existing courses...")
        db.session.query(Course).delete()
        db.session.commit()

        # Add new courses
        print(f"Adding {len(courses_data)} courses with Madgrades info...")
        for c in courses_data:
            madgrades_info = get_madgrades_info(c['course_code'])
            course = Course(
                course_code=c['course_code'],
                title=madgrades_info["title"],
                description=madgrades_info["description"],
                madgrades_uuid=madgrades_info["uuid"]
            )
            db.session.add(course)
        db.session.commit()
        print("Courses repopulated successfully!")

if __name__ == "__main__":
    populate_courses()
