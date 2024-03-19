from flask import Flask, render_template, request, redirect, url_for, session, send_file
import face_recognition
import cv2
from flask_mysqldb import MySQL
import io
import dropbox

app = Flask(__name__)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'prajwaltp'
app.config['MYSQL_DB'] = 'digi'

mysql = MySQL(app)

# Routes for user authentication
DROPBOX_ACCESS_TOKEN ='sl.BxE0rzuACOu1AdNMGzQ-zMxse71jGV7zBP8c5IPiFJdJnFygV43XbLewwtR8qZip46H9XbrJ3rnbQeutHuwVbi54V4K0bM8RTeQE-rEKkOuEbB6w5NNTQfKVdpdxvn3eY3Ehf5KuE_Eb'
dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)

# Secret key for session
app.secret_key = 'your_secret_key'

@app.route('/')
def index():
    return render_template('index.html')

# Landing page
@app.route('/landing')
def landing():
    if 'username' in session:
        return render_template('landing.html')
    else:
        return redirect(url_for('login'))
    
@app.route('/documents', methods=['GET', 'POST'])
def documents():
    if request.method == 'POST':
        entered_key = request.form.get('key')
        stored_key = session.get('secret_key')
        
        if entered_key == stored_key:  
            # Fetch images from Dropbox and pass them to template
            username = session.get('username')
            if username:
                folder_path = '/{}'.format(username)
                return redirect('https://www.dropbox.com/home' + folder_path)
            else:
                return 'User not logged in'
        else:
            return 'Invalid key. Access denied.'
    return render_template('documents.html')
    
@app.route('/user-dropbox-folder')
def user_dropbox_folder():
    username = session.get('username')
    if username:
        folder_path = '/{}'.format(username)
        dropbox_folder_link = "https://www.dropbox.com/home{}".format(folder_path)
        return redirect(dropbox_folder_link)
    else:
        return 'User not logged in'

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Check if username and password are valid
        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM users WHERE username = %s AND password = %s', (username, password))
        user = cur.fetchone()
        cur.close()
        
        if user:
            # Login successful, set up session and redirect to homepage
            session['username'] = username
            return redirect(url_for('landing'))
        else:
            # Login failed
            return 'Invalid username or password'
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        secret_key = request.form['key']
        
        # Store username, password, and secret key in the session
        session['username'] = username
        session['secret_key'] = secret_key

        # Attempt to establish a connection to the MySQL database
        try:
            cur = mysql.connection.cursor()
        except Exception as e:
            return f"Error connecting to the database: {e}"

        # Attempt to execute the INSERT query
        try:
            cur.execute('INSERT INTO users (username, password, `key`) VALUES (%s, %s, %s)', (username, password, secret_key))
            mysql.connection.commit()
            cur.close()
            return redirect(url_for('index'))
        except Exception as e:
            return f"Error executing query: {e}"

    return render_template('signup.html')


@app.route('/normal-access', methods=['GET', 'POST'])
def normal_access():
    if request.method == 'POST':
        entered_key = request.form.get('key')
        if entered_key == session.get('secret_key'):  # You need to store the secret key in session upon login/signup
            # Render the upload form directly if the entered key matches the stored key
            return render_template('upload_form.html')
        else:
            # Deny access and display an error message if the entered key is incorrect
            return 'Invalid key. Access denied.'
    return render_template('normal-access.html')


@app.route('/upload', methods=['GET', 'POST'])
def upload_image():
    if request.method == 'POST':
        if 'image' not in request.files:
            return 'No file part'

        file = request.files['image']

        if file.filename == '':
            return 'No selected file'

        username = session.get('username')
        if username:
            # Create folder if it doesn't exist
            folder_path = '/{}'.format(username)
            try:
                dbx.files_create_folder(folder_path)
            except dropbox.exceptions.ApiError as e:
                if e.error.is_path() and e.error.get_path().is_conflict():
                    pass  # Folder already exists

            # Read the file contents from the FileStorage object
            file_contents = file.read()

            try:
                cur = mysql.connection.cursor()

                # Insert image details into MySQL table without id
                cur.execute("INSERT INTO images (filename) VALUES (%s)", (file.filename,))
                mysql.connection.commit()
                cur.close()

                # Upload the image file to the user's folder in Dropbox
                file_path = '{}/{}'.format(folder_path, file.filename)
                dbx.files_upload(file_contents, file_path)

                return 'File uploaded successfully to {}'.format(username)

            except Exception as e:
                return 'Error: {}'.format(e)

        else:
            return 'User not logged in'



    return render_template('upload_form.html')

@app.route('/display')
def display_image():
    # Download the image file from Dropbox
    _, response = dbx.files_download('/your_image.jpg')

    # Return the image file as a response
    return send_file(io.BytesIO(response.content), mimetype='image/jpeg')

if __name__ == '__main__':
    app.run(debug=True)

# https://www.dropbox.com/developers/apps?_tk=pilot_lp&_ad=topbar4&_camp=myapps