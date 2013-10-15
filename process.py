# encoding: utf-8

from google.appengine.api import search, taskqueue
from google.appengine.ext import ndb, deferred
#from google.appengine.ext.webapp.util import run_wsgi_app

from datetime import datetime
import logging

# zipからインポート
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'distlibs.zip'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'distlibs'))
from flask import Flask

import dbHandler

app = Flask(__name__)

class ToDocument:
	def CreateUserDocument(self, user):
		return search.Document(
			doc_id = str(user.uid),
			fields = [
				search.TextField(name="uid", value=str(user.uid)),
				search.TextField(name="name", value=user.name),
				search.TextField(name="about", value=user.about),
				],
			language="ja"
			)

	def CreateItemDocument(self, item):
		authors = ""
		for i, v in enumerate(item.authors):
			authors += v
			if i != len(item.authors)-1:
				authors += ","
		creators = ""
		for i, v in enumerate(item.creators):
			creators += v.name
			if i != len(item.creators)-1:
				creators +=","

		price = 0
		if item.price is not None:
			price = item.price
		pages = 0
		if item.pages is not None:
			pages = item.pages

		return search.Document(
			doc_id = item.asin,
			fields=[
				search.TextField(name="asin", value=item.asin),
				search.TextField(name="title", value=item.title),
				search.TextField(name="author", value=authors),
				search.TextField(name="creator", value=creators),
				search.TextField(name="publisher", value=item.publisher),
				search.TextField(name="binding", value=item.binding),
				search.NumberField(name="price", value=price),
				search.NumberField(name="pages", value=pages),
				search.TextField(name="publicationdate", value=item.publicationdate),
				search.DateField(name="date", value=datetime.now().date()),
				],
			language="ja"
			)

	def Item2Document(self, asin):
		index = search.Index(name="Items")
		item = dbHandler.Items.query().filter(dbHandler.Items.asin==asin).get()
		index.put(self.CreateItemDocument(item))
		return True

	def User2Document(self, uid):
		index = search.Index(name="Users")
		user = dbHandler.Users.query().filter(dbHandler.Users.uid==uid).get()
		index.put(self.CreateUserDocument(user))
		return True

	def deferred_User2Document(self, uid):
		try:
			deferred.defer(self.User2Document, uid, _name="User2Document_"+str(uid)+"_"+datetime.now().strftime("%Y%m%d%H"), _countdown=3600, _target="user2index")
		except (taskqueue.TaskAlreadyExistsError, taskqueue.TombstonedTaskError):
			pass
	def deferred_Item2Document(self, asin):
		try:
			deferred.defer(self.Item2Document, str(asin), _name="Item2Document_"+str(asin)+"_"+datetime.now().strftime("%Y%m%d%H%M"), _countdown=600, _target="item2index")
		except (taskqueue.TaskAlreadyExistsError, taskqueue.TombstonedTaskError):
			pass

@app.route('/cron/task/delete_user')
def DeleteUsers():
	Users = dbHandler.Users.query().order(db.Handler.Users.date).fetch(100)
	for user in Users:
		res = dbHandler.facebook.delete_permission(user.token)
		user.token = None
		user.put()
	return str(len(Users)) + "Users's all permissions of this app in Facebook are deleted."

@app.route('/cron/task/friendlist')
def friendlist_task():
	try:
		deferred.defer(FriendsUpdate, _target="friendlist-update-task")
		return "Add FriendsUpdate task"
	except (taskqueue.TaskAlreadyExistsError, taskqueue.TombstonedTaskError):
		pass
	return False

def FriendsUpdate():
	Users = dbHandler.Users.query().order(dbHandler.Users.date).fetch(100)
	for user in Users:
		friendlist_json = dbHandler.facebook.fql(user.token, "SELECT uid FROM user WHERE is_app_user=1 and uid IN (SELECT uid2 FROM friend WHERE uid1 = me())")
		if friendlist_json != "Error":
			tmplist_fb = []
			for fb_friend in friendlist_json['data']:
				tmplist_fb.append(fb_friend['uid'])
			user.friendlist = tmplist_fb
			user.put()
	#return str(len(Users)) + "Users's friendlist are updated."
	logging.info(str(len(Users)) + "Users's friendlist are updated.")
	return True

@app.route('/cron/task/items')
def items_task():
	try:
		deferred.defer(ItemsUpdate, _target="items-update-task")
		return "Add ItemsUpdate task"
	except (taskqueue.TaskAlreadyExistsError, taskqueue.TombstonedTaskError):
		pass
	return False

def ItemsUpdate():
	ToD = ToDocument()
	index = search.Index(name="Items")
	# 更新アイテムを検索
	# 更新が古い順に200件
	offset = 0
	limit = 10
	items = dbHandler.Items.query().order(dbHandler.Items.date).fetch(200)
	while offset < len(items):
		asinlist = []
		for item in items[offset:offset+limit]:
			asinlist.append(item.asin)
		if asinlist == []:
			break

		new_items = dbHandler.set_items(asinlist)
		for item in new_items:
			try:
				index.put(ToD.CreateItemDocument(item))
			except:
				pass
		offset += limit
	#return str(len(items)) + "Items is updated."
	logging.info(str(len(items)) + "Items is updated.")
	return True
#run_wsgi_app(app)
