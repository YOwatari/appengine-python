# encoding: utf-8

from __future__ import with_statement
from google.appengine.api import images, files, search, memcache
from google.appengine.ext import ndb, blobstore
#from google.appengine.ext.webapp.util import run_wsgi_app

# zipからインポート
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'distlibs.zip'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'distlibs'))
from flask import Flask, render_template, request, Response, session, redirect, url_for
from flask.ext.bootstrap import Bootstrap

import dbHandler
from pagination import Pagination
from process import ToDocument

app = Flask(__name__)
# ↓↓↓ランダム英数字文字列生成↓↓↓
# import string, random
# ''.join(random.choice(string.digits+string.letters) for i in xrange(18))
# ↑↑↑ランダム英数字文字列生成↑↑↑

# securecookieにセッションID保存してる
app.secret_key = 'JxRtg1e3npLMypw3JC'
Bootstrap(app)
app.config['BOOTSTRAP_USE_MINIFIED'] = True
app.config['BOOTSTRAP_USE_CDN'] = True
app.config['BOOTSTRAP_FONTAWESOME'] = False
app.config['BOOTSTRAP_CDN_BASEURL'] = {'bootstrap': '//netdna.bootstrapcdn.com/twitter-bootstrap/2.2.2/', 'fontawesome': '//netdna.bootstrapcdn.com/font-awesome/'}
app.config['BOOTSTRAP_GOOGLE_ANALYTICS_ACCOUNT'] = "UA-37662940-1"

facebook = dbHandler.facebook
Users = dbHandler.Users
Items = dbHandler.Items

ToD = ToDocument()

def logined_check():
	access_token = session.get('access_token')
	if access_token is None:
		return None

	# アクセストークンでDataStoreを検索
	current_user = Users.query().filter(Users.token==access_token).get()
	# なかったら、loginを促す
	if current_user is None:
		return None
	return current_user

@app.route('/about')
def about():
	current_user = logined_check()
	if current_user is None:
		return render_template('login.html',
				       title = u"市川研 アプリ班")

	return render_template(
				'about.html',
				title = u"市川研 アプリ班",
				current_user = current_user
				)

# トップページ
@app.route('/')
def index():
	current_user = logined_check()
	if current_user is None:
		return render_template('login.html',
				       title = u"市川研 アプリ班")

	return render_template(
				'index.html',
				title = u"市川研 アプリ班",
				current_user = current_user
				)

# ログイン
# 踏むとログイン処理
# ユーザ情報をbigtableに保存
# TODO: クライアント側にアクセストークンを渡さない方法
@app.route('/login')
def login():
	code = request.args.get('code')
	access_token = session.get('access_token')

	if code is None:
		if access_token is not None:
			user = Users.query().filter(Users.token==access_token).get()
			if user is not None:
				return redirect('/')
		return redirect(facebook.authorize())

	# アクセストークン更新
	session['access_token'] = facebook.access_token(code,  facebook.access_token(code))
	access_token = session['access_token']

	# localeチェック
	locale_json = facebook.fql(access_token, "SELECT locale FROM user WHERE uid = me()")
	locale = locale_json['data'][0]['locale']
	if str(locale) != "ja_JP":
		locale = "en_US"

	user_json = facebook.fql(access_token, "SELECT uid, name, current_location, about_me, profile_url, friend_count FROM user WHERE uid = me()" , locale)

	# アクセストークンで検索
	user = Users.query().filter(Users.token==access_token).get()
	if user is None:
		# uidで再度検索
		user = Users.query().filter(Users.uid == int(user_json['data'][0]['uid'])).get()
		if user is not None:
			# DataStoreのアクセストークンが期限切れなので更新
			user.token = unicode(access_token)
			user.name = unicode(user_json['data'][0]['name'])
		else:
			# DataStoreに無いユーザなので、新規登録
			user = Users(
				uid = int(user_json['data'][0]['uid']),
				name = unicode(user_json['data'][0]['name']),
				token = unicode(access_token)
				)
	else:
		# DataStore更新
		user.name = unicode(user_json['data'][0]['name'])
	dbHandler.set_user(user, user_json)

	return redirect('/')

