import os
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from pathlib import Path
import time
import pandas as pd
import dateutil
from datetime import datetime, timedelta
import sys
from selenium.common.exceptions import NoSuchElementException

jira = {'url': 'https://admin.atlassian.com/'}


def get_jira_details():
    global jira
    with open('./jira_creds', 'r') as f:
        for line in f:
            (key, val) = line.split("=")
            jira[key] = val.strip("\"\n")

    jira['days'] = int(sys.argv[1:][0].split('=')[1])


def main():
    get_jira_details()

    # chrome_options = Options()
    # chrome_options.add_argument('--headless')
    # chrome_options.binary_location = '/Application/Google Chrome.app/Contents/MacOS/Google Chrome'
    driver = webdriver.Chrome("./chromedriver.exe")  # , chrome_options=chrome_options)
    driver.get(jira['url'])

    time.sleep(2)
    username = driver.find_element_by_id('username')
    username.clear()
    # username.send_keys('akshita.raghuvanshi@prosus.com')
    username.send_keys(jira['JIRA_USER'])
    print("[*] Input username success")

    login = driver.find_element_by_xpath('//*[@id="login-submit"]')
    login.click()

    time.sleep(2)
    password = driver.find_element_by_id('password')
    password.clear()
    password.send_keys(jira['JIRA_PASS'])
    print("[*] Input password success")

    login = driver.find_element_by_xpath('//*[@id="login-submit"]')
    login.click()

    time.sleep(10)
    name = driver.find_element_by_xpath("//*[contains(text(), 'jochemxyz')]").click()
    print("[*] Onto the user management portal")

    user_file = download_user_file(driver)
    email_address_to_disable = get_inactive_users(user_file, jira['days'])
    print(email_address_to_disable)

    for user in email_address_to_disable:
        set_jira_user_inactive(driver, user)

    email_address_to_disable = get_never_accessed_users(user_file)
    print(email_address_to_disable)

    for user in email_address_to_disable:
        set_jira_user_never_accessed(driver, user)
    # set_jira_user_inactive(driver,'bruno.rocha@zoop.com.br')


def download_user_file(driver):
    try:
        # Click "Export users"
        '''
        Sometimes we get a "StaleElementException" if the element is reloaded between moving 
        and clicking, so in that case we retry
        '''
        time.sleep(2)
        attempts = 0
        while attempts < 5:
            try:
                driver.find_element_by_xpath("//*[contains(text(), 'Export users')]").click()
                break
            except Exception as error:
                print("[!] {}".format(error))
                time.sleep(2)
            attempts += 1

        # Click "Download file"
        driver.implicitly_wait(15)
        driver.find_element_by_xpath("//*[contains(text(), 'Download file')]").click()

        # wait to download the file
        while not is_download_finished("C:\\Users\\Jochem\\Downloads", "export-users.csv"):
            time.sleep(1)

        if not Path('C:\\Users\\Jochem\\Downloads').exists():
            print("[!] Failed to download export-users.csv")
            quit_driver(driver)
            exit(1)

        return "C:\\Users\\Jochem\\Downloads\\export-users.csv"

    except Exception as error:  # pylint: disable=broad-except
        print("[!] {}".format(error))
        quit_driver(driver)
        exit(1)


def is_download_finished(temp_folder, file):
    chrome_temp_file = sorted(Path(temp_folder).glob('*.crdownload'))
    downloaded_file = Path(temp_folder + file).exists()
    if (len(chrome_temp_file) == 0) and downloaded_file:
        return True
    else:
        return False


def quit_driver(driver):
    driver.quit()
    print('[*] quitting')


