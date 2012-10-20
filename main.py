import cookielib
import json
import logging
import os
import urllib
import urllib2
import urlparse

from google.appengine.api import app_identity
from google.appengine.api import mail
from google.appengine.ext import webapp

import bs4

def url_fetch(url, data=None, headers=None):
    if headers is None:
        headers = dict()
    req = urllib2.Request(url, data=data, headers=headers)
    r = urllib2.urlopen(req, timeout=60)
    r.content = r.read()
    r.headers = r.info()
    return r

class DXYPage(webapp.RequestHandler):
    def get(self):
        self.setup()
        try:
            self.login(os.environ["DXY_USERNAME"], os.environ["DXY_PASSWORD"])
            self.fetch_dingdang()
        except Exception:
            logging.exception("Failed.")
            app_id = app_identity.get_application_id()
            mail.send_mail_to_admins("alert@%s.appspotmail.com" % app_id,
                subject="Fail to fetch DingDang",
                body="https://appengine.google.com/logs?&app_id=%s" % app_id)

    def login(self, username, password):
        login_url = "https://auth.dxy.cn/login"
        r = url_fetch(login_url)
        soup = bs4.BeautifulSoup(r.content)
        login_form = soup.find("form", id="user")
        login_inputs = login_form.find_all("input")
        post_data = dict()
        for login_input in login_inputs:
            input_name = login_input.get("name")
            input_name_lower = input_name.lower()
            if input_name is None:
                pass
            elif "username" in input_name_lower:
                post_data[input_name] = username
            elif "password" in input_name_lower:
                post_data[input_name] = password
            else:
                input_value = login_input.get("value")
                if input_value:
                    post_data[input_name] = input_value
        form_action = urlparse.urljoin(login_url, login_form["action"])
        form_method = login_form["method"].lower()
        if form_method == "get":
            o = urlparse.urlparse(form_action)
            query = urlparse.parse_qsl(o[4])
            query.extend((k, v) for k, v in post_data.iteritems())
            o[4] = urllib.urlencode(query)
            form_action = urlparse.urlunparse(o)
            post_data = None
        else:
            post_data = urllib.urlencode(post_data)
        url_fetch(form_action, data=post_data, headers={"Referer": login_url})

    def fetch_dingdang(self):
        home_url = "http://i.dxy.cn/home"
        r = url_fetch(home_url)
        soup = bs4.BeautifulSoup(r.content)
        csrf_token = soup.find("input", attrs={"name": "csrfToken"})["value"]
        login_money_url = "http://i.dxy.cn/snsapi/home/money/login"
        r = url_fetch(login_money_url, data="csrfToken=%s" % csrf_token, headers={"Referer": home_url})
        ajax_response = json.loads(r.content)
        logging.debug(ajax_response["ajaxResponse"]["message"])

    def setup(self):
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.CookieJar()))
        urllib2.install_opener(opener)

app = webapp.WSGIApplication([
    ('/dxy_cron', DXYPage),
], debug=True)