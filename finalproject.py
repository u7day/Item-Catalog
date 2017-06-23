#import files
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, Mitems, Customer
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)


CLIENT_ID = json.loads(
    open('uday.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Restaurant Menu Application"


# Connect to the Database and create a db session
engine = create_engine('sqlite:///restaurantmenuwithusers.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()
session.rollback()

# this function initiates when we click on login button it renders login template and state is passed which is a token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)

# this function is implemented when we click on google signin button





# Edits specific restaurant, if user not signed in redirects to login. If selected restaurant is not created by user, error message flashed and redirects to
# restraunt page. If restaurant id does not exists, flashes message and redirects. If none of above is true, edits current restaurnat name.
@app.route('/dine/<int:restaurant_id>/edit',
           methods=['GET', 'POST'])
def editRestaurant(restaurant_id):
    if 'username' not in login_session:
        flash("To edit restaurant first login")
        return redirect('/login')
    output=''
    itemedit = session.query(Restaurant).filter_by(id=restaurant_id).first()
    if itemedit == None:
        flash("Incorrect Restaurant Id")
        return redirect(url_for('restaurantlist'))
    if itemedit.user_id != login_session['user_id']:
        flash("Unauthorised Access to this restaurant.It is not your Restaurant") 
        return redirect(url_for('restaurantlist'))
    if request.method == 'POST':
        if request.form['name']:
            n=request.form['name']
            output+='Restaurant '
            output+= itemedit.name
            output+=' renamed to '
            output+=n
            itemedit.name = n
        session.add(itemedit)
        session.commit()
        flash(output)
        return redirect(url_for('restaurantlist'))
    else:
        return render_template(
            'editRestaurant.html', restaurant_id=restaurant_id, item=itemedit)


# Creating new restaurant
@app.route('/dine/new', methods=['GET', 'POST'])
def newRestaurant():
    # If user not logged in it redirects to login page.
    if 'username' not in login_session:
        flash("First login to create new restaurant")
        return redirect('/login')
    # Shows form to create new restaurant and the id given by user is validated
    if request.method == 'POST':
        newItem = Restaurant(name=request.form['name'], user_id=login_session['user_id'])
        session.add(newItem)
        session.commit()
        flash("New menu item "+newItem.name+" created!")
        return redirect(url_for('restaurantlist'))
    else:
        return render_template('newRestaurant.html')


# Shows all restuarants if user not LoggedIn, else shows restaurants created by the user
@app.route('/')
@app.route('/dine')
def restaurantlist():
    restlist = session.query(Restaurant).all()
    if 'username' not in login_session:
        return render_template('publicrestaurants.html', restaurants=restlist)
    else:
        restlist = session.query(Restaurant).filter_by(user_id=login_session['user_id'])
        return render_template('restaurant.html', items=restlist)

# Delete restaurant code, if user not signedin redirected to login. If selected restaurant is not created by user, error message flashed and redirected to
# restraunt page. If restaurant id does not exists, flashes message and redirects. If none of above is true, deletes current restaurant and its menu items.
@app.route('/dine/<int:restaurant_id>/delete',
           methods=['GET', 'POST'])
def deleteRestaurant(restaurant_id):
    if 'username' not in login_session:
        flash("First login to delete restaurant")
        return redirect('/login')
    delItem = session.query(Restaurant).filter_by(id=restaurant_id).first()
    if delItem == None:
        flash("Incorrect Restaurant Id")
        return redirect(url_for('restaurantlist'))
    if delItem.user_id != login_session['user_id']:
        flash("Unauthorised Access.It is not your Restaurant") 
        return redirect(url_for('restaurantlist'))
    if request.method == 'POST':
        session.delete(delItem)
        session.commit()
        itemToDelete = session.query(Mitems).filter_by(restaurant_id=restaurant_id).all()
        for i in itemToDelete:
            session.delete(i)
            session.commit()
        flash("Restaurant "+delItem.name+" Deleted")
        return redirect(url_for('restaurantlist'))
    else:
        return render_template('deleteRestaurant.html', item=delItem)

@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validates state token passed to login page.
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code.
    code = request.data

    try:
        # stores credentials object
        oauth_flow = flow_from_clientsecrets('uday.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # validates access token.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # if error occurs passes 500 as status and aborts.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify access token.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # valdates access token for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response
    #if user already logged in then sends status as 200.
    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        flash("you are now logged in as %s" % login_session['user_id'])
        return response

    # Store credentials in the session for later use.
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    # Store user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    #cheks if user is already in user database. If not it stores user info in User database.
    useremail=getUserID(login_session['email'])
    if not useremail:
        useremaail=createUser(login_session)
        login_session['user_id']=useremaail
    else:
        login_session['user_id']=useremail



    #Creates an output for user and sends successful state 200.
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 150px; height: 150px;border-radius: 100px;-webkit-border-radius: 100px;-moz-border-radius: 100px;margin-top:20px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done"
    response = make_response(json.dumps(output),
                                 200)
    response.headers['Content-Type'] = 'application/json'
    return response


# Menu of a specific restaurant
@app.route('/dine/<int:restaurant_id>/menu')
def restaurantMenu(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).first()
    if restaurant == None:
        flash("incorrect restaurant id")
        return redirect(url_for('restaurantlist'))
    creator = getUserInfo(restaurant.user_id)
    items = session.query(Mitems).filter_by(restaurant_id=restaurant_id)
    if 'username' not in login_session or creator.id != login_session['user_id']:
        return render_template('publicmenu.html', restaurant=restaurant, items=items, restaurant_id=restaurant_id, creator=creator)
    else:
        return render_template('menu.html', restaurant=restaurant, items=items, restaurant_id=restaurant_id, creator=creator)


# Edits the specific menu Item
@app.route('/dine/<int:restaurant_id>/<int:menu_id>/edit',
           methods=['GET', 'POST'])
def editMenuItems(restaurant_id, menu_id):
    if 'username' not in login_session:
        flash("First Login to create new restaurant")
        return redirect('/login')
    output=''
    editedItem = session.query(Mitems).filter_by(id=menu_id).first()
    if editedItem == None:
        flash("Menu Id Incorrect")
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    if editedItem.restaurant_id != restaurant_id:
        flash("Incorrect Restaurant and Menu Id combination")
        return redirect(url_for('restaurantlist'))
    if editedItem.user_id != login_session['user_id']:
        flash("Unauthorised Access.It is not your item") 
        return redirect(url_for('restaurantMenu'))

    if request.method == 'POST':
        if request.form['name']:
            n=request.form['name']
            output+='menu item '
            output+= editedItem.name
            output+=' renamed to '
            output+=n
            editedItem.name = n
        session.add(editedItem)
        session.commit()
        flash(output)
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    else:
        return render_template(
            'editmenuitem.html', restaurant_id=restaurant_id, menu_id=menu_id, item=editedItem)


# New menu Item created. If user not logged in redirected to restaurant menu page 
@app.route('/dine/<int:restaurant_id>/new', methods=['GET', 'POST'])
def newMenuItems(restaurant_id):
    if 'username' not in login_session:
        flash("First Login to create new restaurant")
        return redirect('/login')
    if request.method == 'POST':
        newItem = Mitems(name=request.form['name'], description=request.form[
                           'description'], price=request.form['price'], course=request.form['co'], restaurant_id=restaurant_id,  user_id=login_session['user_id'])
        session.add(newItem)
        session.commit()
        flash("New menu item "+newItem.name+" created!")
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    else:
        return render_template('newmenuitem.html', restaurant_id=restaurant_id)




# Returns JSON endpoint of restaurants
@app.route('/dine/JSON')
def dineJSON():
    products = session.query(Restaurant).all()
    return jsonify(Restaurant=[i.poio for i in products])

# Deletes the Specific Menu Item
@app.route('/dine/<int:restaurant_id>/<int:menu_id>/delete',
           methods=['GET', 'POST'])
def deleteMenuItems(restaurant_id, menu_id):
    if 'username' not in login_session:
        flash("First Login to create new restaurant")
        return redirect('/login')
    itemToDelete = session.query(Mitems).filter_by(id=menu_id).first()
    if itemToDelete == None:
        flash("Menu Id incorrect")
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    if itemToDelete.restaurant_id != restaurant_id:
        flash("Incorrect Restaurant and Menu Id combination")
        return redirect(url_for('restaurantlist'))
    if itemToDelete.user_id != login_session['user_id']:
        flash("Unauthorised Access.It is not your item") 
        return redirect(url_for('restaurantMenu'))
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash("Menu item "+itemToDelete.name+" deleted")
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    else:
        return render_template('deleteconfirmation.html', item=itemToDelete)

# Returns JSON endpoint of users
@app.route('/user/JSON')
def customerJSON():
    products = session.query(Customer).all()
    return jsonify(Customer=[i.poio for i in products])



# Returns JSON endpoint of specific menu item of specific restaurant
@app.route('/dine/<int:restaurant_id>/menu/<int:menu_id>/JSON')
def foodListspecifyJSON(restaurant_id,menu_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).first()
    if restaurant == None:
        flash("Restaurant Id incorrect")
        return redirect(url_for('restaurantlist'))
    products = session.query(Mitems).filter_by(id=menu_id).first()
    if products == None:
        flash("Menu Id incorrect")
        return redirect(url_for('restaurantMenu',restaurant_id=restaurant_id))
    return jsonify(Mitems=[products.serialize])


# Creates new user and data to Customer database is added
def createUser(login_session):
    newUser = Customer(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(Customer).filter_by(email=login_session['email']).one()
    return user.id

# If user LoggedIn, tupple containing user data returned else redirects
def getUserInfo(user_id):
    user = session.query(Customer).filter_by(id=user_id).first()
    if user == None:
        flash("Unauthorised User")
        return redirect(url_for('restaurantlist'))
    return user

# Returns JSON endpoint of menu of a specific restaurant
@app.route('/dine/<int:restaurant_id>/menu/JSON')
def foodListJSON(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).first()
    if restaurant == None:
        flash("Restaurant Id incorrect")
        return redirect(url_for('restaurantlist'))
    products = session.query(Mitems).filter_by(
        restaurant_id=restaurant_id).all()
    return jsonify(Mitems=[i.serialize for i in products])

# Diconnect current user
@app.route('/gdisconnect')
def gdisconnect():
        # If no users logged in:
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print result
	# If  user logged in:
    if result['status'] == '200':
        # Reset the user sesson
        del login_session['credentials']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        flash("Successfully disconnected.")
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response = make_response(redirect(url_for('showLogin')))
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        # If given token is invalid
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# Returns id of user
def getUserID(email):
    try:
        user = session.query(Customer).filter_by(email=email).one()
        return user.id
    except:
        return None



if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
