from flask import Flask, render_template, session, request, redirect, url_for, render_template, flash
from google.cloud.sql.connector import Connector
from werkzeug.exceptions import HTTPException
import os
from classes.user import User
import pymysql
import uuid
import sqlalchemy
import random


# Flask Config______________________________________________________________
DEBUG = True
app = Flask(__name__)
app.config.from_object(__name__)
app.config['SECRET_KEY'] = "ZDHX218H9H2KSOS36"
app.config['SESSION_COOKIE_SECURE'] = True #secure session cookies
app.config['MAX_CONTENT_LENGTH'] = 10 * 1000 * 1000# RESOURCE LIMITING

# Google Cloud SQL Connection
os.environ["GOOGLE_APPLICATION_CREDENTIALS"]="static/creds.json"
connector = Connector()

def getconn() -> pymysql.connections.Connection:
    conn: pymysql.connections.Connection = connector.connect(
        'long-sum-361008:asia-southeast1-c:environ-game',
        "pymysql",
        user="root",
        password = '"ph/y0,dHT&9t5?s',
        db="questions"
    )
    return conn
  
pool = sqlalchemy.create_engine(
    "mysql+pymysql://",
    creator=getconn,
)

#to connect to user database
def userconn() -> pymysql.connections.Connection:
    conn: pymysql.connections.Connection = connector.connect(
        'long-sum-361008:asia-southeast1-c:environ-game',
        "pymysql",
        user="root",
        password = '"ph/y0,dHT&9t5?s',
        db="users"
    )
    return conn
  
userpool = sqlalchemy.create_engine(
    "mysql+pymysql://",
    creator=userconn,
)
# PAGES ------------------------------------------------------------------------
@app.errorhandler(HTTPException)
def handle_exception(e):
    name = e.name
    code = e.code
    description = e.description
    return render_template('genericerror.html', name=name, code=code, description=description)

@app.route('/')
def home():
    for key in list(session.keys()):
      if key != "userID" and key != "_flashes":
        session.pop(key)
    return render_template('home.html')


@app.route('/results')
def results():
  if 'name' in session:
  #updating the previous results
    User.saveGame(session['ageOfDeath'], session['money'], session['lifetimeCO2Score'], session['gameDifficulty'])
    with pool.connect() as db_conn:
      completedQns = session['completedQns']
      completedQns_format = '(' + ', '.join(completedQns) + ')'
      completedQns_list = db_conn.execute(f"SELECT * from Questions WHERE {age} BETWEEN ageRange_Min AND ageRange_Max AND id IN {completedQns_format} ORDER BY RAND()").fetchall()  
    return render_template('results.html', completedQns_list=completedQns_list)
  else:
    return redirect(url_for('home'))


@app.route('/pastGames')
def pastGames():
  pastGamesDict = User.retrieveGamesDict()
  return render_template('pastGames.html', pastGamesDict=pastGamesDict)
    
  
# API ------------------------------------------------------------------------
@app.route('/startGame', methods = ['POST'])
def startGame():
    session['gameID'] = uuid.uuid4()
    session['age'] = 1
    session['ageOfDeath'] = random.randint(75,90)
    session['name'] = request.form['plrName']
    session['money'] = 0
    session['currentQnId'] = 0
    session['jobYearlySalary'] = 0
    session['lifetimeCO2Score'] = 0
    session['gameDifficulty'] = request.form['radioDifficulty']
    session['completedQns'] = []
    return redirect(url_for('showQuestion'))


@app.route('/showQuestion')
def showQuestion():
    with pool.connect() as db_conn:
      age = session["age"]
      # completedQn ids need to be string
      completedQns = session['completedQns'] # Save array to session, question IDs added here to prevent repeat
      if len(completedQns) <= 0:
          questionRow = db_conn.execute(f"SELECT * from Questions WHERE {age} BETWEEN ageRange_Min AND ageRange_Max ORDER BY RAND() LIMIT 1").fetchone()
      else:
          completedQns_format = '(' + ', '.join(completedQns) + ')'
          questionRow = db_conn.execute(f"SELECT * from Questions WHERE {age} BETWEEN ageRange_Min AND ageRange_Max AND id NOT IN {completedQns_format} ORDER BY RAND() LIMIT 1").fetchone()
      session['currentQnId'] = questionRow.id
  
    return render_template('question.html', session=session, questionRow = questionRow)


@app.route('/ansQuestion', methods = ['GET'])
def ansQuestion():
    # Determining age progression
    gameDifficulty = session['gameDifficulty']
    if gameDifficulty == 'Fast':
        ageProgression = 15
    elif gameDifficulty == 'Normal':
        ageProgression = 10
    else: # Default will be slow
        ageProgression = 5
      
    session['money'] += ageProgression * session['jobYearlySalary']
    session['age'] += ageProgression
  
    # Assign Co2
    response = int(request.args.get("response"))
    with pool.connect() as db_conn:
      currentQnId = session["currentQnId"]
      questionRow = db_conn.execute(f"SELECT * from Questions WHERE id = {currentQnId};").fetchone()
      if questionRow:
        session['lifetimeCO2Score'] += float(questionRow[f"response{response}_CO2Increment"])

    # Updating of completed questions list
    completedQns = session['completedQns']
    completedQns.append(str(currentQnId))
    session['completedQns'] = completedQns

    # END GAME
    if session['age'] >= session['ageOfDeath']:
      lifetimeCO2 = round(session['lifetimeCO2Score'],3)
      session['lifetimeCO2Score'] = lifetimeCO2
      if 'userID' in session:
      #updating the previous results
        User.saveGame(session['ageOfDeath'], session['money'], session['lifetimeCO2Score'], session['gameDifficulty'])
      with pool.connect() as db_conn:
        completedQns_format = '(' + ', '.join(completedQns) + ')'
        completedQns_list = db_conn.execute(f"SELECT * from Questions WHERE id IN {completedQns_format} ORDER BY RAND()").fetchall()  
      return render_template('results.html', session=session, completedQns_list=completedQns_list)
    else:
      return redirect(url_for('showQuestion'))


# USERS -----------------------------------------------------------------------
@app.route('/register', methods = ['POST'])
def register():
    email = request.form["email"]
    password = request.form["password"]

    if email and password:
      newUser = User(email, password)
      session['userID'] = newUser.get_userID()
      return redirect(url_for('home'))

@app.route('/login', methods = ['POST'])
def login():
    email = request.form["email"]
    password = request.form["password"]

    if email and password:
      user = User.attempt_Login(email, password)
      if user:
        session['userID'] = user.id
        flash('Logged in!', 'Success')
      else:
        flash('Invalid email or password!', 'Error')
      return redirect(url_for('home'))


@app.route('/logOut')
def logOut():
  if User.logOut():
    return redirect(url_for('home'))


# JOBS -------------------------------------------------------------------------
@app.route('/setJobYearlySalary', methods = ['GET'])
def setJobYearlySalary():
    salary = int(request.args.get("salary"))
    session['jobYearlySalary'] = salary
    return redirect(url_for('showQuestion'))
















# FLASK RUN --------------------------------------------------------------------
app.run(host='0.0.0.0', port=81)