import getopt
import http
import importlib
import os
import sys
import time

import pdfkit
import urllib

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from termcolor import colored
from urllib.request import urlopen

# Constants.
QUORA_BOOKMARKS_URL = 'https://www.quora.com/bookmarks'
LOGIN_PAGE_WAIT_TIME = 10
BOOMARKS_LOAD_WAIT_TIME = 15
ANSWERS_DIRECTORY = 'answers'
FAILED_FILE = os.getcwd() + '/failed.txt'
OMISSION_STRING = '...'
MAX_FILENAME_LEN = 255 - len('.pdf')

auto_login = False


def usage():
    print(
        colored('Usage: python quorab.py [--auto-login <credentials_file>]', 'yellow'))


try:
    opts, args = getopt.getopt(sys.argv[1:], 'h', ['auto-login='])
except getopt.GetoptError as opt_err:
    print(colored(opt_err, 'red'))
    usage()
    sys.exit(1)
for opt, arg in opts:
    if opt == '-h':
        usage()
        sys.exit()
    elif opt == '--auto-login':
        try:
            credentials_module_name = arg
            # With this, users can pass both .py files and just the name of the module.
            # Useful for auto-complete in bash prompt.
            if credentials_module_name.endswith('.py'):
                credentials_module_name = credentials_module_name.replace(
                    '.py', '')
            credentials = importlib.import_module(credentials_module_name)
            try:
                email = credentials.email
                password = credentials.password
                auto_login = True
            except AttributeError as attr_err:
                print(colored(attr_err, 'red'))
                print(
                    colored('Please see the README for credentials file format.', 'yellow'))
                sys.exit(3)
        except ModuleNotFoundError as mod_err:
            print(colored(mod_err, 'red'))
            sys.exit(2)

if not auto_login:
    # I know it's a little strange to print this info here and not as an else statement below.
    # However, there's a good reason it's here: Chrome will open on the next command (webdriver.Chrome())
    # and the user's computer will likely auto-focus to Chrome and away from the terminal, and we want
    # the user to see this info first.
    print(colored('Auto-login not enabled. Please manually login.', 'yellow'))

# chromedriver needs to be added to $PATH. Can be done by adding it to /usr/local/bin/ on a Mac.
driver = webdriver.Chrome()

# This will automatically redirect to login page. However, it will redirect back to the Bookmarks page after login.
driver.get(QUORA_BOOKMARKS_URL)

if auto_login:
    try:
        WebDriverWait(driver, LOGIN_PAGE_WAIT_TIME).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[id$=_submit_button]')))
        print(colored('Attempting auto-login...', 'cyan'))

        # It seems that Quora obfuscates and/or hashes id and class names upon each page load, so that is why we use these CSS selectors and list indeces.
        # If Quora ever changes the DOM structure or id/class names of its login page, this could break.
        driver.find_elements_by_css_selector(
            '[id$=_email]')[2].send_keys(email)
        driver.find_elements_by_css_selector(
            '[id$=_password]')[1].send_keys(password)
        driver.find_element_by_css_selector(
            '[id$=_submit_button]').click()
    except TimeoutException:
        print(
            'Loading of login page took too much time. Try increasing LOGIN_PAGE_WAIT_TIME.')
    except:
        print('Auto-login failed. Please try logging in manually.')

# Wait for login until we're on the Bookmarks Page.
while driver.current_url != QUORA_BOOKMARKS_URL:
    pass

print(colored('Successfully logged in.', 'green'))
print(colored('Now auto-scrolling bookmarks page...', 'green'))

# We now load (i.e. scroll) the page until all answers are displayed.
old_num_of_answers = len(
    driver.find_elements_by_class_name('answer_permalink'))
curr_num_of_answers = old_num_of_answers
old_time = time.time()
while True:
    driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')
    if time.time() > old_time + BOOMARKS_LOAD_WAIT_TIME:
        curr_num_of_answers = len(
            driver.find_elements_by_class_name('answer_permalink'))
        if curr_num_of_answers == old_num_of_answers:
            break
        else:
            old_time = time.time()
            old_num_of_answers = curr_num_of_answers

all_ans_elements = driver.find_elements_by_class_name('answer_permalink')
print(colored(str(len(all_ans_elements)) + ' answers found.', 'cyan'))

# Set up answers directory.
if not os.path.exists(ANSWERS_DIRECTORY):
    os.makedirs(ANSWERS_DIRECTORY)
    print(colored('Created ' + ANSWERS_DIRECTORY + ' directory. ', 'cyan'), end='')
