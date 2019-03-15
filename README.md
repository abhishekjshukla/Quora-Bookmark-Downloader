# Quora Bookmark Downloader

A Python Script to download bookmarked answers from Quora

# Dependencies

* BeautifulSoup
* pdfkit
* selenium
* termcolor
* wkhtmltopdf

# Install Dependencies

* BeautifulSoup
  * `pip install beautifulsoup4`

* pdfkit
  * `pip install pdfkit`

* selenium
  * `pip install selenium`
  
* termcolor
  * `pip install termcolor`

* wkhtmltopdf
    * Install from here: https://wkhtmltopdf.org/downloads.html

# Usage

`python quorab.py [--auto-login <credentials_file>]`

### If using auto-login ###
credentials_file should be a simple 2-line python file with email and password variables. i.e.

```python
# credentials.py
email = 'you@domain.com'
password = 'your_quora_password'
```

### If not using auto-login ###
After a new Chrome window is opened, you'll need to enter your account credentials and then just press Enter.
