import threading
import time
import asyncio
import math
import csv
import os
import random
import schedule
import requests
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from fastapi import FastAPI, WebSocket, Request, Depends, HTTPException, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import base64
import sqlite3
import jwt

# Global variables to store emissions data
total_co2_emissions = 0.0
total_energy_kwh = 0.0
current_power_watts = 0.0
total_co2_captured = 0.0
# start_time = datetime.now()
start_time = datetime.strptime('2024-08-16 15:00:00', '%Y-%m-%d %H:%M:%S')


# Configuration for JWT
SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def get_netio_data(ip_address):
    """
    Retrieves the JSON data from a Netio PowerBox at the specified IP address.

    Args:
        ip_address (str): The IP address of the Netio PowerBox.

    Returns:
        dict: The JSON data retrieved from the Netio PowerBox.
    """
    endpoint = f"http://{ip_address}/netio.json"

    try:
        # Make the API call
        response = requests.get(endpoint)
        response.raise_for_status()  # Check if the request was successful (status code 200)

        # Parse the JSON response
        data = response.json()

        return data

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None

def get_current_load(ip_address) -> float:
    """
    Retrieves the current load in watts from the Netio PowerBox.

    Args:
        ip_address (str): The IP address of the Netio PowerBox.

    Returns:
        float: The current power load in watts.
    """
    data = get_netio_data(ip_address)
    if data and 'Outputs' in data:
        # Assuming we are interested in the second object in the Outputs list
        power_in_watts = data['Outputs'][1]['Load']
        return power_in_watts
    else:
        return 0.0

# Function to calculate carbon sequestered by a tree
def calculate_carbon_sequestered(diameter_cm: float, height_cm: float) -> dict:
    """
    Calculate the carbon sequestered by a tree given its diameter and height.

    Args:
        diameter_cm (float): Diameter at breast height (in cm)
        height_cm (float): Height of the tree (in cm)

    Returns:
        dict: A dictionary containing the volume, carbon content, and CO2 equivalent (in Kg)
    """

    # Convert diameter and height from centimeters to meters for the formula
    diameter_m = diameter_cm
    height_m = height_cm / 100.0

    # Calculate D^2 * H
    d2h = (diameter_m ** 2) * height_m

    # Calculate ln(Vol)
    ln_vol = -9.85 + 0.86 * math.log(d2h)

    # Calculate Volume
    volume = math.exp(ln_vol)

    # Calculate Bio Mass (CC)
    dry_biomass = 304 * volume
    
    # Calculate Carbon Content (CC)

    carbon_content = dry_biomass * 0.47
    
    # Calculate CO2 Equivalent (CO2-Eq)
    co2_equivalent = 3.67 * carbon_content

    return {
        'Diameter (cm)': diameter_cm,
        'Height (m)': height_m,
        'Dry Biomass (Kg)': dry_biomass,
        'CO2 Captured (Kg)': co2_equivalent
    }

# Database connection function
def get_db_connection():
    conn = sqlite3.connect('example.db')
    conn.row_factory = sqlite3.Row
    return conn

# Function to log the total energy consumed and CO2 emissions every hour
def log_value():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Execute the insert query
    cursor.execute('''
        INSERT INTO energyRecords (datetime, total_co2_emissions, total_energy_kwh)
        VALUES (DATETIME('now'), ?, ?)
    ''', (total_co2_emissions, total_energy_kwh))

    # Commit the transaction
    conn.commit()

    # Close the connection
    conn.close()

def schedule_task():
    schedule.every().hour.at(":00").do(log_value)

    while True:
        schedule.run_pending()
        time.sleep(1)

def get_latest_record():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT datetime, total_co2_emissions, total_energy_kwh FROM energyRecords ORDER BY datetime DESC LIMIT 1")
    latest_record = cursor.fetchone()
    
    conn.close()
    
    if latest_record:
        return {
            "datetime": datetime.strptime(latest_record[0], '%Y-%m-%d %H:%M:%S'),
            "total_co2_emissions": latest_record[1],
            "total_energy_kwh": latest_record[2]
        }
    else:
        return None
    
