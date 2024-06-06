from flask import Flask, request, g, redirect, url_for
from flask import render_template, make_response, send_from_directory
from flask import flash, session, abort
from markupsafe import escape
import sqlite3
import sys
import os
from werkzeug.utils import secure_filename

MAX_PASSWORD_LENGTH = 50
MAX_USERNAME_LENGTH = 30
MAX_EMAIL_LENGTH = 50

app = Flask(__name__)
DATABASE = os.path.join(app.root_path,'databases/my_database.db')

app.secret_key = b'{JGHR^U<<L?@%"'

ALLOWED_EXTENSIONS = set(['txt', 'png', 'jpg', 'jpeg', 'gif'])

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path,'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/uploads/<user>/<filename>')
def upload(user, filename):
    return send_from_directory(os.path.join(app.root_path, 'uploads/'+user), filename)

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

def query_db(query, args=(), one=False):
    conn = get_db()
    curs = conn.execute(query, args)
    conn.commit()
    rv = curs.fetchall()
    curs.close()
    return (rv[0] if rv else None) if one else rv

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
           
def rating_round(rating):
    c, r = rating//1, rating%1
    if r < 0.25:
        return c, 0
    if r > 0.75:
        return c+1, 0
    return c, 1
           
def not_normal():
    abort(403)

def validate_post(title, description, price, quantity):
    try:
        if len(title)>0 and len(title)<50:
            if description:
                if len(description)>1000:
                    flash("Description too long")
                    abort(418)
            price = float(price)
            quantity = int(float(quantity))
            if price>0 and price<100001:
                if quantity>=1 and quantity<100001:
                    return True
    except:
        pass
    abort(418)
    
def safe_rating(rating):
    rating = int(rating)
    if rating<1:
        rating = 1
    if rating>5:
        rating = 5
    return rating
    
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.errorhandler(404) 
def page_not_found(error):
    return render_template('page_not_found.html'), 404
