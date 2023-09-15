# UIUC Term Scraping Code

Code to scrape all UIUC courses offered in all semesters from FA23 to FA04. Includes Fall, Winter, Spring, and Summer semesters. HIGHLY recommended that you use the SQLite of existing scraped data than scraping data yourself (it'll take >500 API calls, and it's not the fastest API.)

The scraped data is in `offerings.db`. The SQLite table schema is:

```sql
offerings(enc_term integer, subj text, course text)
```

See the Python code for encoding/decoding the `enc_term` field.

## Installation

```sh
pip3 install -r ./requirements.txt
```

## Usage

- ⚠️ `python3 extract_api.py -get`: Scrape the API starting from the existing bookmark & existing scraped data.
- ⚠️ `python3 extract_api.py -f`: Scrape the API starting from scratch (nuke existing bookmark & existing scraped data.)
- `python3 extract_api.py -json`: Export the scraped SQLite to a JSON
- `python3 extract_api.py`: Run demo code for how you would access an existing SQLite db of scraped data.


⚠️ ** Warning ** ⚠️: These commands can fetch terms all the way from the current term to FA'04 by default. This makes a HUGE number of requests! If you need a specific term, you'll have to modify the code: see the `full_exec()` function.

## License

See LICENSES. All licenses are MIT.
