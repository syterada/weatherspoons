"""Flask app for weatherspoons.com"""
from flask import Flask, render_template, url_for, redirect, session, request
from authlib.integrations.flask_client import OAuth
import requests
import secrets
import json
import sqlite3
import zipcodes
import time
import sys

app = Flask(__name__)

app.secret_key = secrets.token_bytes(32)

oauth = OAuth(app)

Geoapify_Key = ""
spoonacular_api_key = ""
app.config['GITHUB_CLIENT_ID'] = ""
app.config['GITHUB_CLIENT_SECRET'] = ""

github = oauth.register (
  name = 'github',
    client_id = app.config["GITHUB_CLIENT_ID"],
    client_secret = app.config["GITHUB_CLIENT_SECRET"],
    access_token_url = 'https://github.com/login/oauth/access_token',
    access_token_params = None,
    authorize_url = 'https://github.com/login/oauth/authorize',
    authorize_params = None,
    api_base_url = 'https://api.github.com/',
    client_kwargs = {'scope': 'user:email'},
)

#API call functions

#get latitutde and longitude from GeoApify API using a zipcode
def get_coords_from_zip(zip):
	"""gets the coordinates from the zip code that the user input adn returns latitude, longitude, and which city the user is in """
	geocodeapi_url = "https://api.geoapify.com/v1/geocode/search?text=" + str(zip) + "&type=postcode&filter=countrycode:us,ca&format=json&apiKey=" + Geoapify_Key
	response = json.loads(requests.request("GET", geocodeapi_url).text)
	latraw = response["results"][0]["lat"]
	lat = format(latraw, ".4f")
	lonraw = response["results"][0]["lon"]
	lon = format(lonraw, ".4f")
	city = response["results"][0]["city"]
	return lat,lon,city

#passes a latitude and longitude to return current weather condition from NWS API
def get_gridpoint_forecast(lat,lon):
	"""gets the forecast for the user's location"""
	points_url = "https://api.weather.gov/points/" + str(lat) + "," + str(lon)
	gridpoint_response = json.loads(requests.request("GET", points_url).text)
	forecast_url = gridpoint_response["properties"]["forecast"]
	forecast_response = json.loads(requests.request("GET", forecast_url).text)
	shortForecast = forecast_response["properties"]["periods"][0]["shortForecast"]
	return shortForecast

#turns short_forecast from NWS API into a search query for use in Spoonacular search
def vibecheck (forecast):
	"""based on the forecast, we choose a keyword to search for a recipe"""
	if "Clear" in forecast:
		vibe = "noodles"
	elif "Cloudy" in forecast:
		vibe = "meatballs"
	elif "Rain" in forecast or "Showers and Breezy" in forecast or "Snow Showers" in forecast:
		vibe = "soup"
	elif "Partly Sunny" in forecast:
		vibe = "wrap"
	elif "Sunny " in forecast:
		vibe = "icecream"
	elif "Sunny and Very Windy" in forecast:
		vibe = "kebab"
	elif "Partly Cloudy" in forecast:
		vibe = "pizza"
	elif "Mostly Cloudy" in forecast:
		vibe = "gnocchi"
	elif "Sunny and Breezy" in forecast:
		vibe = "smoothie"
	elif "Mostly Clear and Windy" in forecast:
		vibe = "salad"
	elif "Scattered Showers and Breezy" in forecast:
		vibe = "coucous"
	elif "Showers and Patchy Fog" in forecast or "Chance Showers and Patchy Fog then Showers and Patchy Fog" in forecast:
		vibe = "stew"
	elif "Areas Freezing Fog " in forecast:
		vibe = "risotto"
	elif "Patchy Freezing Fog" in forecast:
		vibe = "stirfry"
	elif "Patchy Freezing Fog then Partly Sunny" in forecast:
		vibe = "cabbage"
	elif "Showers Likely" in forecast:
		vibe = "fish"
	elif "Slight Chance Snow Showers then Mostly Sunny" in forecast:
		vibe = "pasta"
	elif "Chance Rain And Snow Showers" in forecast:
		vibe = "curry"
	elif "Partly Cloudy then Chance Snow Showers" in forecast:
		vibe = "casserole"
	elif "Slight Chance Snow" in forecast:
		vibe = "chowder"
	elif "Slight Chance T-storms" in forecast:
		vibe = "pretzel"
	else:
		vibe = "sandwich"

