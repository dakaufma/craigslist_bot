from bs4 import BeautifulSoup
import urllib.request
import urllib.parse
import sys
import hashlib
import json
import datetime
import random
import smtplib
import unicodedata
import re

FILENAME = 'craig.db'

curl = lambda url: urllib.request.urlopen(url).read()

def soup_from_url(url):
    html = curl(url)
    soup = BeautifulSoup(html, "lxml")
    return soup

def parse_results_search_page(url, search_soup):
    links = search_soup.find_all('a')

    def is_result(a):
        span = a.findChild('span')
        if span is None:
            return False
        return span.has_attr('id') and span['id'] == "titletextonly"

    results = filter(is_result, links)

    formatted_results = []
    for r in results:
        link_url = urllib.parse.urljoin(url, r['href'])
        title = r.findChild('span').string
        formatted_results.append((title, link_url))

    return formatted_results


def hash_images_from_listing_page(url, listing_soup):
    divs = listing_soup.find_all("div")
    thumbs_list = list(filter(lambda d: d.has_attr("id") and d['id'] == "thumbs", divs))
    if len(thumbs_list) == 0:
        return [str(random.random())] # return something with a unique hash
    thumbs = thumbs_list[0]
    imgs = thumbs.find_all('img')
    img_urls = [img['src'] for img in imgs]

    results = [hashlib.md5(curl(url)).hexdigest() for url in img_urls]
    return results


def hash_hash_list(hash_strs):
    hashes = sorted(hash_strs)
    m = hashlib.md5()
    for h in hashes:
        m.update(h.encode('utf-8'))
    return m.hexdigest()


def load_from_file(file_name):
    try:
        f = open(file_name, 'r')
        contents = f.read()
        f.close()
        return json.loads(contents)
    except:
        print("Failed to load information from file, assuming an empty database")
        return []

def save_to_file(file_name, data):
    try:
        f = open(file_name, 'w')
        f.write(json.dumps(data, indent=4, separators=(', ', ': ')))
        f.close()
    except:
        print("Failed to write database, something is wrong")
        raise


def send_email(from_addr, to_addr, subject, body):
    message = """From: {}
To: {}
Subject: {}

{}
""".format(from_addr, to_addr, subject, body)
    message = unicodedata.normalize('NFKD', message).encode('ascii','ignore')
    try:
        smtp = smtplib.SMTP('outgoing.mit.edu')
        smtp.sendmail(from_addr, [to_addr], message)
    except SMTPException:
        print("Failed to send email alert")


def main(search_url_file, to_addr):
    print("Loading Craigslist search URLs")
    f = open(search_url_file, 'r')
    search_urls = filter(lambda s: len(s) > 0, f.read().splitlines())
    f.close()

    print("Loading database")
    db_list = load_from_file(FILENAME)
    titles = set()
    imghashes = set()
    for (title, imghash, url, date) in db_list:
        titles.add(title)
        imghashes.add(imghash)

    new_listings = []
    for search_url in search_urls:
        print("Querying Craigslist with search url {}".format(search_url))
        date = datetime.date.today().isoformat()
        search_soup = soup_from_url(search_url)
        search_results = parse_results_search_page(search_url, search_soup)

        print("Processing {} results from Craigslist".format(len(search_results)))
        for title, listing_url in search_results:
            try:
                # Check for duplicate title with older listing
                if title in titles:
                    print("Duplicate title")
                    continue

                # Check for duplicate images with older listing
                listing_soup = soup_from_url(listing_url)
                listing_hashes = hash_images_from_listing_page(listing_url, listing_soup)
                listing_hash = hash_hash_list(listing_hashes)
                if listing_hash in imghashes:
                    print("Duplicate images")
                    continue

               	# Check to see if the listing is for september
                if isSeptember(listing_soup.text):
                    print("September listing")
                    continue

                # It's unique!
                db_list.append((title, listing_hash, listing_url, date))
                titles.add(title)
                imghashes.add(listing_hash)
                new_listings.append((title, listing_url))
                print("New unique listing! {} {}".format(title, listing_url))
            except:
                print("Error processing {} {}, skipping".format(title, listing_url))

    if len(new_listings) > 0 and not to_addr is None:
        print("Sending updates by email")
        subject = "{} new listing(s) from your friendly Craigslist scraper".format(len(new_listings))
        body = "New listings!\n\n"
        for title, url in new_listings:
            body = body + "{}\t{}\n".format(title, url)
        send_email("kaufman@mit.edu", to_addr, subject, body)

    print("Writing (potentially) updated db back to file")
    save_to_file(FILENAME, db_list)


def isSeptember(listing_text):
    alpha_num = re.compile('[^a-zA-Z0-9/]+')
    text_alphanum = alpha_num.sub('', str(listing_text)).lower()
    sep_strings = [
        "sep1",
        "sep01",
        "9/1",
        "09/01",
	"september"
    ]
    for sep_string in sep_strings:
        if sep_string in text_alphanum:
            return True
    return False



if len(sys.argv) < 2:
    print("Usage: python scrape.py <craigslist search url>")
    print(sys.argv)
    sys.exit(1)

search_url_file = sys.argv[1]
to_addr = sys.argv[2] if len(sys.argv) > 2 else None

main(search_url_file, to_addr)


