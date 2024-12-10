from flask import Flask, render_template, request, redirect, flash, url_for, session
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import secrets
import os

app = Flask(__name__)

# Set the secret key for session management
app.secret_key = secrets.token_hex(16)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''  # Default for XAMPP
app.config['MYSQL_DB'] = 'blog_db'

# Config for file uploads
app.config['UPLOAD_FOLDER'] = 'static/uploads'  # Set your upload folder path
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

mysql = MySQL(app)

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Route for the homepage (root URL)
@app.route('/')
def home():
    return render_template('index.html')

# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Collect form data
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        middlename = request.form['middlename']
        age = request.form['age']
        birthday = request.form['birthday']
        contact_number = request.form['contact_number']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Password confirmation check
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))

        # Hash the password
        password_hash = generate_password_hash(password)

        # Insert into database
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO users (firstname, lastname, middlename, age, birthday, contact_number, username, email, password_hash)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (firstname, lastname, middlename, age, birthday, contact_number, username, email, password_hash))
        mysql.connection.commit()
        cur.close()

        flash('Registration successful! Please log in.', 'success')
        return redirect('/login')

    return render_template('register.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user[9], password):  # user[9] is the password_hash column
            session['user_id'] = user[0]  # Store user ID in session
            flash('Login successful!', 'success')
            return redirect(url_for('profile'))

        flash('Invalid credentials. Please try again.', 'danger')
        return redirect(url_for('login'))

    return render_template('login.html')

# Profile route with image upload
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    cur.close()

    if request.method == 'POST':
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        age = request.form['age']
        birthday = request.form['birthday']
        contact_number = request.form['contact_number']

        # Handling profile image upload
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                profile_image = filename

                # Update the user's profile image in the database
                cur = mysql.connection.cursor()
                cur.execute("""
                    UPDATE users SET profile_image = %s WHERE id = %s
                """, (profile_image, user_id))
                mysql.connection.commit()
                cur.close()

        # Update other profile information
        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE users SET firstname = %s, lastname = %s, age = %s, birthday = %s, contact_number = %s WHERE id = %s
        """, (firstname, lastname, age, birthday, contact_number, user_id))
        mysql.connection.commit()
        cur.close()

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    return render_template('profile.html', user=user)
@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        # Retrieve form data
        user_id = request.form.get('user_id')  # Check if user_id exists for update
        firstname = request.form.get('firstname')
        lastname = request.form.get('lastname')
        middlename = request.form.get('middlename')
        age = request.form.get('age')
        birthday = request.form.get('birthday')
        contact_number = request.form.get('contact_number')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')  # Optional
        confirm_password = request.form.get('confirm_password')  # Optional
        profile_image = request.files.get('profile_image')  # Optional

        # Check for missing required fields (skip user_id check for new users)
        if not all([firstname, lastname, age, birthday, contact_number, username, email]):
            flash('All required fields must be filled!', 'danger')
            return redirect(url_for('add_user'))

        # Validate passwords if provided
        if password and password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('add_user'))

        cur = mysql.connection.cursor()

        if user_id:  # Update existing user
            # If password is provided, update the password hash
            if password:
                password_hash = generate_password_hash(password)
                cur.execute("""
                    UPDATE users 
                    SET firstname=%s, lastname=%s, middlename=%s, age=%s, birthday=%s, 
                        contact_number=%s, username=%s, email=%s, password_hash=%s
                    WHERE id=%s
                """, (firstname, lastname, middlename, age, birthday, contact_number, username, email, password_hash, user_id))
            else:
                cur.execute("""
                    UPDATE users 
                    SET firstname=%s, lastname=%s, middlename=%s, age=%s, birthday=%s, 
                        contact_number=%s, username=%s, email=%s
                    WHERE id=%s
                """, (firstname, lastname, middlename, age, birthday, contact_number, username, email, user_id))

            # Handle profile image upload if provided
            if profile_image and profile_image.filename:
                profile_image_filename = profile_image.filename
                profile_image.save(f"static/uploads/{profile_image_filename}")
                cur.execute("""
                    UPDATE users 
                    SET profile_image=%s 
                    WHERE id=%s
                """, (profile_image_filename, user_id))

            flash('User updated successfully!', 'success')
        else:  # Insert new user
            # Validate passwords if provided for new users
            if password != confirm_password:
                flash('Passwords do not match!', 'danger')
                return redirect(url_for('add_user'))

            password_hash = generate_password_hash(password)

            cur.execute("""
                INSERT INTO users (firstname, lastname, middlename, age, birthday, contact_number, username, email, password_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (firstname, lastname, middlename, age, birthday, contact_number, username, email, password_hash))

            flash('User added successfully!', 'success')

        mysql.connection.commit()
        cur.close()
        return redirect(url_for('add_user'))

    # Retrieve all users for display (both adding and editing scenarios)
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    cur.close()

    return render_template('add_users.html', users=users)



@app.route('/delete_user/<int:user_id>', methods=['GET'])
def delete_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    mysql.connection.commit()
    cur.close()
    flash('User deleted successfully!', 'success')
    return redirect(url_for('add_user'))

# Route to display all blog posts
@app.route('/blogs', methods=['GET'])
def blogs():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM blogs ORDER BY timestamp DESC")
    blog_posts = cur.fetchall()
    cur.close()
    return render_template('create_blog.html', blog_posts=blog_posts)

# Route to create a new blog post
@app.route('/create_blog', methods=['POST'])
def create_blog():
    title = request.form['title']
    description = request.form['description']

    # Handling image upload
    image = None
    if 'image' in request.files:
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            image = filename

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO blogs (title, description, image)
        VALUES (%s, %s, %s)
    """, (title, description, image))
    mysql.connection.commit()
    cur.close()

    flash('Blog post created successfully!', 'success')
    return redirect(url_for('blogs'))
# Route to handle logout
@app.route('/logout')
def logout():
    # Clear the session to log the user out
    session.pop('user_id', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))  # Redirect to the homepage (index.html)
# Contact Us route
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        # Insert the contact form data into the database
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO contact_form (name, email, message)
            VALUES (%s, %s, %s)
        """, (name, email, message))
        mysql.connection.commit()
        cur.close()

        flash('Your message has been sent successfully!', 'success')
        return redirect(url_for('contact'))

    return render_template('contact.html')

if __name__ == '__main__':
    app.run(debug=True)
