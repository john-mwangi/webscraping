import subprocess
import sys
import time
import tkinter
from enum import Enum
from typing import Union

import html2text
import pyautogui
from bs4 import BeautifulSoup
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from . import params


class ContentType(Enum):
    HTML = params.htmls_dir
    TEXT = params.texts_dir


def clean_path(path: str) -> str:
    return path.split(sep=":", maxsplit=1)[1].strip()


def install_driver(browser: str = "firefox") -> Union[tuple[str, str], None]:
    """Installs the appropriate web driver.

    Args:
    ---
    brower: browser driver to install. See `$selenium-manager --help` for options

    Returns:
    ---
    driver_clean: driver absolute path
    browser_clean: binaries absolute path
    """
    print(f"Installing {browser} driver...")

    cmd = f"selenium-manager --browser {browser}"

    result = subprocess.run(cmd, capture_output=True, shell=True, text=True)

    lines = result.stdout.splitlines()

    driver_path = [
        line for line in lines if line.startswith("INFO\tDriver path:")
    ]
    browser_path = [
        line for line in lines if line.startswith("INFO\tBrowser path:")
    ]

    if driver_path:
        driver_clean = clean_path(driver_path[0])
        browser_clean = clean_path(browser_path[0])

        print("Driver path:", driver_clean)
        print("Browser path:", browser_clean)

        print(f"{browser} driver successfully installed.")

        return driver_clean, browser_clean
    else:
        print("Driver not found.")
        return None


def get_driver(browser: str = "chrome"):
    driver_path, browser_path = install_driver(browser)
    webdriver_service = Service(executable_path=driver_path)

    options = Options()
    options.add_argument("--enable-javascript")
    options.add_argument("--start-maximized")
    options.binary_location = browser_path

    driver = Chrome(service=webdriver_service, options=options)

    return driver


def extract_react_html(url: str, page_load_time: int = params.PAGE_LOAD_TIME):
    """Extracts React generated HTML from the browser's devtools and saves the
    content locally.

    Args:
    ---
    url: the page to extract html content
    page_load_time: time in secs to allow for the page to load
    """

    # driver = get_driver()
    options = Options()
    options.browser_version = params.CHROME_VERSION
    options.add_argument("--enable-javascript")
    options.add_argument("--start-maximized")
    driver = Chrome(options=options)
    driver.get(url)

    print(f"waiting for {page_load_time=} sec...")
    time.sleep(page_load_time)

    # Accept cookies
    ActionChains(driver).send_keys(Keys.TAB).send_keys(Keys.ENTER).perform()

    # Open devtools
    # https://pyautogui.readthedocs.io/en/latest/keyboard.html#keyboard-keys
    cmd_ctrl = (
        ["command", "option"]
        if sys.platform == "darwin"
        else ["ctrl", "shift"]
    )

    with pyautogui.hold(cmd_ctrl):
        pyautogui.press("i")

    time.sleep(params.DEFAULT_WAIT_TIME)

    # # print X, Y positions
    # print("Press Ctrl-C to quit.")
    # try:
    #     while True:
    #         x, y = pyautogui.position()
    #         positionStr = "X: " + str(x).rjust(4) + " Y: " + str(y).rjust(4)
    #         print(positionStr, end="")
    #         print("\b" * len(positionStr), end="", flush=True)
    # except KeyboardInterrupt:
    #     print("\n")

    # Copy React generated code
    pyautogui.click(button="right", **params.right_click_pst)
    pyautogui.press("down", presses=6)
    pyautogui.press("right")
    pyautogui.press("down")
    pyautogui.press("return")
    time.sleep(params.DEFAULT_WAIT_TIME)

    # Paste content as string
    react_html = tkinter.Tk().clipboard_get()

    dir_name = ContentType.HTML.value

    if not dir_name.exists():
        dir_name.mkdir()

    page_name = url.split("/")[-2]
    file_path = dir_name / f"{page_name}.html"

    with open(file_path, mode="w") as f:
        f.write(react_html)

    driver.quit()


def parse_html(html: str, file_name: str, save_text: bool = True, **kwargs):
    """Extract useful content from a html file and save it as a txt file

    Args:
    ---
    - html: The html file that will be handled by `html.parser`
    - file_name: The txt file to write the results of parsing the html
    - save_text: Whether to save or return the parsed html
    - kwargs: kwargs to pass to `soup.find_all()`

    Returns
    ---
    if save_text=True: Writes the parsed content to a txt file
    Else, returns a list of the parsed html content
    """

    print(f"Converting to text {file_name}...")

    soup = BeautifulSoup(html, "html.parser")

    converter = html2text.HTML2Text()
    converter.ignore_links = True
    converter.ignore_images = True
    converter.ignore_tables = True

    content = soup.find_all(**kwargs)

    text = converter.handle(str(content))

    if not save_text:
        return text

    dir_name = ContentType.TEXT.value

    if not dir_name.exists():
        dir_name.mkdir()

    file_path = dir_name / file_name

    with open(file_path, mode="w") as f:
        f.write(text)


def page_parsed(page_name: str, content_type: ContentType):
    """Determines if a url's html content has been extracted or converted to text"""

    file_extension = content_type.value.__str__().split("/")[-1][
        : -len("_files")
    ]
    dir_name = content_type.value

    files = dir_name.glob(f"*.{file_extension}")

    return any([file.stem == page_name for file in files])
