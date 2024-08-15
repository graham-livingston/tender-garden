import sqlite3
from fastapi import FastAPI, Form, Request, Depends, HTTPException, File, UploadFile
import base64
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
import jwt
from datetime import datetime, timedelta
from fastapi.templating import Jinja2Templates
from pathlib import Path
from utils import calculate_tree_weight_cm


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
    cursor.execute("SELECT datetime, height, width, image FROM records")
    records = cursor.fetchall()
    conn.close()

    # Convert image binary data to base64 for displaying
    formatted_records = []
    for record in records:
        formatted_record = {
            "datetime": record["datetime"],
            "height": record["height"],
            "width": record["width"],
            "image": base64.b64encode(record["image"]).decode('utf-8')
        }
        formatted_records.append(formatted_record)
        
        # Calculate trees carbon sequestration
        tree_stats = calculate_tree_weight_cm(formatted_records[-1]["width"], formatted_records[-1]["height"])

    # Render the index.html template with records
    return templates.TemplateResponse("index.html", {"request": request, "records": formatted_records, "tree_stats": tree_stats})


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
