import streamlit as st
import uuid
import pymysql
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import pytz

# Define timezones
utc_tz = pytz.utc
ct_tz = pytz.timezone("America/Chicago")

# AWS RDS Connection Details
db_host = 'gcbdallas.caqfykoqtrvk.us-east-1.rds.amazonaws.com'
db_user = 'Dallas_2024'
db_password = 'GCBDallas$223'
db_name = 'VerizonClientMarketing'

# Function to create a single database connection
def create_db_connection():
    return pymysql.connect(
        host=db_host,
        user=db_user,
        password=db_password,
        database=db_name
    )

# Function to generate unique links
def generate_link(user_id):
    base_url = "https://gcb-verizon-savings.streamlit.app/"  # Replace with your app's URL
    return f"{base_url}?session_id={user_id}"

# Function to send email
def send_email(recipient, subject, body):
    sender_email = "your-email@example.com"
    sender_password = "your-email-password"
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    # Create message
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    # Send email
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient, message.as_string())
        server.quit()
        st.success(f"Link sent to {recipient}")
    except Exception as e:
        st.error(f"Failed to send email: {str(e)}")

# Function to save link to the `links` table in AWS RDS
def save_link_to_db(email, link, connection):
    try:
        with connection.cursor() as cursor:
            # Insert data into the "links" table
            insert_query = "INSERT INTO links (email, link) VALUES (%s, %s)"
            cursor.execute(insert_query, (email, link))
            connection.commit()
        st.success(f"Link saved to database for {email}")
    except Exception as e:
        st.error(f"Error saving to database: {str(e)}")

# Function to fetch data from `links` table
def fetch_links_from_db(connection):
    try:
        with connection.cursor() as cursor:
            # Fetch all data from the "links" table
            fetch_query = "SELECT email, link FROM links"
            cursor.execute(fetch_query)
            result = cursor.fetchall()
        return result
    except Exception as e:
        st.error(f"Error fetching data from database: {str(e)}")
        return []

def fetch_client_data_from_db(connection):
    try:
        with connection.cursor() as cursor:
            # Fetch all data from the "clientInputs" table
            fetch_query = "SELECT email, siteNumber, compPrice, timestamp FROM clientInputs"
            cursor.execute(fetch_query)
            result = cursor.fetchall()

        # Convert timestamps to CT
        converted_result = []
        for row in result:
            email, siteNumber, compPrice, timestamp = row
            if timestamp:  # Ensure timestamp is not None
                timestamp = timestamp.replace(tzinfo=utc_tz).astimezone(ct_tz)
            converted_result.append((email, siteNumber, compPrice, timestamp))

        return converted_result
    except Exception as e:
        st.error(f"Error fetching data from database: {str(e)}")
        return []

# Set Streamlit page configuration to wide mode
st.set_page_config(layout="wide")

# Streamlit UI - Page navigation
page = st.sidebar.radio("Select Page", ("Assign Email and Link", "View Client Data"))

# Create a single database connection
connection = create_db_connection()

if page == "Assign Email and Link":
    st.title("Assign Email, Generate Link, and Save Link Data")

    email = st.text_input("Enter Email Address")

    if st.button("Generate Link, Save to DB, and Send Email"):
        if email:
            user_id = str(uuid.uuid4())[:8]  # Generate a random short user ID
            link = generate_link(user_id)

            save_link_to_db(email, link, connection)

            subject = "Your Unique Access Link"
            body = f"Hello, here is your unique link: {link}"

            # send_email(email, subject, body)

        else:
            st.warning("Please enter an email address.")

    # Display links table
    st.subheader("Generated Links")
    links_data = fetch_links_from_db(connection)

    if links_data:
        links_df = pd.DataFrame(links_data, columns=["Email", "Link"])
        st.dataframe(links_df, use_container_width=True)  # Make the table use full width
    else:
        st.warning("No links found in the `links` table.")

elif page == "View Client Data":
    st.title("View Client Data")

    client_data = fetch_client_data_from_db(connection)

    if client_data:
        df = pd.DataFrame(client_data, columns=["Email", "Site Number", "Compensation Price", "Timestamp"])
        
        # Remove index by setting it explicitly
        st.dataframe(df.style.hide(axis="index"), use_container_width=True)
    else:
        st.warning("No data found in the `clientInputs` table.")