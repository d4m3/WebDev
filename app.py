from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
#from data import Articles
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)

# Config MySQL
app.config['MYSQL_HOST'] = '127.0.0.1' # XAMP
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'myflaskapp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# initialzie MYSQL
mysql = MySQL(app)

# set variable to get the function(s) in Articles
# Pulled from file, but implemented to get from db
#Articles = Articles()

# Decorator
def is_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('Unauthorized access. Please login', 'danger')
			return redirect(url_for('login'))
	return wrap
# Decorator



#Index
@app.route('/')
def index():
	return render_template('home.html')

# About
@app.route('/about')
def about():
	return render_template('about.html')

# Articles
@app.route('/articles',methods=['GET','POST'])
@is_logged_in
def articles():
	# Front-End Article (clicking link) similiar to dashboard()
	cur = mysql.connection.cursor()
	
	result = cur.execute("SELECT * FROM articles")
	
	articles = cur.fetchall()
	
	if result > 0:
		return render_template('articles.html', articles=articles)
	else:
		msg = 'No Articles Found'
		return render_template('articles.html', msg=msg)
	# Close connection
	cur.close()

# Route for the links in articles.html in a tag
# Accessed dynamically <string:id>
# intergrate with id in mysql - upcoming
# Single Article
@app.route('/article/<string:id>/',methods=['GET','POST'])
@is_logged_in
def article(id):
	# Get article and pass to view
	cur = mysql.connection.cursor()

	# Get article from db
	result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])

	article = cur.fetchone()

	return render_template('article.html', article=article)



# Register Form Class
class RegisterForm(Form):
	name = StringField('Name', [validators.Length(min=1, max=50)])
	username = StringField('Username', [validators.Length(min=4, max=25)])
	email = StringField('Email', [validators.Length(min=6,max=50)])
	password = PasswordField('Password', [
			validators.DataRequired(),
			validators.EqualTo('confirm', message='Passwords do not match')
		])
	confirm = PasswordField('Confirm Password')

# User Register
@app.route('/register', methods=['GET', 'POST'])
def register():
	form = RegisterForm(request.form)
	# if register.html is submitted
	if request.method == 'POST' and form.validate():
		name = form.name.data
		email = form.email.data
		username = form.username.data
		# need to encrypt before submitting, wrap with SHA256
		password = sha256_crypt.encrypt(str(form.password.data))

		# Create cursor
		cur = mysql.connection.cursor()

		# Execute query
		cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))
		
		# Commit to DB
		mysql.connection.commit()

		# Close connection
		cur.close()

		# Initailized here, Once register flash message, need to display _message.html
		flash('You are now registered and can log in', 'success')

		return redirect(url_for('login'))	
	return render_template('register.html', form=form)

# User Login
@app.route('/login', methods=['GET','POST'])
def login():
	if request.method == 'POST':
		username = request.form['username'] # Get Form Fields
		password_candiate = request.form['password'] # Get Password From DB for comparision

		# Create cursor
		cur = mysql.connection.cursor()

		# Get user by username
		result = cur.execute("SELECT  * FROM users WHERE username = %s", [username])
		if result > 0:
			# Get stored hash
			data = cur.fetchone()
			password = data['password']

			# Compare passwords from db and typed
			if sha256_crypt.verify(password_candiate, password):
				# Passed 
				session['logged_in'] = True
				session['username'] = username

				flash('You are now logged in','success')
				return redirect(url_for('dashboard'))
				#app.logger.info('PASSWORD MATCHED')
			else:
				error = 'Invalid login'
				return render_template('login.html', error=error)
			# close connection
			cur.close()
				#app.logger.info('PASSWORD NOT MATCHED')
		# If unable to login send to login page along with reason/error 
		else:
			error = 'Username not found'
			return render_template('login.html', error=error)

	return render_template('login.html')

# Check if user logged in (decorator)
# prevent unauthorized access
# http://flask.pocoo.org/snippets/98/
def is_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('Unauthorized access. Please login', 'danger')
			return redirect(url_for('login'))
	return wrap

# Logout
@app.route('/logout')
@is_logged_in
def logout():
	session.clear()
	flash('You are now logged out','success')
	return redirect(url_for('login'))

# Dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
	# List Articles on Dashboard
	# Create Cursor
	cur = mysql.connection.cursor()
	# (Execute) Get Articles from db
	result = cur.execute("SELECT * FROM articles")
	# Fetchall in dict form
	articles = cur.fetchall()

	if result > 0:
		return render_template('dashboard.html', articles=articles)
	else:
		msg = 'No Articles Found'
		return render_template('dashboard.html', msg=msg)
	# Close connection
	cur.close()

# Artilce Form Class
class ArticleForm(Form):
	title = StringField('Title', [validators.Length(min=1, max=200)])
	body = TextAreaField('Body', [validators.Length(min=30)])

# Add Article Route
@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
	form = ArticleForm(request.form)
	if request.method == 'POST' and form.validate():
		title = form.title.data
		body = form.body.data

		# Create Cursor
		cur = mysql.connection.cursor()

		# Execute
		cur.execute("INSERT INTO articles(title, body, author) VALUES(%s, %s,%s)",(title, body, session['username']))

		# Commit
		mysql.connection.commit()

		# Close connection
		cur.close()

		# Notify created article and redirect to dashboard
		flash('Article Created','success')
		return redirect(url_for('dashboard'))

	return render_template('add_article.html',form=form)
	

# Edit Article Route
@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
	# Create Cursor
	cur = mysql.connection.cursor()

	# Get article by id
	result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])

	article = cur.fetchone()

	# Get Form
	form = ArticleForm(request.form)

	# Populate article form fields
	form.title.data = article['title']
	form.body.data = article['body']

	if request.method == 'POST' and form.validate():
		title = request.form['title']
		body = request.form['body']

		# Create Cursor
		cur = mysql.connection.cursor()

		# Execute and UPDATE
		cur.execute("UPDATE articles SET title=%s, body=%s WHERE id=%s", (title, body, id))

		# Commit
		mysql.connection.commit()

		# Close connection
		cur.close()

		# Notify created article and redirect to dashboard
		flash('Article Updated','success')

		return redirect(url_for('dashboard'))

	return render_template('edit_article.html',form=form)	

@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
	# Create Cursor
	cur = mysql.connection.cursor()
	
	# Excute
	cur.execute("DELETE FROM articles WHERE id=%s", [id])

	# Commit and close
	mysql.connection.commit()

	cur.close()

	flash('Article Deleted','success')

	return redirect(url_for('dashboard'))



if __name__ == '__main__':
	# Make this key more secure
	app.secret_key='secret123'
	app.run(debug=True)