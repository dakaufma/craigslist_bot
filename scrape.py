from bs4 import BeautifulSoup
import urllib.request
import urllib.parse
import sys
import hashlib
import json
import datetime

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
        return ['no hashes']
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


def main(search_url):
    print("Loading database")
    db_list = load_from_file(FILENAME)
    titles = set()
    imghashes = set()
    for (title, imghash, url, date) in db_list:
        titles.add(title)
        imghashes.add(imghash)

    print("Querying Craigslist")
    date = datetime.date.today().isoformat()
    search_soup = soup_from_url(search_url)
    search_results = parse_results_search_page(search_url, search_soup)

    print("Processing {} results from Craigslist".format(len(search_results)))
    for title, listing_url in search_results:
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

        # It's unique!
        db_list.append((title, listing_hash, listing_url, date))
        titles.add(title)
        imghashes.add(listing_hash)
        print("New unique listing! {} {}".format(title, listing_url))

    print("Writing (potentially) updated db back to file")
    save_to_file(FILENAME, db_list)


if len(sys.argv) != 2:
    print("Usage: python scrape.py <craigslist search url>")
    print(sys.argv)
    sys.exit(1)

search_url = sys.argv[1]
main(search_url)


