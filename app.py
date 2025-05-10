from flask import Flask,render_template,url_for,redirect,request,flash,session
from flask_mysqldb import MySQL
from markupsafe import Markup
from werkzeug.security import generate_password_hash,check_password_hash
from datetime import datetime
import uuid
from config import Config
import locale

app = Flask(__name__,template_folder="templates",static_folder="static")
app.config.from_object(Config)

mysql = MySQL(app)

def token_generate():
    return str(uuid.uuid4())

def token_upload(emp_id):
    token = token_generate()
    try:
        with mysql.connection.cursor() as connect:
            connect.execute("UPDATE software_developer SET session_token = %s WHERE id = %s", (token, emp_id))
            mysql.connection.commit()
            session['session_token'] = token
        return 'success'
    except Exception as e:
        session.clear()
        return f"Database error: {str(e)}"

def currency(salary):
    # Set to Indian locale
    locale.setlocale(locale.LC_ALL, 'en_IN')
    num = int(salary)
    formatted = locale.format_string("%d", num, grouping=True)
    return formatted

def set_log_out():
    with mysql.connection.cursor() as connect:
        sql = "UPDATE software_developer SET status = %s, logout_time = CURRENT_TIMESTAMP, session_token = NULL WHERE emp_id = %s"
        connect.execute(sql,('Inactive', session.get('emp_id')))
        mysql.connection.commit()

@app.before_request
def check_status():

    if request.endpoint in ['logIn', 'signUp']:
        if session.get('emp_id'):
            return redirect(url_for('home'))
        
    elif session.get('emp_id') and session.get('session_token'):
        emp_id = session.get('emp_id')
        session_token = session.get('session_token')
        with mysql.connection.cursor() as connect:
            connect.execute("SELECT session_token,message FROM software_developer WHERE emp_id = %s", (emp_id,))
            db_token = connect.fetchone()
            if not db_token or db_token.get('session_token') != session_token:
                sql = "UPDATE software_developer SET status = %s, logout_time = CURRENT_TIMESTAMP, session_token = NULL WHERE emp_id = %s"
                connect.execute(sql,('Inactive', session.get('emp_id')))
                mysql.connection.commit()
                session.clear()
                flash("You have been logged out from another location.","tryagain")
                return redirect(url_for('logIn'))
            if session and db_token.get('message'):
                sql = "UPDATE software_developer SET message = NULL WHERE emp_id = %s"
                connect.execute(sql,(session.get('emp_id'),))
                mysql.connection.commit()
                flash(Markup("Someone tried to log in to your account.<br>Please change your password."),"warning")
    else:
        pass

def name_align(name):
    
    username_parts = name.replace('.', ' ').split()
    username_parts = [part for part in username_parts if part.strip()]

    if len(username_parts) == 1:
        return username_parts[0].strip()

    elif len(username_parts) >= 2:
        if len(username_parts[0]) > len(username_parts[-1]):
            return ' '.join(username_parts)
        else:
            mid_index = len(username_parts) // 2
            for i in range(mid_index):
                if len(username_parts[i]) < len(username_parts[-(1 + i)]):
                    if len(username_parts[i]) <= 2:
                        username_parts[i], username_parts[-(1 + i)] = username_parts[-(1 + i)], username_parts[i]
                    else:
                        if mid_index <= 2:
                            username_parts[-1] = username_parts[mid_index]
                            username_parts.pop(mid_index)
                    break
            return ' '.join(username_parts)
    
    return name

def time_formate(value):

    if not value:
        return ""

    if isinstance(value, datetime):
        dt_obj = value
    else:
        dt_obj = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")

    # Format it into desired form
    formatted_str = dt_obj.strftime("%d %b | %I:%M %p")

    return formatted_str

@app.route('/')
def home():
    return render_template("home.html",current_tab='home',job_role = session.get('job_role'))

