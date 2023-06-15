#! /usr/bin/python
""" Creates database """

# Running this file will create an empty database

import sqlite3

# Create Database:

# open database
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# table includes columns for a username, email, and password
# all ids must be unique
cursor.execute('CREATE TABLE USERS (id TEXT, username TEXT, realname TEXT, zipcode TEXT, favimg TEXT, favurl TEXT, favtitle TEXT, UNIQUE(id))')

# close database
conn.commit()
conn.close()