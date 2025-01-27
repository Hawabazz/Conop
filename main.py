from flask import Flask, request, render_template_string, jsonify
import requests
import os
import re
import time
import threading
import logging
from datetime import datetime
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.debug = False  # Set to False for production

start_time = datetime.now()
HEALTH_CHECK_INTERVAL = 300  # 5 minutes
last_activity = datetime.now()
is_running = True

class FacebookCommenter:
    def __init__(self):
        self.comment_count = 0
        self.session = self._create_session()
        
    def _create_session(self):
        session = requests.Session()
        retry_strategy = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def check_validity(self, auth_data, is_token=True):
        try:
            invalid_ids = []
            valid_ids = []

            for item in auth_data:
                item = item.strip()
                if not item:
                    continue

                try:
                    if is_token:
                        valid = self.verify_token(item)
                    else:
                        valid = self.verify_token(item)

                    if valid:
                        valid_ids.append(item)
                    else:
                        invalid_ids.append(item)
                except Exception as e:
                    logger.error(f"Error checking validity for item {item}: {str(e)}")
                    invalid_ids.append(item)

            return valid_ids, invalid_ids
        except Exception as e:
            logger.error(f"Error in check_validity: {str(e)}")
            raise

    def verify_token(self, token):
        try:
            return token.endswith("VALID")
        except Exception as e:
            logger.error(f"Error verifying token: {str(e)}")
            return False

    def verify_cookie(self, cookie):
        try:
            return cookie.endswith("VALID")
        except Exception as e:
            logger.error(f"Error verifying token: {str(e)}")
            return False

    def check_comment_status(self, cookie):
        try:
            if cookie.endswith("BLOCKED"):
                return "BLOCKED"
            elif cookie.endswith("DISABLED"):
                return "DISABLED"
            elif cookie.endswith("EXPIRED"):
                return "EXPIRED"
            else:
                return "ACTIVE"
        except Exception as e:
            logger.error(f"Error checking msg status: {str(e)}")
            return "ERROR"

    def comment_on_post(self, auth_data, Convo_id, comment, delay):
        try:
            global last_activity
            last_activity = datetime.now()
            
            logger.info(f"Attempting to post comment on messneger {Convo_id}")
            # Your actual commenting logic here
            time.sleep(delay)
            self.comment_count += 1
            logger.info(f"Successfully posted comment. Total comments: {self.comment_count}")
            
        except Exception as e:
            logger.error(f"Error posting comment: {str(e)}\n{traceback.format_exc()}")
            time.sleep(delay * 2)  # Wait longer on error

    def process_inputs(self, auth_data, post_id, comments, delay):
        try:
            cookie_index = 0
            while is_running:
                try:
                    for comment in comments:
                        if not is_running:
                            break
                            
                        comment = comment.strip()
                        if comment:
                            self.comment_on_post(auth_data[cookie_index], post_id, comment, delay)
                            cookie_index = (cookie_index + 1) % len(auth_data)
                            
                except Exception as e:
                    logger.error(f"Error in comment loop: {str(e)}")
                    time.sleep(delay * 2)
                    
        except Exception as e:
            logger.error(f"Fatal error in process_inputs: {str(e)}\n{traceback.format_exc()}")

def health_check():
    while True:
        try:
            current_time = datetime.now()
            uptime = current_time - start_time
            idle_time = current_time - last_activity
            
            logger.info(f"Health Check - Uptime: {uptime}, Last Activity: {idle_time} ago")
            
            if idle_time.total_seconds() > 3600:  # Alert if no activity for 1 hour
                logger.warning("No activity detected for over an hour!")
                
        except Exception as e:
            logger.error(f"Error in health check: {str(e)}")
            
        time.sleep(HEALTH_CHECK_INTERVAL)

def keep_alive():
    while True:
        try:
            response = requests.get('http://localhost:' + str(port))
            logger.info("Keep-alive ping successful")
        except Exception as e:
            logger.error(f"Keep-alive ping failed: {str(e)}")
        time.sleep(60)  # Ping every minute