@app.route('/signup', methods=['POST', 'GET'])
def signUp():

    if request.method == 'POST':
        # Get form data
        username = request.form.get('username').strip().title()
        username = name_align(username)
        email = request.form.get('email').strip()
        department = request.form.get('department')
        job_role = request.form.get('job_role')
        joined_date = request.form.get('joined_date')
        password = request.form.get('password').strip()
        confirm_password = request.form.get('confirm_password').strip()

        # Check if passwords match
        if password != confirm_password:
            flash(Markup("The password and confirmation password do not match.<br>Please re-enter both fields carefully."), "tryagain")
            return render_template("signup.html", data = request.form, category = 'wrong_password')

        try:
            with mysql.connection.cursor() as connect:
                # Check if email already exists
                sql = "SELECT id FROM software_developer WHERE email=%s"
                connect.execute(sql, (email,))
                
                if connect.fetchone():
                    message = Markup(f"""
                        This Email ID is already registered.<br>
                        Please use a different email or 
                        <a href="{url_for('logIn')}" class="login-link">Login</a> to continue.
                    """)
                    flash(message, "tryagain")
                    return render_template("signup.html", data = request.form , category ='exist_email')

                hash_password = generate_password_hash(password)

                formatted_date = datetime.strptime(joined_date, "%d-%m-%Y").strftime("%Y-%m-%d")
               
                # Insert new user
                sql = "INSERT INTO software_developer(username, email, password, department, job_role, joined_date) VALUES (%s, %s, %s, %s, %s, %s)"
                connect.execute(sql, (username, email, hash_password, department, job_role, formatted_date))
                
                last_inserted_id = connect.lastrowid

                employee_id = f"EMP{str(last_inserted_id).zfill(4)}"
                token = token_generate()
                sql = "UPDATE software_developer SET emp_id = %s, status = %s, login_time = CURRENT_TIMESTAMP, session_token = %s WHERE id = %s"
                connect.execute(sql,(employee_id,'Active',token, last_inserted_id))
                mysql.connection.commit()

                session['session_token'] = token
                session['emp_id'] = employee_id
                session.permanent = True
                flash("Signup successful! Welcome", "success")
                return redirect(url_for('profile'))

        except Exception as e:
            mysql.connection.rollback()
            session.clear()
            flash("Database error: " + str(e), "tryagain")
            return render_template("signup.html", data = request.form, category = "")
    return render_template("signup.html", data = {}, category = "")

@app.route('/login', methods=['POST', 'GET'])
def logIn():

    if request.method == 'POST':
        # Get form data
        email = request.form['email'].strip()
        password = request.form['password'].strip()

        try:
            with mysql.connection.cursor() as connect:
                # Check if email already exists
                sql = "SELECT emp_id,password,status FROM software_developer WHERE email=%s"
                connect.execute(sql, (email,))
                user = connect.fetchone()

                if user is None:
                    message = Markup(f"""
                        This Email ID is not registered.<br>
                        Please check your entry or <a href="{url_for('signUp')}" class="signup-link">signup</a> to continue.
                    """)
                    flash(message, "tryagain")
                    return render_template("login.html", data = session, category = "invalid_email")
                
                elif not check_password_hash(user.get('password',''), password):
                    flash("Incorrect password. Please try again.","tryagain")
                    return render_template("login.html",data = request.form, category = "wrong_password")
                
                elif(user.get('status','') == 'Active'):
                    sql = "UPDATE software_developer SET message = 'warning' WHERE emp_id = %s"
                    connect.execute(sql,(user.get('emp_id'),))
                    mysql.connection.commit()
                    flash("This ID is already logged in from another device.","tryagain")
                    return render_template("login.html",data = request.form, category = "")
                else:
                    token = token_generate()
                    sql = "UPDATE software_developer SET status = %s, login_time = CURRENT_TIMESTAMP , logout_time = NULL, session_token = %s WHERE emp_id = %s"
                    connect.execute(sql,('Active', token, user.get('emp_id')))
                    mysql.connection.commit()
                    session['session_token'] = token
                    session['emp_id'] = user.get('emp_id')
                    session.permanent = True
                    flash("Login successful!", "success")
                    return redirect(url_for('profile'))
        except Exception as e:
            session.clear()
            flash("Database error: " + str(e), "tryagain")
            return render_template("login.html", data = request.form, category = "")
    return render_template("login.html", data = {}, category = "")