# ログアウト
# 踏むとログアウト処理
# とりあえず、セッション破棄してるだけ
# TODO: Facebook側ログアウト処理
@app.route('/logout')
def logout():
	access_token = session.get('access_token')
	session.pop('access_token', None)
	return redirect('/')

# ユーザページ
# Facebookのuidで識別
# 所有
def url_for_other_page(page):
	args = request.view_args.copy()
	args['p'] = page
	if request.endpoint == "search_disp":
		args['q'] = request.args['q']
	return url_for(request.endpoint, **args)
app.jinja_env.globals['url_for_other_page'] = url_for_other_page

@app.route('/user/<int:arg_uid>/hands', methods=['GET'], strict_slashes=False)
def user_handlist(arg_uid):
	current_user = logined_check()
	if current_user is None:
		return render_template('login.html',
				       title = u"市川研 アプリ班")

	page = request.args.get('p')
	if page:
		if page.isdecimal() is False:
			return redirect('/user/'+str(arg_uid)+'/hands')
		page = int(page)
	else:
		page = 1

	# ユーザー情報取得
	view_user = Users.query().filter(Users.uid==int(arg_uid)).get()
	if view_user is None:
		return redirect('/')

	# アイテム情報取得
	itemlist = []
	limit = 10
	offset = (int(page)-1)*limit
	itemlist = Items.query().filter(Items.asin.IN([None]+view_user.handlist[offset:offset+limit])).fetch(limit)
	"""
	tmplist = view_user.handlist[offset:offset+limit]
	for item in itemlist:
		index = view_user.handlist[offset:offset+limit].index(item.asin)
		tmplist[index] = item
	for asin in view_user.handlist[offset:offset+limit]:
		if asin in tmplist:
			item = dbHandler.DictObj()
			item.asin = asin
			item.title = "Not Found in DataStore. Click here to create data in DataStore."
			item.authors = None
			item.pic_url = None
			tmplist[tmplist.index(asin)] = item
	itemlist = tmplist
	"""
	pagination = Pagination(page, limit, len(view_user.handlist))

	if view_user.uid == current_user.uid:
		title = u"あなたの持ち物"
	else:
		title = view_user.name + u"さんの持ち物"

	return render_template(
		'userhand.html',
		title = title,
		current_user = current_user,
		itemlist = itemlist,
		view_user = view_user,
		pagination = pagination
		)

# Friend
@app.route('/user/<arg_uid>/friends', methods=['GET'], strict_slashes=False)
def user_friendlist(arg_uid):
	current_user = logined_check()
	if current_user is None:
		return render_template('login.html',
				       title = u"市川研 アプリ班")

	page = request.args.get('p')
	if page:
		if page.isdecimal() is False:
			return redirect('/user/'+str(arg_uid)+'/friends')
		page = int(page)
	else:
		page = 1

	# ユーザー情報取得
	view_user = Users.query().filter(Users.uid==int(arg_uid)).get()
	if view_user is None:
		return redirect('/')


	friendlist = []
	limit = 5
	offset = (int(page)-1)*limit
	friendlist = Users.query().filter(Users.uid.IN([None]+view_user.friendlist[offset:offset+limit])).fetch(limit)
	tmplist = view_user.friendlist[offset:offset+limit]
	for friend in friendlist:
		index = view_user.friendlist[offset:offset+limit].index(friend.uid)
		tmplist[index] = friend
	for uid in view_user.friendlist[offset:offset+limit]:
		if uid in tmplist:
			user = dbHandler.DictObj()
			user.uid = uid
			user.name = "Not Found in DataStore."
			user.about = None
			user.location = None
			user.handlist = []
			user.friendlist = []
			user.fb_friends = 0
			user.fb_url = "http://www.facebook.com/"+str(uid)
			tmplist[tmplist.index(uid)] = user
	friendlist = tmplist

	pagination = Pagination(page, limit, len(view_user.friendlist))

	if view_user.uid == current_user.uid:
		title = u"あなたの友達"
	else:
		title = view_user.name + u"さんの友達"

	return render_template(
		'userfriend.html',
		title = title,
		current_user = current_user,
		friendlist = friendlist,
		view_user = view_user,
		pagination = pagination
		)

