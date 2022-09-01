from flask import Flask, render_template, session, request, redirect, url_for, render_template, flash
from passlib.hash import sha256_crypt # password hashing
from google.cloud.sql.connector import Connector
import os
import pymysql
import sqlalchemy
from sqlalchemy.sql import text
import uuid
import json

# Google Cloud SQL Connection
os.environ["GOOGLE_APPLICATION_CREDENTIALS"]="static/creds.json"
connector = Connector()

def getconn() -> pymysql.connections.Connection:
    conn: pymysql.connections.Connection = connector.connect(
        "long-sum-361008:asia-southeast1-c:environ-game",
        "pymysql",
        user="root",
        password='"ph/y0,dHT&9t5?s',
        db="users"
    )
    return conn
  
pool = sqlalchemy.create_engine(
    "mysql+pymysql://",
    creator=getconn,
)

class User:
    """ This superclass is used for all users."""
    def __init__(self, email, password):
        self.__id = str(uuid.uuid4())
        self.__email = email.lower()
        self.__passwordHash = sha256_crypt.hash(password)

        with pool.connect() as db_conn:
          db_conn.execute("INSERT INTO Users VALUES ('%s', '%s', '%s', '{}')" % (self.__id, self.__email, self.__passwordHash))

    # Accessor Methods
    def get_email(self):
        return self.__email
      
    def get_userID(self):
        return self.__id   


    def attempt_Login(email, password):
      try:
        with pool.connect() as db_conn:
          a = text("SELECT * FROM Users WHERE email = :email")
          result = db_conn.execute(a, {'email': email}).first()
          if result and sha256_crypt.verify(password, result.passwordHash):
            return result
          else:
            return False
      except Exception as e:
        print(e)

    def logOut():
      if 'userID' in session:
        session.pop('userID')
        return True

    def saveGame(ageOfDeath, money, co2):
      with pool.connect() as db_conn:
        userID = session['userID']
        resultsJSON = db_conn.execute(f"SELECT pastGameIDs FROM Users WHERE id = '{userID}'").fetchone()[0]
        resultsDict = json.loads(resultsJSON)
        gameID = str(session['gameID'])
        resultsDict[gameID] = {}
        resultsDict[gameID]["ageOfDeath"] = ageOfDeath
        resultsDict[gameID]["money"] = money
        resultsDict[gameID]["lifetimeCO2Score"] = co2
        db_conn.execute(f"UPDATE Users SET PastGameIDs = '{json.dumps(resultsDict)}' WHERE id = '{userID}'")

    def retrieveGamesDict():
      with pool.connect() as db_conn:
        userID = session['userID']
        resultsJSON = db_conn.execute(f"SELECT pastGameIDs FROM Users WHERE id = '{userID}'").fetchone()[0]
        
        if resultsJSON:
         return json.loads(resultsJSON)