@app.route('/profile')
def profile():
    if not session:
        return redirect(url_for('logIn'))
    with mysql.connection.cursor() as connect:
        sql = """
            SELECT emp_id, username, email, department, joined_date, job_role, mobile, salary, status, login_time, logout_time, mobile, gender, marital_status, date_of_birth, skill_set, street, city, state, zip, country 
            FROM software_developer 
            WHERE emp_id = %s
        """
        connect.execute(sql, (session.get('emp_id'),))
        data = connect.fetchone()

        if data is None:
            session.clear()
            return redirect(url_for("home"))
        if data.get('salary',''):
            data['salary'] = f"Rs. {currency(data.get('salary'))}"
        if data.get('street'):
            street = f'{data.get('street')}, '
        else:
            street = ''
        if data.get('city'):
            if data.get('zip'):
                city = f'{data.get('city')} - {data.get('zip')}'
            else:
                city = f'{data.get('city')}'
        else:
            city = ''
        data['address'] = f"{street}{city}"
        session['job_role'] = data.get('job_role')

        return render_template("home.html", employee_data = data, current_tab = 'profile')

@app.route('/employees-details')
def employees():
    if not session:
        return redirect(url_for('logIn'))
    if session.get('job_role','').lower() == 'manager':
        with mysql.connection.cursor() as connect:
            sql = """
                SELECT emp_id, username, email, department, job_role, joined_date, salary, status, login_time, logout_time, mobile, gender, marital_status, date_of_birth, skill_set, street, city, state, zip, country
                FROM software_developer 
                WHERE job_role != %s
                ORDER BY status ASC;
            """
            connect.execute(sql, (session.get('job_role'),))
            datas = connect.fetchall()
            for data in datas:
                if data.get('login_time'):
                    data['login_time'] = time_formate(data['login_time'])

                if data.get('logout_time'):
                    data['logout_time'] = time_formate(data['logout_time'])

                if data.get('salary',''):   
                    data['salary'] = f"Rs. {currency(data.get('salary'))}"
                if data.get('street'):
                    street = f'{data.get('street')}, '
                else:
                    street = ''
                if data.get('city'):
                    if data.get('zip'):
                        city = f'{data.get('city')} - {data.get('zip')}'
                    else:
                        city = f'{data.get('city')}'
                else:
                    city = ''
                data['address'] = f"{street}{city}"

            return render_template("home.html", job_role = session.get('job_role'), employees_data = datas, current_tab = 'employees')
    else:
        session.clear()
        return redirect(url_for('home'))

def isvalid(emp_id,password):
    with mysql.connection.cursor() as connect:
        sql = "SELECT password FROM software_developer WHERE emp_id=%s"
        connect.execute(sql, (emp_id,))
        user = connect.fetchone()
        if check_password_hash(user['password'], password):
            return True
        else:
            return False

    
def delete_action(emp_id):
    with mysql.connection.cursor() as connect:
        sql = "DELETE FROM software_developer WHERE emp_id = %s"
        connect.execute(sql, (emp_id,))
        mysql.connection.commit()
        return True
    
@app.route('/<tab>/delete-account',methods=['POST', 'GET'])
def delete(tab):
    if not session:
        return redirect(url_for('logIn'))
    emp_id = request.args.get('emp_id','')

    if ((session.get('job_role','').lower() in ['manager'] and session.get('emp_id') != emp_id) and tab == 'employees'):
        if request.method == 'POST':
            delete_action(emp_id)
            return redirect(url_for('employees'))
    elif (emp_id==session.get('emp_id') and tab == 'profile'):
        if request.method == 'POST':
            password = request.form.get('password')
            if isvalid(emp_id,password):
                delete_action(emp_id)
                session.clear()
                return redirect(url_for('home'))
            else:
                return render_template("delete.html", job_role = session.get('job_role',''), tab=tab, emp_id=emp_id, category = "wrong_password")
    else:
        session.clear()
        return redirect(url_for('home'))
    return render_template("delete.html", job_role = session.get('job_role',''),tab=tab,emp_id=emp_id)

def email_exist(emp_id,email):
    with mysql.connection.cursor() as connect:
        sql = """
        SELECT email 
        FROM software_developer 
        WHERE emp_id != (
            SELECT emp_id FROM software_developer WHERE emp_id = %s LIMIT 1
        ) AND email = %s
        """
        connect.execute(sql, (emp_id,email)) 
        return connect.fetchone() is not None 
    
def get_data(tab,emp_id):
    try:
        with mysql.connection.cursor() as connect:
                sql = "SELECT username, email, department, joined_date, job_role, mobile, date_of_birth,salary, gender, marital_status skill_set, street, city, state, zip, country FROM software_developer WHERE emp_id=%s"
                connect.execute(sql, (emp_id,))
                return connect.fetchone()
    except:
        return None
    
