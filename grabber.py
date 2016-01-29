import os
import re
import logging
import argparse
from tornado import ioloop, gen, httpclient
from lxml import html


class ImageGrabber(object):
    def __init__(self):
        self.downloaded = 0
        self.total = 0

    def get_source_thread(self, url):
        try:
            response = httpclient.HTTPClient().fetch(url)
        except:
            raise BaseException('please check the url')

        source_page = response.body.decode()

        return source_page

    def find_images(self, source_page, images_ext):
        tree = html.fromstring(source_page)
        links = tree.xpath('.//a[@target="_blank"]')

        for link in links:
            src = link.attrib['href']
            ext = src.split('.')[-1]
            if ext in images_ext:
                self.total += 1
                yield src

    @gen.coroutine
    def start_download(self, domain, source_page, images_ext, dir, full_path=False, max_threads=15):
        logging.info('start download')
        pool = []
        for image in self.find_images(source_page, images_ext):
            pool.append(self.download_image(image, domain, dir, full_path, max_threads))

            if len(pool) > max_threads - 1:
                yield pool
                pool = []

        if len(pool):
                yield pool

        logging.info('download finished')
        logging.info('downloaded {0} images / {1}'.format(self.count, self.total))
        exit('All done')

    @gen.coroutine
    def download_image(self, image, domain, dir, full_path=False, max_threads=15):
        url = domain + image

        if not full_path:
            base_dir = os.path.dirname(__file__)

        dir = os.path.join(base_dir, dir)
        os.makedirs(dir, exist_ok=True)

        name = image.split('/')[-1]

        logging.info('getting image: {0}'.format(image))

        try:
            res = yield httpclient.AsyncHTTPClient(max_clients=max_threads).fetch(
                            httpclient.HTTPRequest(url, request_timeout=100, connect_timeout=50), raise_error=True
                        )

        except Exception as e:
            raise BaseException('cant get image {0}'.format(image))

        if res.code == 200:
            self.downloaded += 1
            with open(os.path.join(dir, name), 'wb') as f:
                logging.info('saving image: {0}'.format(image))
                f.write(res.body)

    def grabb(self, url, images_ext, dir=None):
        if not re.search('http', url):
            raise BaseException('url should start with http/https')

        if dir is None:
            dir = url.split('/')[-1].split('.')[0]
            full_path = False
        else:
            full_path = True

        url_split = url.split('/')
        domain = '{0}//{1}/'.format(url_split[0], url_split[2])

        source_page = self.get_source_thread(url)
        self.start_download(domain, source_page, images_ext, dir, full_path)


if __name__ == '__main__':
    images_ext = ['webm', 'jpeg', 'jpg', 'png', 'gif']

    argparser = argparse.ArgumentParser()
    argparser.add_argument("--url", help="Thread's url")
    argparser.add_argument("--dir", help="Path to dir for images")
    args = argparser.parse_args()
    if not args.url:
        raise BaseException('Use --help for args')

    logging.basicConfig(level = logging.DEBUG)

    imagegrabber = ImageGrabber()
    imagegrabber.grabb(args.url, images_ext, args.dir)

    ioloop.IOLoop.current().start()
