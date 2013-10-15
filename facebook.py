# encoding: utf-8

from urllib import urlencode
import urllib2, json

# Facebookクラス
# GraphAPI及びFQL
# マルチクエリー対応は必要になったらやる
class Facebook:
	def __init__(self, app_id, app_secret, site_url):
		self.client_id = app_id
		self.client_secret = app_secret
		self.redirect_uri = site_url
		self.scope = "user_about_me,user_location,read_friendlists"

	def authorize(self):
		params = dict(
			client_id = self.client_id,
			redirect_uri =self.redirect_uri,
			scope = self.scope
			)
		return "https://graph.facebook.com/oauth/authorize?" + urlencode(params)

	def access_token(self, code, access_token=None):
		params = dict(
			client_id = self.client_id,
			redirect_uri=self.redirect_uri,
			client_secret = self.client_secret,
			code = code
			)
		if access_token is not None:
			params.update(
					dict(
						grant_type = "fb_exchange_token",
						fb_exchange_token = access_token
					)
				)
		response = urllib2.urlopen(
			"https://graph.facebook.com/oauth/access_token?" + urlencode(params)
			).read()
		return response.split('&')[0].split('=')[1]

	def delete_permission(self, access_token):
		params = dict(access_token=access_token)
		request = urllib2.Request("https://graph.facebook.com/me/permissions?" + urlencode(params))
		request.get_method = lambda: 'DELETE'
		try:
			response = urllib2.urlopen(request)
			if response.read() == "true":
				return True
			else:
				return False
		except urllib2.URLError:
			return False

	def me(self, access_token):
		try:
			response = urllib2.urlopen(
				"https://graph.facebook.com/me?locale=ja_JP&access_token="  + access_token
				)
		except urllib2.URLError:
			return "Error"
		return json.loads(response.read())

	def fql(self, access_token, query,  locale="en_US"):
		args = {
			'q': query,
			'format': "json",
			'locale': locale,
			'access_token': access_token,
		}
		try:
			response = urllib2.urlopen(
				"https://graph.facebook.com/fql?" + urlencode(args)
			)
		except urllib2.URLError:
			return "Error"
		return json.loads(response.read())
