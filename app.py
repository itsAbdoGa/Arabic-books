from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session
import os
import csv
import io
import json
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a random secret key
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'csv'}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Store books in memory (in a real app, you'd use a database)
books = []

# Admin credentials (in a real app, use a database with hashed passwords)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password"  # Change this to a secure password

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('يرجى تسجيل الدخول للوصول إلى هذه الصفحة', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    results = []
    
    if query:
        # Add index to each book so we can reference it later
        results = []
        for i, book in enumerate(books):
            if query.lower() in book['book_name'].lower() or query.lower() in book['author'].lower():
                # Create a copy of the book with its index
                book_with_index = book.copy()
                book_with_index['id'] = i  # Add the actual index
                results.append(book_with_index)
    
    return jsonify(results)

@app.route('/autocomplete')
def autocomplete():
    query = request.args.get('q', '').strip()
    suggestions = []
    
    if query:
        # Get unique book names and authors containing the query
        suggestions = list(set([book['book_name'] for book in books if query.lower() in book['book_name'].lower()]))
        
        # Add author suggestions if they match
        author_suggestions = list(set([book['author'] for book in books if query.lower() in book['author'].lower()]))
        suggestions.extend(author_suggestions)
        
        # Limit to top 10 suggestions
        suggestions = suggestions[:10]
    
    return jsonify(suggestions)

@app.route('/book/<int:book_id>')
def book_details(book_id):
    if 0 <= book_id < len(books):
        return render_template('book_details.html', book=books[book_id], book_id=book_id)
    return render_template('404.html'), 404

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            flash('تم تسجيل الدخول بنجاح', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'error')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('index'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    return render_template('admin_dashboard.html', book_count=len(books))

@app.route('/admin/import', methods=['GET', 'POST'])
@login_required
def import_books():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('لم يتم تحديد ملف', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('لم يتم تحديد ملف', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            try:
                # Read CSV file
                stream = io.StringIO(file.stream.read().decode('utf-8'))
                csv_reader = csv.reader(stream)
                
                # Get headers
                headers = next(csv_reader)
                
                # Clear existing books
                books.clear()
                
                # Process rows
                for row in csv_reader:
                    if len(row) >= len(headers):
                        book = {
                            'source': row[0],
                            'author': row[1],
                            'book_name': row[2],
                            'num_of_volumes': row[3]
                        }
                        books.append(book)
                
                # Save to a file for persistence (optional)
                with open(os.path.join(app.config['UPLOAD_FOLDER'], 'books.json'), 'w', encoding='utf-8') as f:
                    json.dump(books, f, ensure_ascii=False)
                
                flash(f'تم استيراد {len(books)} كتاب بنجاح', 'success')
                return redirect(url_for('admin_dashboard'))
                
            except Exception as e:
                flash(f'حدث خطأ أثناء معالجة الملف: {str(e)}', 'error')
                return redirect(request.url)
        else:
            flash('نوع الملف غير مسموح به. يرجى استخدام ملفات CSV فقط', 'error')
            return redirect(request.url)
    
    return render_template('import_books.html')

# Load books from file on startup if available
try:
    books_file = os.path.join(app.config['UPLOAD_FOLDER'], 'books.json')
    if os.path.exists(books_file):
        with open(books_file, 'r', encoding='utf-8') as f:
            books = json.load(f)
except Exception as e:
    print(f"Error loading books: {e}")

if __name__ == '__main__':
    app.run(debug=True)