def update_data(datas,emp_id):

    try:
        with mysql.connection.cursor() as connect:
            for key, value in datas.items():
                sql = f"UPDATE software_developer SET {key} = %s WHERE emp_id = %s"
                connect.execute(sql, (value, emp_id))
            mysql.connection.commit()
            return 'success'
    except Exception as e:
        return f"Database error:  {str(e)}"
    
def data_filter(db_data,form_data):
    local_dict = dict()
    
    for key, value in form_data.items():
        if key == 'password' and value != '':
            local_dict[key] = generate_password_hash(str(value))
            token = token_generate()
            local_dict['session_token'] = token
        elif key == 'username' and value != '':
            local_dict[key] = name_align(value)
        elif (key == 'joined_date' or key == 'date_of_birth') and value != '':
            formatted_date = datetime.strptime(value, "%d-%m-%Y").strftime("%Y-%m-%d")
            if formatted_date != db_data.get(key):
                local_dict[key] = formatted_date
        elif (key == 'skill_set' and value != ''):
            words = value.split(',')
            acronyms = ['AI', 'ML', 'HTML', 'CSS', 'SQL', 'JSON', 'XML', 'YAML', 'PHP']
            words = value.split(',')
            formatted_words = []
            for word in words:
                word = word.strip()
                if word.upper() in acronyms:
                    formatted_words.append(word.upper())
                else:
                    formatted_words.append(word.title())
            data = ', '.join(sorted(set(formatted_words)))
            if data != db_data.get(key):
                local_dict['skill_set'] = data
        elif (key == 'mobile' and value != ''):
            num_directory = {'india':'+91','uk':'+44','usa':'+1'}
            size = 0
            if ' ' in value:
                size = value.index(' ')
            
            country = (form_data.get('country','india')).lower()
            if  num_directory.get(country,'india') in value and ' ' in value:
                num = value

            else:
                country = form_data.get('country','india').lower()
                if size <=3:
                    value = value[size:]
                    value = value.strip()
                if num_directory.get(country,'india') in value:
                    value =  value.replace(num_directory.get(country,'india'),'')
                value =  value.replace('-','').replace(' ','').replace(num_directory.get(country,''),'').replace('(','').replace(')','')
                value = str(int(value))
                value = value[ :10]
                if country == 'uk':
                    num = f"{num_directory.get('uk')} {value[:4]} {value[4:]}"
                elif country == 'usa':
                    num = f"{num_directory.get('usa')} ({value[:3]}) {value[3:6]}-{value[6:]}"
                else:
                    num = f"+91 {value}"
            local_dict[key] = num
           
        else:
            if (value != '' and value != db_data.get(key)) or (db_data.get(key) and not(value)):
                if (key == 'joined_date' or key == 'date_of_birth'):
                    local_dict[key] = None
                else:
                    local_dict[key] = value
    return local_dict

