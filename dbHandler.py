# encoding: utf-8

# とりあえず、インタフェース部分と入力部分だけでも分離

from google.appengine.ext import ndb
from google.appengine.api import memcache

from lxml import objectify

# zipからインポート
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'distlibs.zip'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'distlibs'))

from facebook import Facebook
# Facebook インスタンス化
facebook = Facebook(
	"382415631844147",
	"0f63043747e8c4f9510f5b5a359e2dd0",
	"http://yowatariapp.appspot.com/login"
	)

import bottlenose
amazon = bottlenose.Amazon(
	"AKIAIJOM2QR7W6G2EPXQ",
	"UYdlW609tfa+qgIatdZXESqaCt3Pw0q5ZiPzMOVY",
	"yyutao88-22",
	Region='JP'
	)

# DataStoreインタフェース
# ユーザ
class Users(ndb.Model):
	uid = ndb.IntegerProperty(required=True)
	name = ndb.StringProperty(indexed=False, required=True)
	location = ndb.StringProperty(indexed=False)
	about = ndb.TextProperty(indexed=False)
	fb_url = ndb.StringProperty(indexed=False)
	fb_friends = ndb.IntegerProperty(indexed=False)
	friendlist = ndb.IntegerProperty(repeated=True)
	handlist = ndb.StringProperty(repeated=True, indexed=True)
	token = ndb.StringProperty(required=True)
	date = ndb.DateTimeProperty(auto_now=True)

class Creators(ndb.Model):
	name = ndb.StringProperty()
	role = ndb.StringProperty()

# アイテム
class Items(ndb.Model):
	asin = ndb.StringProperty(required=True)
	title = ndb.StringProperty(indexed=False)
	authors = ndb.StringProperty(repeated=True, indexed=False)
	creators = ndb.StructuredProperty(Creators, repeated=True, indexed=False)
	similaritems_amazon = ndb.StringProperty(repeated=True)
	price = ndb.IntegerProperty(indexed=False)
	publisher = ndb.StringProperty(indexed=False)
	publicationdate = ndb.StringProperty(indexed=False)
	binding = ndb.StringProperty(indexed=False)
	pages = ndb.IntegerProperty(indexed=False)
	url = ndb.TextProperty(indexed=False)
	pic_url = ndb.StringProperty(indexed=False)
	date = ndb.DateTimeProperty(auto_now=True)

class DictObj (dict):
	__getattr__ = dict.__getitem__
	__setattr__ = dict.__setitem__
	__delattr__ = dict.__delitem__

def set_user(user, json):
	# まず更新
	try:
		user.location = unicode(json['data'][0]['current_location']['name'])
	except:
		user.location = None
	try:
		user.about = unicode(json['data'][0]['about_me'])
	except:
		user.about = None
	user.fb_url = unicode(json['data'][0]['profile_url'])
	user.fb_friends = int(json['data'][0]['friend_count'])

	# friendlist作成
	friendlist_json = facebook.fql(user.token, "SELECT uid FROM user WHERE is_app_user=1 and uid IN (SELECT uid2 FROM friend WHERE uid1 = me())")
	tmplist_fb = []
	for fb_friend in friendlist_json['data']:
		tmplist_fb.append(fb_friend['uid'])
	user.friendlist = tmplist_fb

	#set_user_memcache(user)
	user.put()

def set_user_memcache(user):
	#mem_value = unicode(user.uid)+u","+user.name
	#memcache.set(key=user.token, value=mem_value, time=7200)
	#memcache.set(key=str(user.uid)+"handlist", value=user.handlist)
	pass

def get_item(Item):
	# 存在チェック
	#item = Items.gql("WHERE  asin = :1", Item.ASIN.text).get()
	item = Items.query().filter(Items.asin==Item.ASIN.text).get()
	if item is None:
		item = Items(
			asin = unicode(Item.ASIN.text),
			)

	authors = []
	try:
		for author in Item.ItemAttributes.Author:
			authors.append(author.text)
		item.authors = authors
	except AttributeError:
		pass

	creators = []
	try:
		for creator in Item.ItemAttributes.Creator:
			creators.append(Creators(name=creator.text, role=creator.attrib['Role']))
		item.creators = creators
	except AttributeError:
		pass

	try:
		item.title = unicode(Item.ItemAttributes.Title.text)
	except AttributeError:
		item.title = None

	try:
		item.price = int(Item.ItemAttributes.ListPrice.Amount.text)
	except AttributeError:
		item.price = None

	try:
		item.publisher = unicode(Item.ItemAttributes.Publisher.text)
	except AttributeError:
		item.publisher = None

	try:
		item.publicationdate = unicode(Item.ItemAttributes.PublicationDate.text)
	except AttributeError:
		item.publicationdate = None

	try:
		item.binding = unicode(Item.ItemAttributes.Binding.text)
	except AttributeError:
		item.binding = None

	try:
		item.pages = int(Item.ItemAttributes.NumberOfPages.text)
	except AttributeError:
		item.pages = None

	try:
		item.url = unicode(Item.DetailPageURL.text)
	except AttributeError:
		item.url = None

	"""
	try:
		item.pic = images.resize(urllib2.urlopen(unicode(Item.LargeImage.URL.text)).read(),  170, 250)
	except (AttributeError, urllib2.URLError):
		item.pic = images.resize(urllib2.urlopen("http://images.amazon.com/images/G/09/en_JP/nav2/dp/no-image-no-ciu.gif").read(), 190, 190)
	"""

	try:
		item.pic_url = Item.LargeImage.URL.text
	except AttributeError:
		item.pic_url = None

	similaritems_amazon = []
	try:
		for SimilarProduct in Item.SimilarProducts.SimilarProduct:
			similaritems_amazon.append(SimilarProduct.ASIN.text)
		item.similaritems_amazon = similaritems_amazon
	except AttributeError:
		pass

	return item

def set_item(asin):
	for i in range(3):
		try:
			xml = amazon.ItemLookup(ItemId=asin, ResponseGroup="Images,ItemAttributes,Similarities", IdType="ASIN")
			root = objectify.fromstring(xml)
			break
		except:
			pass

	if root.Items.Item.ItemAttributes.ProductGroup.text != "Book":
		return None

	item = get_item(root.Items.Item)

	item.put()
	return item

def set_items(asinlist):
	items = []
	# フィルタリング：書籍のみ残す
	try:
		xml = amazon.ItemLookup(ItemId=",".join(asinlist), ResponseGroup="Images,ItemAttributes,Similarities", IdType="ASIN")
		root = objectify.fromstring(xml)
	except:
		return items

	for Item in root.Items.Item:
		if Item.ItemAttributes.ProductGroup.text == "Book":
			item = get_item(Item)
			items.append(item)
		else:
			pass
	ndb.put_multi(items)
	return items
