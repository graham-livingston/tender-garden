import threading
import time
import asyncio
import math
from datetime import datetime, timedelta
from fastapi import FastAPI, WebSocket, Request, Depends, HTTPException, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import base64
import sqlite3
import jwt
from carbonCalc import get_current_load

# Global variables to store emissions data
total_co2_emissions = 0.0
total_energy_kwh = 0.0
current_power_watts = 0.0
start_time = datetime.now()

# Configuration for JWT
SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI()

# Mount static files for serving CSS and JS
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure Jinja2 templates
templates = Jinja2Templates(directory=".")

# OAuth2 scheme for token-based authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

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

@app.on_event("startup")
async def startup_event():
    background_carbon_monitor()

# Database connection function
def get_db_connection():
    conn = sqlite3.connect('example.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch all records from the database
    cursor.execute("SELECT datetime, height, width, image FROM records ORDER BY datetime DESC")
    all_records = cursor.fetchall()
    conn.close()

    formatted_records = []
    tree_stats = {}
    total_carbon_offset = 0.0

    if all_records:
        # Calculate carbon sequestration for the latest record
        latest_record = all_records[0]
        height_cm = latest_record["height"]
        diameter_cm = latest_record["width"]
        tree_stats = calculate_carbon_sequestered(diameter_cm, height_cm)

        # Calculate total carbon offset
        total_carbon_offset = tree_stats["CO2 Captured (Kg)"] - total_co2_emissions

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
        "total_carbon_offset": total_carbon_offset,
        "records": formatted_records
    })


@app.websocket("/ws/carbon-footprint")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        uptime = datetime.now() - start_time
        uptime_seconds = uptime.total_seconds()
        data = {
            "current_watts": current_power_watts,
            "total_kwh": total_energy_kwh,
            "uptime_seconds": uptime_seconds,
            "total_co2_emissions": total_co2_emissions
        }
        await websocket.send_json(data)
        await asyncio.sleep(1)  # Send updates every second

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

# Route to handle login form submission
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
        
        # Render the postForm.html content
        form_html = templates.TemplateResponse("postForm.html", {"request": request}).body.decode('utf-8')
        
        # Return the token and the form HTML
        return {"access_token": token, "form_html": form_html}
    else:
        # Return login page with error message
        return {"error": "Incorrect username or password"}

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