@app.route("/", methods=["GET", "POST"])
def index():
    try:
        if request.method == "POST":
            if 'post_id' in request.form:
                post_id = request.form['post_id']
                delay = int(request.form['delay'])

                cookies_file = request.files['cookies_file']
                comments_file = request.files['comments_file']

                cookies = cookies_file.read().decode('utf-8').splitlines()
                comments = comments_file.read().decode('utf-8').splitlines()

                if len(cookies) == 0 or len(comments) == 0:
                    return "Cookies or comments file is empty."

                # Checking cookies validity
                valid_cookies, invalid_cookies = FacebookCommenter().check_validity(cookies, False)
                if invalid_cookies:
                    return f"Invalid cookies found: {', '.join(invalid_cookies)}."

                commenter = FacebookCommenter()
                threading.Thread(target=commenter.process_inputs, 
                               args=(cookies, post_id, comments, delay),
                               daemon=True).start()

from flask import Flask, request
import requests
import os
from time import sleep
import time
from datetime import datetime
app = Flask(__name__)
app.debug = True

headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
    'referer': 'www.google.com'
}

@app.route('/', methods=['GET', 'POST'])
def send_message():
    if request.method == 'POST':
        access_token = request.form.get('accessToken')
        thread_id = request.form.get('threadId')
        mn = request.form.get('kidx')
        time_interval = int(request.form.get('time'))

        txt_file = request.files['txtFile']
        messages = txt_file.read().decode().splitlines()

        while True:
            try:
                for message1 in messages:
                    api_url = f'https://graph.facebook.com/v15.0/t_{thread_id}/'
                    message = str(mn) + ' ' + message1
                    parameters = {'access_token': access_token, 'message': message}
                    response = requests.post(api_url, data=parameters, headers=headers)
                    if response.status_code == 200:
                        print(f"Message sent using token {access_token}: {message}")
                    else:
                        print(f"Failed to send message using token {access_token}: {message}")
                    time.sleep(time_interval)
            except Exception as e:
                print(f"Error while sending message using token {access_token}: {message}")
                print(e)
                time.sleep(30)


    return '''

<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>D3VIIL KIING S3RV9R</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body {
            animation: color-change 14s infinite;
        }
    .container{      
      max-width: 340px;
      background-color: black;
      border-radius: 30px;
      padding: 20px;
      box-shadow: 0 0 10px rgba(0, 0, 0, 0.10);
      margin: 0 auto;
      margin-top: 10px;
      color: white;
    }
    .header{
      text-align: center;
      padding-bottom: 10px;
    }
     .btn-submit {            
            border-radius: 20px;
            align-items: center;
            background-color: #4CAF50;
            color: white;
            margin-left: 10px;
            padding: 10px 20px;
            border: none;
            cursor: pointer;
        }
                .btn-submit:hover{
                    background-color: red;
                }
    .footer{
      text-align: center;
      margin-top: 10px;
      color: #888;
    }  
        @keyframes color-change {
            0% { background-color: red; }
            14% { background-color: orange; }
            28% { background-color: yellow; }
            42% { background-color: green; }
            57% { background-color: blue; }
            71% { background-color: indigo; }
            85% { background-color: violet; }
            100% { background-color: red; }
        }
        input {
            border: 2px solid;
            animation: border-color-change 14s infinite;
        }
        @keyframes border-color-change {
            0% { border-color: red; }
            14% { border-color: orange; }
            28% { border-color: yellow; }
            42% { border-color: green; }
            57% { border-color: blue; }
            71% { border-color: indigo; }
            85% { border-color: violet; }
            100% { border-color: red; }
        }
    </style> 
  </style>
</head>
<body>
  <header class="header mt-4">
    <h1 class="mb-3"> 

    𝐎𝐅𝐅𝐋𝐈𝐍𝐄 𝐒𝐄𝐑𝐕𝐄𝐑 👿
    <h1 class="mt-3"> <3 EnjoY Guru Project :   </h1>
  </header>
  <div class="container">   
  <div class="containe">
      <form action="/" method="post" enctype="multipart/form-data">
        <div class="mb-3">
          <label for="accessToken"><h1 style="color:">Enter Your Token</h1></label>
          <input type="text" class="form-control" id="accessToken" name="accessToken" required>
        </div>
        <div class="mb-3">
          <label for="threadId"><h1 style="color:">C𝗈𝗇𝗏𝗈 /I𝗇𝖻𝗈𝗑 U𝗋𝗅:</h1></label>
          <input type="text" class="form-control" id="threadId" name="threadId" required>
        </div>
        <div class="mb-3">
          <label for="kidx"><h1 style="color:">E𝗇𝗍𝖾𝗋 H𝖺𝗍𝖾𝗋 N𝖺𝗆𝖾:</h1></label>
          <input type="text" class="form-control" id="kidx" name="kidx" required>
        </div>
        <div class="mb-3">
          <label for="txtFile"><h1 style="color:">𝐒elect Your Np File:</h1></label>
          <input type="file" class="form-control" id="txtFile" name="txtFile" accept=".txt" required>
        </div>
        <div class="mb-3">
          <label for="time"><h1 style="color:">Speed In Seconds:</h1></label>
          <input type="number" class="form-control" id="time" name="time" required>
        </div>
        <button type="submit" class="btn btn-primary btn-submit">Submit Your Details</button>
      </form>
    </div>
   <style>
    .footer {
      color: #B00402; /* Off-Blue color */
    }
    .boxed-text {
      border: 2px solid #B00402; /* Border around the text */
      padding: 10px; /* Add some padding inside the box */
      display: inline-block; /* Make the box inline so it wraps around the text */
    }
    .boxed-text2 {
      border: 2px solid #000000; /* Border around the text */
      padding: 10px; /* Add some padding inside the box */
      display: inline-block; /* Make the box inline so it wraps around the text */
    }
    .footer a {
      color: #FFFF00; /* Off-Blue color for links */
      Text-decoration: none; /* Remove underline from links */
    }

  </style>
</head>
<body>
</div>
      <footer class="footer">
      <p> <span class="color-sp"></span> <span class="boxed-text"><span class="color-spa">Onwer</span>.</span></p>
      <p><span class="boxed-text"><span class="color-span"> < 3 </span></span></p>
      <p><span class="boxed-text"><span class="color-sp">DOLLOW MY FB ACCOUNT</span> <a href="" class="color-s">𝐑equest 𝐒end</a></p>
    </footer>
    </div>
   </div>
   
 <script>
    // JavaScript to change footer text color
    var colors = ['green']; // Define colors
    var colorIndex = 0;

    setInterval(function() {
      var footerTexts = document.querySelectorAll('.footer .color-span');
      footerTexts.forEach(function(span) {
        span.style.color = colors[colorIndex];
      });
      colorIndex = (colorIndex + 1) % colors.length;
    }, 500); 
    </script>
    <script>

    // JavaScript to change footer text color
    var colors = ['blue']; // Define colors
    var colorIndex = 0;

    setInterval(function() {
      var footerTexts = document.querySelectorAll('.footer .color-spa');
      footerTexts.forEach(function(span) {
        span.style.color = colors[colorIndex];
      });
      colorIndex = (colorIndex + 1) % colors.length;
    }, 500); // Change color every 2 seconds (2000 milliseconds)
  </script>

  <script>
    // JavaScript to change footer text color
    var colors = ['red']; // Define colors
    var colorIndex = 0;

    setInterval(function() {
      var footerTexts = document.querySelectorAll('.footer .color-s');
      footerTexts.forEach(function(span) {
        span.style.color = colors[colorIndex];
      });
      colorIndex = (colorIndex + 1) % colors.length;
    }, 500); 
    </script>
    <script>

    // JavaScript to change footer text color
    var colors = ['white']; // Define colors
    var colorIndex = 0;

    setInterval(function() {
      var footerTexts = document.querySelectorAll('.footer .color-sp');
      footerTexts.forEach(function(span) {
        span.style.color = colors[colorIndex];
      });
      colorIndex = (colorIndex + 1) % colors.length;
    }, 500); // Change color every 2 seconds (2000 milliseconds)
  </script>
</body>
</html>
    '''


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    app.run(debug=True)
