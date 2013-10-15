# コードレビュー
# フレンドリスト機能について
* 2012/12/17 月曜日 2:43
* fb_friendに存在するが、DataStoreに存在しない場合に対応できてない
* 結果、表示がおかしくなる
    * 実際に動かす場合に起こりにくい？
    * 対応するかどうかは放置→TODO化
 
# 表示できないアイテム
* [Amazon.co.jp： 体系的に学ぶ 安全なWebアプリケーションの作り方　脆弱性が生まれる原理と対策の実践: 徳丸 浩: 本](http://www.amazon.co.jp/dp/4797361190)
## エラーログ

		Exception on /item/4797361190 [GET]
		Traceback (most recent call last):
		  File "./distlibs.zip/flask/app.py", line 1687, in wsgi_app
		    response = self.full_dispatch_request()
		  File "./distlibs.zip/flask/app.py", line 1360, in full_dispatch_request
		    rv = self.handle_user_exception(e)
		  File "./distlibs.zip/flask/app.py", line 1358, in full_dispatch_request
		    rv = self.dispatch_request()
		  File "./distlibs.zip/flask/app.py", line 1344, in dispatch_request
		    return self.view_functions[rule.endpoint](**req.view_args)
		  File "/base/data/home/apps/s~yowatariapp/1.363912150728089941/main.py", line 303, in item
		    item = set_item(arg_asin)
		  File "/base/data/home/apps/s~yowatariapp/1.363912150728089941/main.py", line 345, in set_item
		    pic = urllib2.urlopen(soupitem.largeimage.url.string).read()
		  File "/base/python27_runtime/python27_lib/versions/1/google/appengine/ext/db/__init__.py", line 970, in __init__
		    prop.__set__(self, value)
		  File "/base/python27_runtime/python27_lib/versions/1/google/appengine/ext/db/__init__.py", line 614, in __set__
		    value = self.validate(value)
		  File "/base/python27_runtime/python27_lib/versions/1/google/appengine/ext/db/__init__.py", line 2851, in validate
		    % (self.name, len(value), self.MAX_LENGTH))
		BadValueError: Property url is 544 characters long; it must be 500 or less.