def get_inactive_users(filename, days):
    pd.set_option('display.max_rows', None)
    df = pd.read_csv(filename, parse_dates=['Last seen in Jira Software - prosus-ra', 'Added to org',
                                            'Last seen in Jira Software - prosus-ra'])
    df = df.loc[df['Last seen in Jira Work Management - prosus-ra'] != 'Never accessed']
    df['Last seen in Jira Work Management - prosus-ra'] = df['Last seen in Jira Work Management - prosus-ra'].apply(
        dateutil.parser.parse)

    results = df[(df['Last seen in Jira Work Management - prosus-ra'] < numberOfDaysAgo(days)) & (
                df['Added to org'] < numberOfDaysAgo(days)) & (df['User status'] == 'Active')]
    print("[+] Found " + str(len(results['email'].unique())) + " inactive users")
    print(results[['email', 'Last seen in Jira Work Management - prosus-ra']])
    input("[?] Do you want to disable these Jira users? Press any key to continue. Press CTRL+C to abort")
    return set(results['email'].to_list())


def get_never_accessed_users(filename):
    pd.set_option('display.max_rows', None)
    df = pd.read_csv(filename, parse_dates=['Last seen in Jira Software - prosus-ra', 'Added to org',
                                            'Last seen in Jira Software - prosus-ra'])
    results = df.loc[df['Last seen in Jira Work Management - prosus-ra'] == 'Never accessed']

    print("[+] Found " + str(len(results['email'].unique())) + " inactive users")
    print(results[['email', 'Last seen in Jira Work Management - prosus-ra']])
    input("[?] Do you want to disable these Jira users? Press any key to continue. Press CTRL+C to abort")
    return set(results['email'].to_list())


def numberOfDaysAgo(numberOfDays):
    return datetime.now() - timedelta(days=numberOfDays)


def set_jira_user_inactive(driver, user):
    """ Disable a Jira user"""
    try:
        # Click Search field and enter the username
        driver.find_element_by_xpath("//input[@aria-label='Search']").click()
        # First clear any input from previous queries
        driver.find_element_by_xpath("//input[@aria-label='Search']").send_keys(Keys.COMMAND + "a")
        driver.find_element_by_xpath("//input[@aria-label='Search']").send_keys(Keys.DELETE)
        driver.find_element_by_xpath("//input[@aria-label='Search']").send_keys(user)

        # Wait one second to fetch results before continuing
        time.sleep(3)

        # Click on the button with three-dots
        driver.find_element_by_css_selector('.cLrmQm').click()
        time.sleep(1)
        # Click on 'Revoke site access'
        driver.find_element_by_xpath("//*[contains(text(), 'Revoke site access')]").click()

        time.sleep(1)
        # Click final red 'Revoke site access' button
        driver.find_element_by_css_selector('#submit-activate-user-modal').click()
        time.sleep(2)
        print("[+] User {} succesfully disabled".format(user))

    except NoSuchElementException as e:
        if "Revoke site access" in str(e):
            print("[!] Cannot Revoke site access, {} might be already inactive".format(user))
        time.sleep(1)

    except Exception as error:  # pylint: disable=broad-except
        print("[!] {}".format(error))
        screenshot = '{}/{}.png'.format(".", filename)
        driver.get_screenshot_as_file(screenshot)
        print("[!] Screenshot saved as - " + screenshot)
        driver.quit()


def set_jira_user_never_accessed(driver, user):
    """ Disable a Jira user"""
    try:
        # Click Search field and enter the username
        driver.find_element_by_xpath("//input[@aria-label='Search']").click()
        # First clear any input from previous queries
        driver.find_element_by_xpath("//input[@aria-label='Search']").send_keys(Keys.COMMAND + "a")
        driver.find_element_by_xpath("//input[@aria-label='Search']").send_keys(Keys.DELETE)
        driver.find_element_by_xpath("//input[@aria-label='Search']").send_keys(user)

        # Wait one second to fetch results before continuing
        time.sleep(3)

        # Click on the button with three-dots
        driver.find_element_by_css_selector('.cLrmQm').click()
        time.sleep(1)
        # Click on 'Revoke site access'
        driver.find_element_by_xpath("//*[contains(text(), 'Show details')]").click()
        time.sleep(1)
        driver.find_element_by_xpath("//*[@class='css-ji2l50']").click()
        driver.back()
    except:
        pass


main()
