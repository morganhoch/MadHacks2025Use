import xml.etree.ElementTree as ET
from app import db, Course

# Path to your sitemap XML file
xml_file = "courses_sitemap.xml"

# Parse the XML
tree = ET.parse(xml_file)
root = tree.getroot()

# XML namespaces
ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

courses_added = 0

for url in root.findall('ns:url', ns):
    loc = url.find('ns:loc', ns).text
    # Extract course code from URL
    course_code_full = loc.split('/')[-1]  # e.g., 'AAE_101'
    if "_" not in course_code_full:
        continue
    subject, number = course_code_full.split("_", 1)

    # Create course entry with placeholder title/description
    course = Course(
        course_code=course_code_full,
        title=f"{subject} {number}",
        description="Placeholder description",
        subjects=subject,
        prerequisites=""
    )
    db.session.add(course)
    courses_added += 1

db.session.commit()
print(f"Added {courses_added} courses to the database.")
