import xml.etree.ElementTree as ET
from app import app, db, Course

# Path to your XML sitemap file
XML_FILE = "courses_sitemap.xml"

# Parse the XML file
tree = ET.parse(XML_FILE)
root = tree.getroot()

# XML namespace (from the sitemap spec)
ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

# Extract course codes from URLs
course_codes = []
for url in root.findall("ns:url", ns):
    loc = url.find("ns:loc", ns).text  # e.g., "https://uwcourses.com/courses/AAE_101"
    code = loc.split("/")[-1]          # e.g., "AAE_101"
    course_codes.append(code)

if not course_codes:
    print("No courses found in XML.")
else:
    print(f"Found {len(course_codes)} courses. Adding to database...")

# Insert courses into DB inside application context
with app.app_context():
    db.create_all()  # create tables if they don't exist

    for code in course_codes:
        # Check if course already exists
        existing = Course.query.filter_by(course_code=code).first()
        if existing:
            continue  # skip duplicates

        # Create a new course entry
        course = Course(
            course_code=code,
            title="",         # you can fill in title if you have it
            description="",   # you can fill in description if you have it
            subjects="",      # optional: you could extract subject from code
            prerequisites=""
        )
        db.session.add(course)

    db.session.commit()
    print("Courses added successfully!")