# アイテムページ
# Amazonのasinで識別
@app.route('/item/<arg_asin>')
def item(arg_asin):
	current_user = logined_check()
	if current_user is None:
		return render_template('login.html',
				       title = u"市川研 アプリ班")

	item = Items.query().filter(Items.asin==arg_asin).get()
	if item is None:
		item = dbHandler.set_item(arg_asin)
		if item is None:
			return "Error: Not Book."
		ToD.deferred_Item2Document(item.asin)

	# 関連書籍が空の時はここで終わり
	if item.similaritems_amazon == []:
		return render_template(
			'item.html',
			title = item.title,
			item = item,
			current_user = current_user,
			similaritems = None
			)

	similaritems = Items.query().filter(Items.asin.IN(item.similaritems_amazon)).fetch(len(item.similaritems_amazon))
	tmplist = [None]*len(item.similaritems_amazon)
	# 順序を正規化
	for similaritem in similaritems:
		index = item.similaritems_amazon.index(similaritem.asin)
		tmplist[index] = similaritem
	similaritems = tmplist

	# DataStoreに無いitemがあった場合
	if None in similaritems:
		# 複数item情報取得
		tmplist = item.similaritems_amazon
		for index, similaritem in enumerate(similaritems):
			if similaritem is not None:
				tmplist[index] = ""
		new_similaritems = dbHandler.set_items(tmplist)
		# 新しいitemをセット
		if new_similaritems != []:
			for similaritem in new_similaritems:
				ToD.deferred_Item2Document(similaritem.asin)
			for index, asin in enumerate(tmplist):
				if asin != ""  and new_similaritems != []:
					similaritems[index] = new_similaritems[0]
					new_similaritems.pop(0)
		# ゴミ駆除
		while None in similaritems:
			similaritems.remove(None)

		# item.similaritems_amazon更新
		tmplist = []
		for similaritem in similaritems:
			tmplist.append(similaritem.asin)
		item.similaritems_amazon = tmplist
		item.put()

	return render_template(
		'item.html',
		title = item.title,
		item = item,
		current_user = current_user,
		similaritems = similaritems
		)

# 所有情報更新
# 重複だと破棄
# 新規だと所有
@app.route('/item/<arg_asin>/hand')
def hand(arg_asin):
	current_user = logined_check()
	if current_user is None:
		return render_template('login.html',
				       title = u"市川研 アプリ班")

	if arg_asin in current_user.handlist:
		current_user.handlist.remove(arg_asin)
	else:
		current_user.handlist.insert(0, arg_asin)
	current_user.put()

	return redirect('/user/' + str(current_user.uid) + "/hands")