#get recipe from Spoonacular API
def get_recipe (vibe):
	"""makes a query to spoonacular to get a recipe for the user"""
	spoonacular_url = "https://api.spoonacular.com/recipes/complexSearch?query="+str(vibe)+"&number=1&limitLicense=true&apiKey="+str(spoonacular_api_key)
	random_recipe_url = "https://api.spoonacular.com/recipes/random?number=1&apiKey="+str(spoonacular_api_key)
	response = json.loads(requests.request("GET", spoonacular_url).text)
	if response["totalResults"] < 1:
		response = json.loads(requests.request("GET", random_recipe_url).text)
		title = response["recipes"][0]["title"]
		image = response["recipes"][0]["image"]
		id = response["recipes"][0]["id"]
		sourceUrl = response["recipes"][0]["spoonacularSourceUrl"]
	else:
		title = response["results"][0]["title"]
		image = response["results"][0]["image"]
		id = response["results"][0]["id"]
		recipe_url = "https://api.spoonacular.com/recipes/"+str(id)+"/information"
		response = json.loads(requests.request("GET", recipe_url).text)
		sourceUrl = response["spoonacularSourceUrl"]
	session["sourceUrl"] = sourceUrl
	session["image"] = image
	session["title"] = title
	return title,image,id,sourceUrl

# Sign-in
@app.route('/')
def index():
  return render_template('index.html')
#Sign off
@app.route('/index')
def signoff():
  return render_template('index.html')

# Get zipcode from new users
@app.route('/newuser')
def newuser():
  failure = False
  return render_template('newuser.html', failure = failure)

# Home page from newuser form
@app.route('/home/', methods = ['POST', 'GET'])
def home():
	if request.method == 'GET':
		zipcode = session["zipcode"]
		lat,lon,city = get_coords_from_zip(zipcode)
		forecast = get_gridpoint_forecast(lat,lon)
		vibe = vibecheck(forecast)
		title,image,recipe_id,sourceUrl = get_recipe(vibe)
		session["sourceUrl"] = sourceUrl
		session["image"] = image
		session["title"] = title
		return render_template('home.html',lat=lat,lon=lon,forecast=forecast,title=title,image=image,recipe_id=recipe_id,sourceUrl=sourceUrl,city=city,zipcode=zipcode)
	if request.method == 'POST':

		# If the zipcode is real then render the home page normally
		zipcode = request.form.get("zipcode")
		if zipcodes.is_real(zipcode) == True:
			id = session["id"]

			# add zipcode to user profile in database
			conn = sqlite3.connect("database.db")
			cursor = conn.cursor()
			cursor.execute("UPDATE USERS SET zipcode = :zipcode WHERE id = :id", {'zipcode': zipcode, 'id': id})
			conn.commit()
			conn.close()

			# save zipcode during session for easy access
			session["zipcode"] = zipcode
		lat,lon,city = get_coords_from_zip(zipcode)
		forecast = get_gridpoint_forecast(lat,lon)
		vibe = vibecheck(forecast)
		title,image,recipe_id,sourceUrl = get_recipe(vibe)
		session["sourceUrl"] = sourceUrl
		session["image"] = image
		session["title"] = title
		return render_template("home.html",lat=lat,lon=lon,forecast=forecast,title=title,image=image,recipe_id=recipe_id,sourceUrl=sourceUrl,city=city,zipcode=zipcode)

	# Otherwise return to the newuser page to try again
	else:
		failure = True
		return render_template('newuser.html', failure = failure)

# Get zipcode from new users
@app.route('/profile')
def profile():
  username = session["username"]
  realname = session["realname"]
  zipcode = session["zipcode"]
  avatar = session["avatar"]
  return render_template('profile.html', username = username, realname = realname, zipcode = zipcode, avatar = avatar)

