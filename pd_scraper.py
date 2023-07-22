import scrapy
import os
import random
import hashlib
import time
import zipfile

from scrapy import signals
from scrapy.downloadermiddlewares.useragent import UserAgentMiddleware
from scrapy.utils.project import get_project_settings
from fake_useragent import UserAgentMiddleware as RandomUserAgentMiddleware

import random
import time

class RandomUserAgentMiddleware(UserAgentMiddleware):
    def __init__(self, user_agent=''):
        self.user_agent = user_agent

    def process_request(self, request, spider):
        ua = random.choice(self.user_agent_list)
        if ua:
            request.headers.setdefault('User-Agent', ua)
            spider.logger.debug(f'User-Agent: {ua}')

    # Define a list of user agents to choose from
    user_agent_list = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:54.0) Gecko/20100101 Firefox/54.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36 Edg/89.0.774.48',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.96 Safari/537.36',
    ]


class RandomDelayMiddleware(object):
    def __init__(self, delay):
        self.delay = delay

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings.getfloat('DOWNLOAD_DELAY'))

    def process_request(self, request, spider):
        delay = random.uniform(1.5*self.delay, 2.5*self.delay)
        time.sleep(delay)
        spider.logger.debug(f"RandomDelayMiddleware: Sleeping for {delay:.2f} seconds")


class PdSpider(scrapy.Spider):
    name = "pd"
    allowed_domains = [
        "aspress.co.uk",
        "puredata.info",
        "patchstorage.com",
        "martin-brinkmann.de",
        "oscilloscopemusic.com",
        "pdpatchrepo.info",
    ]
    start_urls = [
        "http://aspress.co.uk/sd/",
        "https://puredata.info/community/member-downloads/patches",
        "https://patchstorage.com/platform/pd-vanilla/",
        "http://www.martin-brinkmann.de/pd-patches.html",
        "https://oscilloscopemusic.com/software/puredata/",
        "https://forum.pdpatchrepo.info/category/2/patch",
    ]
    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "CONCURRENT_REQUESTS": 2,
        "DOWNLOAD_DELAY": 15,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 5,
        "AUTOTHROTTLE_MAX_DELAY": 60,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1,
        "COOKIES_ENABLED": True,
        "DOWNLOADER_MIDDLEWARES": {
            'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
            'random_useragent.RandomUserAgentMiddleware': 400,
            'scrapy_rotating_proxies.middlewares.RotatingProxyMiddleware': 610,
            'scrapy.downloadermiddlewares.retry.RetryMiddleware': 90,
            'scrapy.downloadermiddlewares.downloadtimeout.DownloadTimeoutMiddleware': 350,
            'scrapy.downloadermiddlewares.redirect.RedirectMiddleware': 700,
            'scrapy.downloadermiddlewares.cookies.CookiesMiddleware': 800,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
            'scrapy.downloadermiddlewares.httpcache.HttpCacheMiddleware': 900,
            'random_delay.RandomDelayMiddleware': 999
        },
        "ROTATING_PROXY_LIST_PATH": "/path/to/proxies.txt",
        "HTTPCACHE_ENABLED": True,
        "HTTPCACHE_EXPIRATION_SECS": 86400,
        "HTTPCACHE_DIR": 'httpcache',
        "HTTPCACHE_IGNORE_HTTP_CODES": [],
        "HTTPCACHE_STORAGE": 'scrapy.extensions.httpcache.FilesystemCacheStorage',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.save_directory = "/Users/macuser/Documents/GitHub/PureDataGPT/TrainingData"

    # Define a function to generate a random wait time between 2 and 6 seconds
    def get_wait_time(self):
        return random.uniform(2, 6)

    # Define a function to generate a unique filename based on the URL
    def get_filename(self, url):
        return hashlib.sha256(url.encode()).hexdigest() + ".pd"

    def start_requests(self):
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            for url in self.start_urls:
                yield scrapy.Request(url, headers=headers, callback=self.parse)


    # Define the entry point to start parsing links
    def parse(self, response):
        for link in response.css("a::attr(href)").getall():
            if link.endswith(".pd") or link.endswith(".zip"):
                download_url = response.urljoin(link)
                yield scrapy.Request(download_url, callback=self.download_file)
            else:
                yield response.follow(link, callback=self.parse_links)

    # Define a function to download a file
    def download_file(self, response):
        # Set the download path
        download_path = os.path.join(self.save_directory, self.get_filename(response.url))

        # Download the file
        request = scrapy.Request(response.url, callback=self.save_file)
        request.meta["download_path"] = download_path
        yield request

    # Define a function to save the file
    def save_file(self, response):
        download_path = response.meta["download_path"]
        if response.status == 200:
            with open(download_path, "wb") as f:
                f.write(response.body)
            # Check for zip file and extract pd files
            if download_path.endswith(".zip"):
                with zipfile.ZipFile(download_path, "r") as zip_ref:
                    for filename in zip_ref.namelist():
                        if filename.endswith(".pd"):
                            zip_ref.extract(filename, os.path.dirname(download_path))
                            self.logger.info(f"Downloaded: {filename}")
            else:
                self.logger.info(f"Downloaded: {download_path}")
        else:
            self.logger.warning(f"Failed to download: {response.url}")


