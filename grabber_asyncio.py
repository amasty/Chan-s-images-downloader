import os
import re
import logging
import argparse
import datetime
import asyncio
import aiohttp
from lxml import html


class ImageGrabber(object):
    def __init__(self):
        self.downloaded = 0
        self.total = 0
        self.start_time = datetime.datetime.now()

    async def fetch_page(self, client, url):
        async with client.get(url) as response:
            assert response.status == 200
            source_page = await response.read()
        return source_page.decode()

    def find_images(self, domain, source_page, images_ext):
        tree = html.fromstring(source_page)
        links = tree.xpath('.//a[@target="_blank"]')

        for link in links:
            src = link.attrib['href']
            if src.endswith(images_ext):
                self.total += 1
                url = domain + src
                name = src.split('/')[-1]
                yield url, name

    def start_download(self, thread_url, domain, images_ext, dir, max_threads=15):
        logging.info('start download')
        pool = []
        loop = asyncio.get_event_loop()
        client = aiohttp.ClientSession(loop=loop)

        source_page = loop.run_until_complete(self.fetch_page(client, thread_url))

        for image_url, image_name in self.find_images(domain, source_page, images_ext):
            pool.append(self.download_image(client, image_url, image_name, dir, max_threads))

            if len(pool) == max_threads:
                loop.run_until_complete(asyncio.wait(pool))
                pool = []

        if len(pool):
                loop.run_until_complete(asyncio.wait(pool))

        logging.info('download finished for {0}'.format(datetime.datetime.now()-self.start_time))
        logging.info('downloaded images: {0}/{1}'.format(self.downloaded, self.total))
        client.close()
        loop.close()
        exit('All done')

    @asyncio.coroutine
    def download_image(self, client, url, image_name, dir, max_threads):
        logging.debug('getting image: {0}'.format(image_name))
        try:
            res = yield from client.get(url)
        except Exception as e:
            raise Exception('cant get image {0}'.format(image_name))
        else:
            self.downloaded += 1
            with open(os.path.join(dir, image_name), 'wb') as f:
                logging.debug('saving image: {0}'.format(image_name))
                img = yield from res.read()
                f.write(img)

    def grabb(self, url, images_ext, dir=None):
        if not re.search('http', url):
            raise Exception('url should start with http/https')

        if dir is None:
            base_dir = os.path.dirname(__file__)
            dir = os.path.join(base_dir, url.split('/')[-1].split('.')[0])

        os.makedirs(dir, exist_ok=True)

        url_split = url.split('/')
        domain = '{0}//{1}/'.format(url_split[0], url_split[2])

        self.start_download(url, domain, images_ext, dir)


if __name__ == '__main__':
    images_ext = ('webm', 'jpeg', 'jpg', 'png', 'gif')

    argparser = argparse.ArgumentParser()
    argparser.add_argument("--url", help="Thread's url")
    argparser.add_argument("--dir", help="Path to dir for images")
    argparser.add_argument("--debug")
    args = argparser.parse_args()
    if not args.url:
        raise exit('Use --help for args')

    level = 20
    if args.debug:
        level = 10
    logging.basicConfig(level = level)

    imagegrabber = ImageGrabber()
    imagegrabber.grabb(args.url, images_ext, args.dir)