# Get zipcode from new users
@app.route('/favorites', methods = ['POST', 'GET'])
def favorites():
	id = session["id"]
	sourceUrl = session["sourceUrl"]
	image = session["image"]
	title = session["title"]

	if request.method == 'POST':
		conn = sqlite3.connect("database.db")
		cursor = conn.cursor()

		cursor.execute("UPDATE USERS SET favurl = :sourceUrl WHERE id = :id", {'sourceUrl': sourceUrl, 'id': id})
		cursor.execute("UPDATE USERS SET favimg = :image WHERE id = :id", {'image': image, 'id': id})
		cursor.execute("UPDATE USERS SET favtitle = :title WHERE id = :id", {'title': title, 'id': id})

		conn.commit()
		conn.close()
	
	conn = sqlite3.connect("database.db")
	cursor = conn.cursor()

	favimg = cursor.execute("SELECT favimg FROM USERS WHERE id = (:id)", {'id': id})
	favimg = cursor.fetchone()
	favimg = favimg[0]

	favurl = cursor.execute("SELECT favurl FROM USERS WHERE id = (:id)", {'id': id})
	favurl = cursor.fetchone()
	favurl = favurl[0]

	favtitle = cursor.execute("SELECT favtitle FROM USERS WHERE id = (:id)", {'id': id})
	favtitle = cursor.fetchone()
	favtitle = favtitle[0]

	conn.commit()
	conn.close()

	if favimg == None:
		b = False
	else:
		b = True

	return render_template('favorites.html', bool = b, favurl = favurl, favimg = favimg, favtitle = favtitle)

# Github login
@app.route('/login/github')
def github_login():
    github = oauth.create_client('github')
    redirect_url = url_for('github_authorize', _external=True)
    return github.authorize_redirect(redirect_url)

# Github authorization
@app.route('/login/github/authorize')
def github_authorize():
	github = oauth.create_client('github')
	token = github.authorize_access_token()

	all_user_info = github.get('user').json()
	username = all_user_info['login']
	id = all_user_info['id']
	realname = all_user_info['name']
	avatar = all_user_info['avatar_url']

    # save user info during session (easier than using the database every time)
	session["username"] = username
	session["id"] = id
	session["realname"] = realname
	session["avatar"] = avatar

	conn = sqlite3.connect("database.db")
	cursor = conn.cursor()

    # add user's github id and username into the database 
	cursor.execute("INSERT OR IGNORE INTO USERS (id) VALUES (:id)", {'id': id})
	cursor.execute("UPDATE USERS SET username = :username WHERE id = :id", {'username': username, 'id': id})
    # if they have their real name on their github account, add that to the database as well
	if (realname != "None"):
		cursor.execute("UPDATE USERS SET realname = :realname WHERE id = :id", {'realname': realname, 'id': id})

    # check if the user's id has a zipcode attached
	zipcode = cursor.execute("SELECT zipcode FROM USERS WHERE id = (:id)", {'id': id})
	zipcode = cursor.fetchone()
	zipcode = zipcode[0]

	conn.commit()
	conn.close()

    # if this is a new account without a zipcode, then render a "newuser" html page which will ask them...
    # ...to input their zipcode before bringing them to the home page
	if zipcode == None:
		return render_template('newuser.html', username = username, id = id, realname = realname, zipcode = zipcode)

    # otherwise just go to the home page and save the zipcode during session for easy access
	session["zipcode"] = zipcode
	lat,lon,city = get_coords_from_zip(zipcode)
	forecast = get_gridpoint_forecast(lat,lon)
	vibe = vibecheck(forecast)
	title,image,recipe_id,sourceUrl = get_recipe(vibe)
	return render_template('home.html', username = username, id = id, realname = realname, lat=lat,lon=lon,forecast=forecast,title=title,image=image,recipe_id=recipe_id,sourceUrl=sourceUrl,city=city,zipcode=zipcode)

app.run(host='localhost', port=5000)
