import argparse, sys, time
from pathlib import Path
from selenium import webdriver
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options

USERNAME = "-"
PASSWORD = "-"
LOGIN_URL = "https://seller.mm.ru/seller/signin"
TIMER_URL = "https://seller.mm.ru/seller/14229/marketing/marketing-sales/timer"
DOWNLOAD_DIR = Path(__file__).resolve().parent

BTN_ADD_PRODUCTS = "button[data-test-id='button__timer-panel-search-filters-add']"
BTN_SWITCH_UPLOAD = "//div[contains(@class,'timer-create__switch')]//button[contains(.,'Загрузить файл')]"
BTN_DOWNLOAD = "button[data-test-id='button__create-timer-file-worker-modal-step-download']"


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--headless", action="store_true")
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def create_driver(headless=False):
    o = Options()
    if headless:
        o.add_argument("--headless=new")
        o.add_argument("--window-size=1920,1080")
    o.add_argument("--disable-dev-shm-usage")
    o.add_argument("--no-sandbox")
    o.add_argument("--lang=ru-RU")
    o.add_experimental_option("prefs", {
        "download.default_directory": str(DOWNLOAD_DIR),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    })
    return webdriver.Chrome(options=o)


def log(msg, debug):
    if debug:
        print(f"[*] {msg}")


def wait_click(driver, locator, by="css", timeout=20, debug=False):
    w = WebDriverWait(driver, timeout)
    el = w.until(EC.element_to_be_clickable((By.CSS_SELECTOR if by == "css" else By.XPATH, locator)))
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    try:
        el.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", el)
    log(f"Кликнули {locator}", debug)
    return el


def log_in(driver, debug=False):
    driver.get(LOGIN_URL)
    w = WebDriverWait(driver, 20)
    w.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(USERNAME)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[data-test-id='button__next']").click()
    log("Нажали Продолжить", debug)
    time.sleep(8)


def fetch_timer_text(driver):
    driver.get(TIMER_URL)
    return WebDriverWait(driver, 20).until(
        EC.visibility_of_element_located((By.XPATH, "//span[contains(text(),'Осталось')]"))
    ).text


def extract_time(raw):
    return " ".join(
        raw.replace("Осталось", "")
        .replace(".", "")
        .replace("ч", " ч ")
        .replace("м", " м ")
        .split()
    )


def download_product_list(driver, download_dir, debug=False, timeout=120):
    existing = set(download_dir.iterdir())
    wait_click(driver, BTN_ADD_PRODUCTS, debug=debug)
    time.sleep(2)
    wait_click(driver, BTN_SWITCH_UPLOAD, by="xpath", debug=debug)
    time.sleep(1)
    wait_click(driver, BTN_DOWNLOAD, debug=debug)
    end = time.time() + timeout
    while time.time() < end:
        for f in download_dir.iterdir():
            if f in existing:
                continue
            if f.suffix.lower() in {".xlsx", ".xls", ".csv"} and not f.with_suffix(f.suffix + ".crdownload").exists():
                log(f"Файл скачан: {f.name}", debug)
                return f
        time.sleep(1)
    raise TimeoutException("Файл не скачался за отведённое время")


def main():
    args = parse_args()
    d = create_driver(args.headless)
    try:
        log_in(d, args.debug)
        print(extract_time(fetch_timer_text(d)))
        f = download_product_list(d, DOWNLOAD_DIR, debug=args.debug)
        print(f"Успешно скачан и помещён в папку: {f.name}")
    finally:
        d.quit()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[!] Ошибка: {e}", file=sys.stderr)
        sys.exit(1)