@app.route('/<tab>/edit-account',methods=['POST', 'GET'])
def edit(tab):
    if not session:
        return redirect(url_for('logIn'))
    emp_id = request.args.get('emp_id','')
    db_data = get_data(tab,emp_id)
    if db_data:
        if (session.get('job_role','').lower() in ['manager'] and session.get('emp_id') != emp_id and tab == 'employees'):
            if request.method == 'POST':
                form_data = dict()
                form_data['username'] = request.form.get('username').strip().title()
                form_data['email'] = request.form.get('email').strip()
                form_data['password'] = request.form.get('password').strip()
                form_data['department'] = request.form.get('department')
                form_data['joined_date'] = request.form.get('joined_date')
                form_data['job_role'] = request.form.get('job_role')
                form_data['salary'] = request.form.get('salary')
                if email_exist(emp_id, form_data.get('email')):
                    message = Markup(f"""
                        This Email ID is already registered.<br>
                        Please use a different email to continue.
                    """)
                    flash(message, "exist_email")
                    return render_template("edit.html", data = form_data ,job_role = session.get('job_role'),tab=tab,emp_id=emp_id, category ='exist_email')
                store_data = data_filter(db_data,form_data)
                result = update_data(store_data, emp_id)
                if result == 'success':
                    return redirect(url_for('employees'))
                else:
                    flash(result, "tryagain")
                    return render_template("edit.html", data = form_data ,job_role = session.get('job_role'),tab=tab,emp_id=emp_id, category ='tryagain')

        elif (emp_id==session.get('emp_id') and tab == 'profile'):
            if request.method == 'POST':
                form_data = dict()
                form_data['username'] = request.form.get('username','').strip().title()
                form_data['email'] = request.form.get('email','').strip()
                form_data['mobile'] = request.form.get('mobile','').strip()
                form_data['marital_status'] = request.form.get('marital_status','')
                form_data['gender'] = request.form.get('gender','')
                form_data['date_of_birth'] = request.form.get('date_of_birth','')
                form_data['skill_set'] = request.form.get('skill_set','')
                form_data['street'] = request.form.get('street','').strip()
                form_data['city'] = request.form.get('city','').strip()
                form_data['state'] = request.form.get('state','').strip()
                form_data['zip'] = request.form.get('zip','').strip()
                form_data['country'] = request.form.get('country','')
                if email_exist(emp_id, form_data.get('email')):
                    message = Markup(f"""
                        This Email ID is already registered.<br>
                        Please use a different email or 
                        <a href="{url_for('logIn')}" class="login-link">Login</a> to continue.
                    """)
                    flash(message, "exist_email")
                    return render_template("edit.html", data = form_data ,job_role = session.get('job_role'),tab=tab,emp_id=emp_id, category ='exist_email')
                store_data = data_filter(db_data,form_data)
                result = update_data(store_data, emp_id)
                if result == 'success':
                    return redirect(url_for('profile'))
                else:
                    flash(result, "tryagain")
                    return render_template("edit.html", data = form_data ,job_role = session.get('job_role'),tab=tab,emp_id=emp_id, category ='tryagain')
        return render_template("edit.html",data = db_data, job_role = session.get('job_role'),tab=tab,emp_id=emp_id)
    else:
        session.clear()
        return redirect(url_for('home'))

def create_salary(job_role):
    salary = min_salaries = {
    "Manager": 800000,
    "Software Engineer": 500000,
    "UI/UX Designer": 400000,
    "Front-End Developer": 450000,
    "Back-End Developer": 500000,
    "Full Stack Developer": 550000,
    "QA Engineer": 400000,
    "DevOps Engineer": 600000,
    "Software Architect": 1000000,
    "Mobile App Developer": 500000
    }
    return salary.get(job_role,300000)

def create_password(joined_date, username):
    try:
        date_part = f'{joined_date[-2:]}{joined_date[5:7]}'
    except (TypeError, IndexError):
        date_part = '1234'

    if username:
        username_parts = username.replace('.', ' ').split()
    else:
        username_parts = []

    if len(username_parts) == 1:
        user = username_parts[0].lower().strip()
    elif len(username_parts) >= 2:
        filtered = [u for u in username_parts if len(u) > 2]
        user = filtered[0].lower().strip() if filtered else username_parts[0].lower().strip()
    else:
        user = 'user'
    return f'{user}@{date_part}'
 
@app.route('/<tab>-details/add-employee', methods=['GET', 'POST'])
def add_employee(tab):
    if not session:
        return redirect(url_for('logIn'))
    if session.get('job_role','').lower() not in ['manager','ceo']:
        session.clear()
        return redirect(url_for('home'))

    elif request.method == 'POST':
        username = request.form.get('username','').strip().title()
        username = name_align(username)
        email = request.form.get('email','').strip()
        department = request.form.get('department','')
        job_role = request.form.get('job_role','')
        joined_date = request.form.get('joined_date','')
        password = request.form.get('password','').strip()
        salary = request.form.get('salary','')

        try:
            with mysql.connection.cursor() as connect:
                # Check if email already exists
                sql = "SELECT id FROM software_developer WHERE email=%s"
                connect.execute(sql, (email,))
                
                if connect.fetchone():
                    message = Markup(f"""
                        This Email ID is already registered.<br>
                        Please use a different email to continue.
                    """)
                    flash(message, "tryagain")
                    return render_template("signup.html", data = request.form , category ='exist_email')
                
                formatted_date = datetime.strptime(joined_date, "%d-%m-%Y").strftime("%Y-%m-%d")

                if not password:
                    password = create_password(formatted_date, username)
                hash_password = generate_password_hash(password)
                
                if not salary:
                    salary = create_salary(job_role)
                else:
                    salary = int(salary)

                # Insert new user
                sql = "INSERT INTO software_developer(username, email, password, department, job_role, joined_date, salary) VALUES (%s, %s, %s, %s, %s, %s,%s)"
                connect.execute(sql, (username, email, hash_password, department, job_role, formatted_date, salary))
                
                last_inserted_id = connect.lastrowid

                employee_id = f"EMP{str(last_inserted_id).zfill(4)}"
                sql = "UPDATE software_developer SET emp_id = %s WHERE id = %s"
                connect.execute(sql,(employee_id, last_inserted_id))
                mysql.connection.commit()
                if tab == 'employees':
                    return redirect(url_for('add_employee', tab = tab))
                else:
                    set_log_out()
                    session.clear()
                    return redirect(url_for('logIn'))
                
        except Exception as e:
            mysql.connection.rollback()
            flash("Database error: " + str(e), "tryagain")
            return render_template("add_employee.html", data = request.form, category = "",tab=tab)
    else:
        return render_template("add_employee.html", data = {}, category = "",tab=tab)