"""
@app.errorhandler(403)
def forbiddden(error):
    return render_template('page_not_found.html'), 404
"""

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        if request.form.get('username') and request.form.get('passwd'):
            username = secure_filename(request.form.get('username'))
            email = request.form.get('email')
            password = request.form.get('passwd')
            passwd2 = request.form.get('passwd2')
            ip = request.remote_addr

            if ('@' not in email) or ('.' not in email):
                flash('Invalid email')
                return redirect(url_for('register'))
            if password != passwd2:
                flash("Passwords don't match :)")
                return redirect(url_for('register'))
            if len(username) > MAX_USERNAME_LENGTH:
                flash("Username too long")
                return redirect(url_for('register'))
            if len(email) > MAX_EMAIL_LENGTH:
                flash("Email too long")
                return redirect(url_for('register'))
            if len(password) > MAX_PASSWORD_LENGTH:
                flash("Password too long")
                return redirect(url_for('register'))
            
            user = query_db("SELECT * FROM users WHERE username=?", (username,))
            if user:
                flash("Username already exists")
                return redirect(url_for('register'))

            values = (username, email, password)
            query_db("INSERT INTO users VALUES (?, ?, ?, datetime('now'));", values)

            flash("Successfully registered. Now you can log in.")
            return redirect(url_for('login'))
        else:
            flash('Sorry, you need to submit a username and a password')
            return redirect(url_for('register'))
    else:
        if 'username' in session: #if the user is already logged in
            username = escape(session['username'])
            return render_template("already_logged.html", username=username)
        return render_template("register.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('username') and request.form.get('password'):
            username = request.form.get('username')
            password = request.form.get('password')
            ip = request.remote_addr
            values = (username, password)
            user = query_db("SELECT username FROM users WHERE username=? AND password=?", values)
            if user:
                session['username'] = user[0][0]
                flash('You are successfully logged in')
                return redirect(url_for('home'))
            else:
                flash('Wrong username or password')
            return redirect(url_for('login'))
        else:
            flash('Sorry, you need to submit an username and a password')
            return redirect(url_for('login'))
    else:
        if 'username' in session: #if the user is already logged in
            username = escape(session['username'])
            return render_template("already_logged.html", username=username)
        return render_template("login.html")

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('username', None)
    flash("Successfully logged out")
    return redirect(url_for('index'))

@app.route('/home', methods=['GET'])
def home():
    if 'username' in session:
        username = session['username']
        return render_template('home.html')
    else:
        flash('You need to log in to access your account')
        return redirect(url_for('login'))

@app.route('/profile/<username>', methods=['GET'])
def profile(username):
    email = query_db("SELECT email FROM users WHERE username=?", (username,))[0][0]
    user = [username, email]
    return render_template('profile.html', user=user)

@app.route('/new_post', methods=['GET', 'POST'])
def new_post():
    if request.method == 'GET':
        if 'username' in session:
            return render_template('new_post.html')
        else:
            flash("You need to log in to sell a product")
            return redirect(url_for('login'))
    else:
        if 'username' not in session:
            abort(403)
        assert(request.method == 'POST')

        product_title = request.form.get('product_title')
        product_price = request.form.get('product_price')
        product_description = request.form.get('product_description')
        product_quantity = request.form.get('product_quantity')
        validate_post(product_title, product_description, product_price, product_quantity)
        product_price = round(float(product_price), 2)
        product_quantity = int(float(product_quantity))

        seller = session['username'] #the username of the person posting
        values = (product_title, product_price, product_description, seller, product_quantity)

        query_db("INSERT INTO products (title, price, description, seller, quantity, post_date) VALUES (?, ?, ?, ?, ?, datetime('now'));", values)
        user = seller
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    product_id = query_db("SELECT id FROM products WHERE title=? AND price=? AND description=? AND seller=? AND quantity=?", values)[0][0]
                    print("product_id:", product_id)
                    query_db("UPDATE products SET image=? WHERE id=?", (filename, product_id))
                    newpath = os.path.join(app.root_path, 'uploads/'+user) 
                    if not os.path.exists(newpath):
                        os.makedirs(newpath)
                    upload_path = os.path.join(app.root_path,'uploads/'+user+"/"+filename)
                    file.save(upload_path)
                    
        flash('product successfully posted')
        return redirect(url_for('home'))
        

@app.route('/posts', methods=['GET'])
def posts():
    query = "SELECT title, description, price, seller, quantity, id FROM products WHERE quantity>0"
    sort_st = request.args.get('sort') 
    if sort_st:
        if sort_st == 'rating_up':
            query += " ORDER BY rating DESC" #because they will be reverted
        elif sort_st == 'rating_down':
            query += " ORDER BY rating ASC"
    
    posts = query_db(query)
    posts = posts[::-1]
    # print("posts: ", posts)
    
    search = request.args.get('search')
    if search:
        if len(search) > 50:
            not_normal()
        search = search.lower()
        # print("search: ", search)
        good_posts = []
        for post in posts:
            if search in post[0].lower() or search in post[1].lower() or search in post[3].lower():
                good_posts.append(post)
        posts = good_posts

    if request.args.get('sort'):
        sort = sort_st.split('_')
        if sort[0] == 'time':
            if sort[1] == 'up':
                posts = posts[::-1]
        if sort[0] == 'price':
            posts = sorted(posts, key=lambda post: post[2])
            if sort[1] == 'down':
                posts = posts[::-1]
                
    ovr_ratings = query_db("SELECT id, rating FROM products")
    ovr_rating = dict(ovr_ratings)
    ratings = dict(ovr_ratings)
    
    for post in posts:
        if ovr_rating[post[5]]:
            m = ovr_rating[post[5]]
            y, x = rating_round(m)
            z = 5 - x - y
            if z<0:
                z=0
            nr = [int(y), int(x), int(z)]
            m = []
            for i in range(nr[0]):
                m.append('★')
            if nr[1]:
                m.append('✬')
            for i in range(nr[2]):
                m.append('☆')
            ratings[post[5]] = m

    
    return render_template('posts.html', posts=posts, sort=sort_st, search=search, ratings=ratings, ovr_rating=ovr_rating)
    
@app.route('/post/<post_id>', methods=['GET', 'POST'])
def post(post_id):
    if request.method == "POST":
        if 'username' in session:
            rating = request.form.get('rating')
            if rating:
                rating = safe_rating(rating)
                content = request.form.get('comment')
                user = session['username']
                existing = query_db("SELECT rating FROM reviews WHERE post_id=? AND user=?", (post_id, user))
                if existing:
                    flash("You already submitted a review")
                    return redirect(url_for('post', post_id=post_id))
                values = (rating, content, post_id, user)
                query_db("INSERT INTO reviews (rating, content, post_id, user, time) VALUES (?, ?, ?, ?, datetime('now'))", values)
                ovr_rating = query_db("SELECT AVG(rating) FROM reviews WHERE post_id=?", (post_id,))[0][0]
                ovr_rating = round(ovr_rating, 2)
                query_db("UPDATE products SET rating=? WHERE id=?", (ovr_rating, post_id))
                flash("review posted")
                return redirect(url_for('post', post_id = post_id))
            else:
                flash("enter a rating")
                return redirect(url_for('post', post_id = post_id))
        else:
            flash("Log in first")
            return redirect(url_for('login'))
    elif request.method == "GET":
        posts = query_db("SELECT title, description, price, seller, quantity, rating FROM products WHERE id=?", (post_id,))
        seller = posts[0][3]
        image = query_db("SELECT image FROM products WHERE id=?", (post_id,))[0][0]
        if image:
            image = "/uploads/"+seller+"/"+image
        comments = query_db("SELECT user, content, rating FROM reviews WHERE post_id=?", (post_id,))
        if comments:
            ovr_rating = posts[0][5]
        else:
            ovr_rating = "no reviews yet"
        if 'username' in session:
            logged_in = True
        else:
            logged_in = False
        
        return render_template('post_details.html', post=posts[0], image=image, comments=comments, rating=ovr_rating, logged_in=logged_in)

@app.route('/my_posts', methods=['GET'])
def my_posts():
    if 'username' in session:
        username = session['username']
        posts = query_db("SELECT title, description, price, id, quantity FROM products WHERE seller=?", (username,))
        posts = posts[::-1]
        return render_template('my_posts.html', posts=posts)
    else:
        flash('You need to log in to access your posts')
        return redirect(url_for('login'))

@app.route('/edit_post/<post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    if request.method == 'GET':
        if 'username' in session:
            username = session['username']
        else:
            flash('You need to log in to edit your post')
            return redirect(url_for('login'))
        post = query_db("SELECT title, description, price, id, quantity FROM products WHERE id=? AND seller=?", (post_id, username))
        if post:
            return render_template('edit_post.html', post=post[0])
        else:
            abort(404)
    else:
        assert request.method == 'POST'
        if 'username' not in session:
            not_normal()
        seller = query_db("SELECT seller FROM products WHERE id=?", (post_id,))[0][0]
        if session['username'] != seller:
            not_normal()
            
        title = request.form.get('product_title')
        description = request.form.get('product_description')
        price = request.form.get('product_price')
        quantity = request.form.get('product_quantity')
        validate_post(title, description, price, quantity)
        price = round(float(price), 2)
        quantity = int(float(quantity))
        
        params = (title, description, price, quantity, post_id)
        query_db("UPDATE products SET title=?, description=?, price=?, quantity=? WHERE id=?", params)
        flash("Post edited")
        return redirect(url_for('my_posts'))

@app.route('/delete_post/<post_id>', methods=['GET', 'POST'])
def delete_post(post_id):
    if request.method == 'GET':
        if 'username' in session:
            username = session['username']
        else:
            return redirect(url_for('login'))
        post = query_db("SELECT title, id FROM products WHERE id=? AND seller=?", (post_id, username))
        if post:
            return render_template('delete_post.html', post=post[0])
        else:
            abort(404)
    else:
        assert request.method == 'POST'
        if 'username' in session:
            username = session['username']
        else:
            not_normal()
        query_db("DELETE FROM products WHERE id=? AND seller=?", (post_id, username))
        flash("Post deleted")
        return redirect(url_for('my_posts'))

@app.route('/manage_images/<post_id>', methods=['GET', 'POST'])
def manage_images(post_id):
    if 'username' not in session:
        flash('You need to log in first')
        return redirect(url_for('login'))
    user = session['username']
    title = query_db('SELECT title FROM products WHERE id=? AND seller=?', (post_id, user))[0][0]
    if title:
        pass
    else:
        flash("The post you want to edit doesn't seem to exist")
        return redirect(url_for('my_posts'))

    if request.method == 'GET':
        main_image = query_db('SELECT image FROM products WHERE id=? AND seller=?', (post_id, user))
        main_image = main_image[0][0]
        return render_template('manage_images.html', title=title, post_id=post_id, main_image=main_image, seller=user)
    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    query_db("UPDATE products SET image=? WHERE id=?", (filename, post_id))
                    newpath = os.path.join(app.root_path, 'uploads/'+user) 
                    if not os.path.exists(newpath):
                        os.makedirs(newpath)
                    upload_path = os.path.join(app.root_path,'uploads/'+user+"/"+filename)
                    file.save(upload_path)
                    flash("image succesfully saved")
                    return redirect(url_for('manage_images', post_id=post_id))
                else:
                    flash("Bad file extension")
            else:
                flash("No image submited")
        else:
            flash('No image submited')
        flash("Image wasn't saved")
        return redirect(url_for('manage_images', post_id=post_id))
    abort(404)

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'username' not in session:
        flash('You need to log in first')
        return redirect(url_for('login'))
    user = session['username']
    
    if request.method == 'GET':
        email = query_db("SELECT email FROM users WHERE username=?", (user,))[0][0]
        if email:
            return render_template('edit_profile.html', email=email)
        else:
            abort(404)
    if request.method == 'POST':
        email = request.form.get('email')
        if ('@' not in email) or ('.' not in email):
            flash('Invalid email')
            return redirect(url_for('edit_profile'))
        if len(email) > MAX_EMAIL_LENGTH:
            flash("Email too long")
            return redirect(url_for('edit_profile'))
        else:
            query_db('UPDATE users SET email=? WHERE username=?', (email, user))
            flash('Profile successfully edited')
            return redirect(url_for('home'))

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'username' not in session:
        flash('You need to log in first')
        return redirect(url_for('login'))
    user = session['username']
    
    if request.method == 'GET':
        return render_template('change_password.html')
    if request.method == 'POST':
        password = request.form.get('passwd')
        current_password = request.form.get('current_passwd')
        if not password:
            flash('Enter a password')
            return redirect(url_for('change_password'))
        if len(password) > MAX_PASSWORD_LENGTH:
            flash('Password too long')
            return redirect(url_for('change_password'))
        username = query_db("SELECT username FROM users WHERE username=? AND password=?", (user, current_password))
        if username:
            query_db("UPDATE users SET password=? WHERE username=?", (password, user))
            flash('Password changed')
            return redirect(url_for('home'))
        else:
            flash("Wrong (current) password")
            return redirect(url_for("change_password"))

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'GET':
        return render_template('feedback.html')
    if request.method == 'POST':
        flash("Thanks for your feedback")
        return redirect(url_for("index"))
            
@app.route('/test', methods=['GET','POST'])
def test():
    return render_template('test.html')
    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