else:
    print(colored(ANSWERS_DIRECTORY + ' directory found. ', 'cyan'), end='')
os.chdir(ANSWERS_DIRECTORY)
print(colored('Putting PDFs there.', 'cyan'))

options = {
    'page-size': 'Letter',
    'dpi': 450,
    'javascript-delay': 10000,
    'quiet': ''
}

for web_element in all_ans_elements:
    ans_url = web_element.get_attribute('href')
    url_read_clean = False
    num_incomplete_reads, num_http_error = 0, 0
    while (not url_read_clean) and num_incomplete_reads < 5 and num_http_error < 5:
        try:
            conn = urlopen(ans_url)
            soup = BeautifulSoup(conn.read(), 'html.parser')
            url_read_clean = True
        except http.client.IncompleteRead:
            print(colored('IncompleteRead. Trying again.', 'yellow'))
            num_incomplete_reads += 1
        except urllib.error.HTTPError:
            print(colored('HTTPError. Trying again.', 'yellow'))
            num_http_error += 1
        finally:
            if num_incomplete_reads == 5:
                print(colored('Failed \"' + ans_url +
                              '\" due to IncompleteRead. Now moving on.', 'red'))
            if num_http_error == 5:
                print(colored('Failed \"' + ans_url +
                              '\" due to HTTPError. Now moving on.', 'red'))
    title = soup.find('a', class_='question_link').text
    raw_author_text = soup.find('div', class_='feed_item_answer_user').text
    # This strips away whitespace and the author 'credentials' line.
    author = raw_author_text.strip().split(',')[0]
    author_string = ' (' + author + ')'
    unsafe_title_and_author = title + author_string

    # '/' and '%' can't go into filenames.
    title_and_author = unsafe_title_and_author.replace(
        '/', ' or ').replace('%', ' percent')

    # Filenames must be <= 255 characters.
    if len(title_and_author) > 255:
        # Note: I'm assuming that author names (just names, not credentials lines) wont have '/' or '%'. If that changes, this could break. Easy fix is just to reduce MAX_FILENAME_LEN by 10.
        # We need len(trimmed_title) + len(carry_on_string) + len(author_string) = MAX_FILENAME_LEN
        # Therefore, len(trimmed_title) = MAX_FILENAME_LEN - len(carry_on_string) - len(author_string)
        trimmed_title = title_and_author[:MAX_FILENAME_LEN -
                                         len(OMISSION_STRING) -
                                         len(author_string)]
        title_and_author = trimmed_title + OMISSION_STRING + author_string
        print('Trimming filename to conform to length standards: ',
              unsafe_title_and_author)

    new_filename = title_and_author + '.pdf'

    # Starting at 1 and immediately incrementing to 2 because we want count to match up with 'javascript-delay'.
    # This is so we can eaily and intuitively incrememnt 'javascript-delay' if page load takes too much time.
    count = 1
    while count <= 6:
        try:
            # Note to Mac users: You may need to move EPPEX Plug-In to Disabled Plug-Ins.
            # i.e. run this in your command prompt (without the quotation marks): "sudo mv EPPEX\ Plugin.plugin Disabled\ Plug-Ins/"

            # This is so the script can be run multiple times in a row (without having to recreate the same files), after the user has added more bookmarks.
            if os.path.isfile(new_filename):
                print(colored('File already exists :)', 'cyan'))
            else:
                pdfkit.from_url(ans_url, new_filename, options=options)
                print(colored('Succeeded: ' + title_and_author, 'green'))
            break
        except OSError as error:
            # It seems this error is caused by the page taking too long to load. In response, we increase allotted 'load time' (javascript-delay) and make another attempt, up to five times.
            count += 1
            if count >= 6:
                print(colored('Failed \"' + title_and_author +
                              '\" after ' + str(count) + ' tries. Now moving on.', 'red'))
                print(colored(str(error), 'red'))
                # Log failures.
                with open(FAILED_FILE, 'a') as failed:
                    failed.write(title_and_author + '\n')
                break
            else:
                # Here we increase page wait time by 10 seconds.
                options['javascript-delay'] = count * 10000
        except Exception as e:
            print(colored('Failed ' + title_and_author +
                          ' because of unknown error.', 'red'))
            print(colored('Type of Error: ' + str(type(e)), 'red'))
            print(colored(str(e), 'red'))
            # Log failures.
            with open(FAILED_FILE, 'a') as failed:
                failed.write(title_and_author + '\n')
            break
    # Reset javascript-delay to 10 seconds for the next loop iteration.
    options['javascript-delay'] = 10000

print('PDF Downloads Completed!')

driver.quit()