def add_record_to_db(record_datetime, total_co2_emissions, total_energy_kwh):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''INSERT INTO energyRecords (datetime, total_co2_emissions, total_energy_kwh)
                      VALUES (?, ?, ?)''', (record_datetime.strftime('%Y-%m-%d %H:%M:%S'), total_co2_emissions, total_energy_kwh))
    
    conn.commit()
    conn.close()
    
def backfill_missing_records():
    latest_record = get_latest_record()
    current_time = datetime.now()

    if not latest_record:
        # If there's no record in the table, create the first one.
        print("No records found. Creating the first record.")
        add_record_to_db(current_time.strftime('%Y-%m-%d %H:%M:%S'), 0.0, 0.0)
        return

    last_time = latest_record['datetime']
    total_energy_kwh = latest_record['total_energy_kwh']
    total_co2_emissions = latest_record['total_co2_emissions']

    while last_time + timedelta(hours=1) <= current_time:
        last_time += timedelta(hours=1)
        
        noise = random.uniform(0.001, 0.1)
        # Calculate energy usage for the hour
        energy_kwh_per_hour = (205 + noise) / 1000.0  # Energy in kWh for the hour

        # Calculate CO2 emissions for the hour
        co2_emissions_per_hour = energy_kwh_per_hour * 22.301 / 1000.0

        # Update totals
        total_energy_kwh += energy_kwh_per_hour
        total_co2_emissions += co2_emissions_per_hour

        # Insert the new record
        add_record_to_db(last_time, total_co2_emissions, total_energy_kwh)

    print("Backfill completed.")

def restart_global_variables():
    latest_record = get_latest_record()
    current_time = datetime.now()
    seconds_since_last_record = (current_time - latest_record['datetime']).total_seconds()
    
        # Calculate total energy usage since the last record
    energy_kwh_since_last_record = (205.2 / 1000.0) * (seconds_since_last_record / 3600.0)  # kWh

    # Calculate total CO2 emissions since the last record
    co2_emissions_since_last_record = energy_kwh_since_last_record * (22.301 / 1000.0)

    # Update global variables
    total_energy_kwh = latest_record['total_energy_kwh'] + energy_kwh_since_last_record
    total_co2_emissions = latest_record['total_co2_emissions'] + co2_emissions_since_last_record

    print(f"Global variables reloaded. Total energy (kWh): {total_energy_kwh}, Total CO2 emissions (kg): {total_co2_emissions}")


# Classes to handle storing information for the graph interface
class dateValue:
    '''
     holds date and value pairs used for the graph in the seconds interval.
    '''
    def __init__(self, date, value) -> None:
        self.date = date
        self.value = value

class meterlogger:
    '''
     used to log the values of the meter every second.
     values are stored as dateValue objects in the record list.

    '''
    def __init__(self, limit) -> None:
        self.record = []
        self.limit = limit
        
    def addValue(self, value):
        if len(self.record) >= self.limit:
            self.record.pop(-1)
            self.record.insert(0, dateValue(datetime.now(), value))
        else:
            self.record.insert(0, dateValue(datetime.now(), value))

graphMeter = meterlogger(60) # lasts for one minute

lock = threading.Lock()
        
app = FastAPI()


# Mount static files for serving CSS and JS
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure Jinja2 templates
templates = Jinja2Templates(directory="templates")

# OAuth2 scheme for token-based authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Background task to monitor energy usage
def start_carbon_monitoring(ip_address="192.168.1.89"):
    global total_co2_emissions, total_energy_kwh, current_power_watts
    while True:
        current_power_watts = get_current_load(ip_address)
        energy_kwh = current_power_watts / 1000.0 * (1 / 3600)
        total_energy_kwh += energy_kwh
        co2_emissions = energy_kwh * 22.301 / 1000.0
        total_co2_emissions += co2_emissions
        time.sleep(1)

def background_carbon_monitor(ip_address="192.168.1.89"):
    thread = threading.Thread(target=start_carbon_monitoring, args=(ip_address,))
    thread.daemon = True
    thread.start()

def background_energy_logger():
    thread = threading.Thread(target=schedule_task)
    thread.daemon = True
    thread.start()

@app.on_event("startup")
async def startup_event():
    backfill_missing_records()
    restart_global_variables()
    background_carbon_monitor()
    background_energy_logger()



@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    global total_co2_captured
    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch all records from the database
    cursor.execute("SELECT datetime, height, width, image FROM records ORDER BY datetime DESC")
    all_records = cursor.fetchall()
    conn.close()

    formatted_records = []
    tree_stats = {}
    global total_co2_captured
    if all_records:
        # Calculate carbon sequestration for the latest record
        latest_record = all_records[0]
        height_cm = latest_record["height"]
        diameter_cm = latest_record["width"]
        tree_stats = calculate_carbon_sequestered(diameter_cm, height_cm)

        # Calculate total carbon offset
        total_co2_captured = tree_stats["CO2 Captured (Kg)"]

        # Format all records for display
        for record in all_records:
            formatted_record = {
                "datetime": record["datetime"],
                "height": record["height"],
                "width": record["width"],
                "image": base64.b64encode(record["image"]).decode('utf-8')
            }
            formatted_records.append(formatted_record)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "tree_stats": tree_stats,
        "records": formatted_records
    })


@app.websocket("/ws/carbon-footprint")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()


    while True:

        uptime = datetime.now() - start_time
        uptime_seconds = uptime.total_seconds()

        total_co2_offset = total_co2_captured - total_co2_emissions
        print(f'total_co2_offset: {total_co2_offset}')
        
        data = {
            "current_watts": current_power_watts,
            "total_kwh": total_energy_kwh,
            "uptime_seconds": uptime_seconds,
            "total_co2_emissions": total_co2_emissions
        }
        
        current_power_watts = data["current_watts"]
        total_energy_kwh = data["total_kwh"]
        total_co2_emissions = data["total_co2_emissions"]
        data["total_co2_offset"] = total_co2_offset
    
        await websocket.send_json(data)
        await asyncio.sleep(1)  # Send updates every second

@app.get("/get-popup-content/{tag_id}", response_class=HTMLResponse)
async def get_popup_content(tag_id: str, request: Request):
    try:
        # Render the HTML template based on the tag_id
        return templates.TemplateResponse(f"{tag_id}.html", {"request": request})
    except:
        raise HTTPException(status_code=404, detail="Content not found")


# Function to create a JWT token
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Route for the login page
@app.get("/login", response_class=HTMLResponse)
async def get_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if the username and password are correct
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        # Generate JWT token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        token = create_access_token(
            data={"sub": username}, expires_delta=access_token_expires
        )
        
        # Render the forms.html content
        form_html = templates.TemplateResponse("forms.html", {"request": request}).body.decode('utf-8')
        
        # Return the token and the form HTML
        return {"access_token": token, "form_html": form_html}
    else:
        # Return login page with error message
        return {"error": "Incorrect username or password"}

@app.get("/form/{form_type}", response_class=HTMLResponse)
async def get_form(request: Request, form_type: str, token: str = Depends(oauth2_scheme)):
    form_template = ""
    if form_type == "new":
        form_template = "newForm.html"
        all_records = None
    elif form_type == "edit":
        form_template = "editForm.html"
        formatted_records = []
            # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch all records from the database
        cursor.execute("SELECT id, datetime, height, width, image FROM records ORDER BY datetime DESC")
        all_records = cursor.fetchall()
        conn.close()
        
        for record in all_records:
            formatted_record = {
                "datetime": record["datetime"],
                "height": record["height"],
                "width": record["width"],
                "image": base64.b64encode(record["image"]).decode('utf-8')
            }
            formatted_records.append(formatted_record)

    elif form_type == "delete":
        form_template = "deleteForm.html"
        formatted_records = []
            # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch all records from the database
        cursor.execute("SELECT id, datetime, height, width, image FROM records ORDER BY datetime DESC")
        all_records = cursor.fetchall()
        conn.close()
        
        for record in all_records:
            formatted_record = {
                "datetime": record["datetime"],
                "height": record["height"],
                "width": record["width"],
                "image": base64.b64encode(record["image"]).decode('utf-8')
            }
            formatted_records.append(formatted_record)

    if form_template and all_records: 
        return templates.TemplateResponse(form_template, {"request": request, "records": formatted_records})
    elif form_template and not all_records:
        return templates.TemplateResponse(form_template, {"request": request})
    else:
        raise HTTPException(status_code=404, detail="Form not found")

@app.post("/edit-record/{record_id}")
async def edit_record(
    request: Request,
    record_id: int,
    token: str = Depends(oauth2_scheme),
    datetime: str = Form(...),
    height: float = Form(...),
    width: float = Form(...),
    image: UploadFile = File(None)
):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    username = payload.get("sub")

    if username is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    # Prepare the update statement
    if image is not None:
        image_data = await image.read()
        cursor.execute('''
            UPDATE records
            SET height = ?, width = ?, image = ?
            WHERE id = ?
        ''', (height, width, image_data, record_id))
    
    else:
        cursor.execute('''
            UPDATE records
            SET height = ?, width = ?
            WHERE id = ?
        ''', (height, width, record_id))
    
    # Commit and close the connection
    conn.commit()
    conn.close()

    return {"message": "Record updated successfully."}

@app.post("/delete-record/{record_id}")
async def delete_record(
    request: Request,
    record_id: int,
    token: str = Depends(oauth2_scheme)
):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    username = payload.get("sub")

    if username is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    # Execute the deletion
    cursor.execute('DELETE FROM records WHERE id = ?', (record_id,))
    
    # Commit and close the connection
    conn.commit()
    conn.close()

    return {"message": "Record deleted successfully."}

@app.post("/submit")
async def submit_form(
    request: Request,
    token: str = Depends(oauth2_scheme),
    height: float = Form(...),
    width: float = Form(...),
    image: UploadFile = File(...)
):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    username = payload.get("sub")
    
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Read the file contents as binary data
    image_data = await image.read()
    datetime_value = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    # Insert the form data into the records table
    cursor.execute('''
        INSERT INTO records (datetime, height, width, image) VALUES (?, ?, ?, ?)
    ''', (datetime_value, height, width, image_data))
    
    # Commit and close the connection
    conn.commit()
    conn.close()

    return {"message": "Form submitted successfully."}

@app.get("/graph/seconds")
async def get_seconds():
    global graphMeter
    with lock:
        return {"meter_seconds": graphMeter.record} # this will need to be maybe two lists in order

@app.get("/graph/treeLifeSpan")
async def get_tree_life_span():
    pass

@app.get("/graph/hours")
async def get_hours():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT datetime, total_co2_emissions FROM energyRecords ORDER BY datetime ASC")
    serverHistory = cursor.fetchall()
    return {"serverHistory": serverHistory}
    # then get all the archive items from records in the html since it should all already be on the front end in the Archive section

@app.get("/graph/hours/last")
async def get_latest_hour():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT datetime, total_co2_emissions FROM energyRecords ORDER BY datetime DESC LIMIT 1")
    latest_entry = cursor.fetchone()
    return {"latestEntry": latest_entry}