@app.route('/profile/change-password', methods=['GET', 'POST'])
def change_password():
    if not session:
        return redirect(url_for('logIn'))

    data = {}
    emp_id = session.get('emp_id')

    if request.method == 'POST':
        form_type = request.form.get('form_type', '')

        if form_type == 'verify':
            old_password = request.form.get('old_password', '').strip()
            session['old_password'] = old_password
            data['old_password'] = old_password

            try:
                with mysql.connection.cursor() as connect:
                    sql = "SELECT password FROM software_developer WHERE emp_id=%s"
                    connect.execute(sql, (emp_id,))
                    user = connect.fetchone()

                    if user and check_password_hash(user.get('password', ''), old_password):
                        flash(Markup("Old password is verified. <br>Please enter a new password to proceed."), "success")
                        return render_template(
                            'change_password.html',
                            emp_id=emp_id,
                            data=data,
                            validate=True,
                            category=""
                        )
                    else:
                        flash("Incorrect password. Please try again.", "tryagain")
                        return render_template(
                            'change_password.html',
                            emp_id=emp_id,
                            data=data,
                            validate=False,
                            category="wrong_password"
                        )
            except Exception as e:
                flash("Database error: " + str(e), "tryagain")
                return render_template(
                    'change_password.html',
                    emp_id=emp_id,
                    data=data,
                    validate=False,
                    category=""
                )

        elif form_type == 'change':
            new_password = request.form.get('new_password', '').strip()
            confirm_password = request.form.get('confirm_password', '').strip()

            data['new_password'] = new_password
            data['confirm_password'] = confirm_password

            if new_password != confirm_password:
                flash(Markup("The password and confirmation password do not match.<br>Please re-enter both fields carefully."), "tryagain")
                return render_template(
                    'change_password.html',
                    emp_id=emp_id,
                    data=data,
                    validate=True,
                    category='wrong_password'
                )

            hashed_password = generate_password_hash(new_password)
            token = token_generate()

            try:
                with mysql.connection.cursor() as connect:
                    sql = "UPDATE software_developer SET password=%s, session_token=%s WHERE emp_id=%s"
                    connect.execute(sql, (hashed_password, token, emp_id))
                    session['session_token'] = token
                mysql.connection.commit()

                flash("Password successfully updated.", "success")
                return redirect(url_for('profile'))

            except Exception as e:
                flash("Database error: " + str(e), "tryagain")
                return render_template(
                    'change_password.html',
                    emp_id=emp_id,
                    data=data,
                    validate=True,
                    category=""
                )

    return render_template(
        'change_password.html',
        emp_id=emp_id,
        data=data,
        validate=False,
        category=""
    )

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    if not session:
        return redirect(url_for('logIn'))
    if request.method == 'POST':
        set_log_out()
        session.clear()
        flash("Logout successful!", "success")
        return redirect(url_for('home'))
    return render_template("home.html",current_tab='logout',job_role = session.get('job_role'))

@app.route("/auto-logout")
def auto_logout():
    if 'emp_id' in session:
        set_log_out()
        session.clear()
    return ('', 204)

if __name__=="__main__":
    app.run(debug=True)