# アイテム画像表示
# DataStoreに保存した画像バイナリから生成
# key=asin
@app.route('/amazon')
def amazon_disp():
	# StringIOかcStringIO使う
	# GAE上じゃC使うやつは無理っぽい？
	import urllib2
	try:
		from cStringIO import StringIO
	except:
		from StringIO import StringIO

	key = str(request.args.get('key'))
	pic = memcache.get(key)
	if pic is None:
		#item = Items.query().filter(Items.asin==key).get()
		blob_info = blobstore.BlobInfo.all().filter("filename =", key+".png").get()
		try:
			blob_reader = blob_info.open()
			#blob_reader = blobstore.BlobReader(item.pic)
			pic = blob_reader.read()
		except:
			item = Items.query().filter(Items.asin==key).get()
			if item.pic_url is not None:
				try:
					data = urllib2.urlopen(unicode(item.pic_url)).read()
					pic = images.resize(data, 170, 250, output_encoding=images.PNG)
				except urllib2.URLError:
					pic = None
			else:
				#data = urllib2.urlopen(u"http://images.amazon.com/images/G/09/en_JP/nav2/dp/no-image-no-ciu.gif").read()
				#image = images.Image(image_data=data)
				#image.crop(1/float(image.width), 1/float(image.height), (image.width-1)/float(image.width), (image.height-1)/float(image.height))
				#pic = image.execute_transforms(output_encoding=images.PNG)
				pic = open("./static/no_image.png", 'r').read()
			if pic is not None:
				blob_io = files.blobstore.create(mime_type='image/png', _blobinfo_uploaded_filename=key+".png")
				with files.open(blob_io, 'a') as f:
					f.write(pic)
				files.finalize(blob_io)
				#item.pic = files.blobstore.get_blob_key(blob_io)
				#item.put()
	memcache.set(key=key, value=pic)
	return Response(response=StringIO(pic), content_type="image/png")

# 検索ページ
@app.route('/search' )
def search_disp():
	import urllib, unicodedata

	current_user = logined_check()
	if current_user is None:
		return render_template('login.html',
				       title = u"市川研 アプリ班")

	page = request.args.get('p')
	if page:
		if page.isdecimal() is False:
			return redirect('/')
		page = int(page)
	else:
		page = 1

	q_key = request.args.get('q')
	if q_key is None:
		return redirect('/')
	search_query = unicodedata.normalize('NFKC', request.args.get('q'))

	Limit = 10
	index = search.Index(name="Items")
	options = search.QueryOptions(
		limit=Limit,
		offset=(page-1)*Limit,
		returned_fields=['asin', 'title', 'author'])

	query = search.Query(
		query_string = search_query,
		options = options
		)

	results = index.search(query)

	tmplist = []
	for scored_document in results:
		tmp_dict = {}
		for field in scored_document.fields:
			tmp_dict.update({field.name:field.value})
		tmplist.append(tmp_dict)

	if "iPhone"  in request.headers.get('User-Agent')\
	or "Android"  in request.headers.get('User-Agent'):
		url_prefix = u"http://www.amazon.co.jp/gp/aw/s/?"
		encoding = 'utf-8'
		query_encode = [
			('__mk_ja_JP', u"カタカナ".encode(encoding)),
			('i', u"stripbooks".encode(encoding)),
			('k', unicode(q_key).encode(encoding)),
			]
	else:
		url_prefix = u"http://www.amazon.co.jp/gp/search/?"
		encoding = 'utf-8'
		query_encode = [
			('__mk_ja_JP', u"カタカナ".encode(encoding)),
			('url', u"search-alias".encode(encoding)+u"=".encode(encoding)+u"stripbooks".encode(encoding)),
			('field-keywords', unicode(q_key).encode(encoding)),
			]
	amazon_search = url_prefix + urllib.urlencode(query_encode)

	pagination = Pagination(page, Limit, results.number_found)

	return render_template(
		'search.html',
		title = u"検索結果："+q_key,
		query = (q_key, results.number_found),
		amazon_search = amazon_search,
		itemlist = tmplist,
		current_user = current_user,
		pagination = pagination
		)

"""
@app.route('/test')
def new_items():
	all_items = memcache.get("all_items_list")
	if all_items is None:
		all_user = Users.query()
		all_items = []
		for user in all_user.iter():
			all_items += user.handlist
		all_items = list(set(all_items))
		memcache.set(key="all_items_list", value=all_items)
	all_items_raw = Items.query()
	for item in all_items_raw.iter():
		try:
			all_items.remove(item.asin)
		except:
			pass
	offset = 0
	limit = 10
	for page in map(lambda v: v+1, range(100)):
		offset = (int(page)-1)*limit
		if all_items[offset:offset+limit] == []:
			break
		dbHandler.set_items(all_items[offset:offset+limit])
	return str(offset+limit) + " set."
"""
