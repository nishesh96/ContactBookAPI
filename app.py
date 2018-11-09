from flask import Flask, request, flash, make_response, json, jsonify, g, session
from models import db, Contact, User
from flask_httpauth import HTTPBasicAuth
import redis
from redis import ConnectionError
import logging


# Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'my secret'
app.config['DEBUG'] = False

# Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///book.sqlite'
# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root@localhost/book'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
r = redis.Redis(host='0.0.0.0')

auth = HTTPBasicAuth()
user = User()

logging.basicConfig()
logger = logging.getLogger('redis')


@app.route("/redis")
def redisCheck():
    try:
        r.ping()
    except ConnectionError:
        logger.error(
            "Redis isn't running. try `/etc/init.d/redis-server restart`")
        exit(0)


@app.route("/")
def index():
    '''
    Home page
    '''
    return redirect('./contacts')


@app.route('/api/users', methods=['POST'])
def new_user():
    if request.data:
        username = request.json.get('username')
        password = request.json.get('password')

        if username is None or password is None:
            # missing arguments
            return make_response("username and password fields are mandatory for the account to get created \n", 400)
        try:
            if User.query.filter_by(username=username).first() is not None:
                # existing user
                return make_response("User Name Already Exists \n", 400)
            user = User(username=username)
            user.hash_password(password)
            db.session.add(user)
            db.session.commit()
            token = get_auth_token()

        except Exception as e:
            return make_response("error: {0}".format(e), 503)

        return token
    else:
        return make_response('Bad Input \n', 400)


@app.route('/api/users/<int:id>')
def get_user(id):
    user = User.query.get(id)
    if not user:
        return make_response("Please try registering after sometime\n", 500)
    return jsonify({'username': user.username})


@auth.verify_password
def verify_password(username_or_token, password):
    # first try to authenticate by token
    user = User.verify_auth_token(username_or_token)
    if not user:
        # try to authenticate with username/password
        user = User.query.filter(User.username == username_or_token).first()
        if not user or not user.verify_password(password):
            return False
    session["user_id"] = user.id
    return True


@app.route('/api/token')
@auth.login_required
def get_auth_token():
    token = g.user.generate_auth_token()
    return jsonify({'token': token.decode('ascii')})


@app.route("/api/add_contact", methods=('GET', 'POST'))
@auth.login_required
def new_contact():
    response_text = ''
    if request.data:
        data = request.data
        dataDict = json.loads(data)
        try:
            if 'name' in dataDict and 'email' in dataDict and 'mobile' in dataDict:
                try:
                    if Contact.query.filter_by(email=dataDict['email'], userid=session["user_id"]).first() is not None:
                        response_text = response_text + \
                            dataDict['email']+' user already found \n'
                        return make_response(response_text, 503)

                    contact = Contact()
                    contact.email = dataDict['email']
                    contact.mobile = dataDict['mobile']
                    contact.name = dataDict['name']
                    contact.surname = dataDict['surname']
                    contact.userid = session["user_id"]
                    db.session.add(contact)
                    try:
                        db.session.commit()
                        response_text = 'Contacts Added \n' + contact.name
                        #r.set(contact.email, contact)
                        return make_response(response_text, 200)
                    except:
                        db.session.rollback()
                except Exception as e:
                    return make_response("OS1 error: {0}".format(e), 503)
            else:
                response_text = response_text + ' Values not given properly \n'
        except Exception as e:
            return make_response("OS error: {0}".format(e), 503)

        if response_text == '':
            response_text = 'Contacts Not Added \n'
            return make_response(response_text, 200)
        else:
            response = make_response(
                "\nBad Request - Input JSON is empty\n", 400)
            return response


@app.route("/api/edit_contact/<id>", methods=('GET', 'POST'))
@auth.login_required
def edit_contact(id):
    my_contact = Contact.query.filter_by(
        id=id, userid=session["user_id"]).first()
    if request.data:
        data = request.data
        dataDict = json.loads(data)
        try:
            # Update contact
            if 'name' in dataDict:
                my_contact.name = dataDict['name']
            if 'mobile' in dataDict:
                my_contact.mobile = dataDict['mobile']
            if 'surname' in dataDict:
                my_contact.surname = dataDict['surname']
            if 'email' in dataDict:
                my_contact.email = dataDict['email']
            try:
                current_db_sessions = db.session.object_session(my_contact)
                current_db_sessions.add(my_contact)
                current_db_sessions.commit()
            except Exception as e:
                db.session.add(my_contact)
                db.session.commit()
                # User info
                flash('Saved successfully', 'success')
        except:
            db.session.rollback()
            flash('Error update contact.', 'danger')
    return make_response("Contact editted succesfully -"+my_contact.email, 200)


@app.route("/api/contacts")
@auth.login_required
def contacts():
    '''
    Show alls contacts
    '''
    contacts = Contact.query.filter_by(
        userid=session["user_id"]).order_by(Contact.name).all()
    output = ''
    for contact in contacts:
        output += str(contact.id) + "\t" + contact.name + "\t" + contact.surname + \
            "\t" + contact.email + "\t" + str(contact.phone) + "\n"
    return make_response(output, 200)


@app.route("/api/search", methods=('POST',))
@auth.login_required
def search():
    '''
    Search
    '''
    name_search = ""
    email_search = ""
    if request.data:
        data = request.data
        dataDict = json.loads(data)
    if 'name' in dataDict:
        name_search = dataDict['name']
    if 'email' in dataDict:
        email_search = dataDict['email']
    if name_search:
        all_contacts = Contact.query.filter(
            Contact.name.contains(name_search),
        ).filter(Contact.userid.contains(session["user_id"])).order_by(Contact.name).limit(10)
    if email_search:
        #val = r.hget(email_search)
        # if val is not None:
        #    all_contacts = val
        # else:
        all_contacts = Contact.query.filter(
            Contact.email.contains(email_search)
        ).filter(Contact.userid.contains(session["user_id"])).order_by(Contact.name).limit(10)
    output = ''
    for contact in all_contacts:
        output += str(contact.id) + "\t" + contact.name + "\t" + contact.surname + \
            "\t" + contact.email + "\t" + str(contact.phone) + "\n"
    return make_response(output, 200)


@app.route("/api/contacts/delete/<id>", methods=('GET', 'POST'))
@auth.login_required
def contacts_delete(id):
    '''
    Delete contact
    '''
    try:
        my_contact = Contact.query.filter_by(
            id=id, userid=session["user_id"]).first()
        current_db_sessions = db.session.object_session(my_contact)
        current_db_sessions.delete(my_contact)
        current_db_sessions.commit()
        r.flushdb()
    except:
        db.session.rollback()
    return make_response("Contact Deleted", 200)


if __name__ == "__main__":
    app.run(host="0.0.0.0")
    app.debug = True
