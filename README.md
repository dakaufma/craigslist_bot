Usage: python scraper.py <craigslist search url>


# Description

Parses a craigslist search url and stores results in a file. Unique entries are
determined by title and the hash of their images (both must be unique). Each
run outputs new unique entries and updates the database of old entries.


# Store in JSON:
[(title, imghash, url, date)]


# On update, create:
set(title)
set(imghash)

If the titles don't match then download and hash the images
If it's new, print out it's url/date (later: option for sending an email)
When done, rewrite the file


