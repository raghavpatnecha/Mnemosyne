import re
import requests
from bs4 import BeautifulSoup
from firecrawl import FirecrawlApp
from config import Config
import re

firecrawl_app = FirecrawlApp(Config.FIRECRAWL.API_KEY)

def extract_data_from_url(url: str):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract the title of the page
    title = soup.title.string if soup.title else "No title found"
    title = re.sub(r'\s*-\s*Freedium$', '', title).strip()

    # Initialize containers for content, images, and code blocks
    article_content = ""
    images = []
    code_blocks = []

    # Find content between the markers "< Go to the original" and "Reporting a Problem"
    start_marker = "< Go to the original"
    end_marker = "Reporting a Problem"

    page_text = soup.get_text()
    start_index = page_text.find(start_marker)
    end_index = page_text.find(end_marker)

    if start_index != -1 and end_index != -1:
        article_content = page_text[start_index + len(start_marker):end_index].strip()

    # Extract content, images, and code blocks using BeautifulSoup
    for tag in soup.find_all(True):  # Find all tags
        if tag.name == 'img':
            src = tag.get('src')
            if src and re.search(r'\.(jpeg|jpg|png|gif)$', src, re.IGNORECASE):
                # Clean and construct URL if necessary
                cleaned_url = re.sub(r'/resize:[^/]+/', '/', src)
                images.append(cleaned_url)

        elif tag.name == 'pre' or tag.name == 'code':
            code_blocks.append(tag.get_text())

    # Remove code blocks from article content
    for code in code_blocks:
        article_content = article_content.replace(code, "")

    return title, article_content, images, code_blocks


def extract_data_from_firecrawl(url: str):
    scrape_status = firecrawl_app.scrape_url(
        url,
        params={'formats': ['markdown']}
    )
    mdex = MarkdownExtractor(scrape_status['markdown'])
    md_dict = mdex.extract_all()
    for k, v in scrape_status['metadata'].items(): md_dict[k] = v
    md_dict['content'] = scrape_status['markdown']
    return md_dict


def divide_text_into_chunks(text, limit=1000):
    """
    Divide the given text into chunks of approximately 'limit' characters.

    Args:
        text (str): The text to divide into chunks.
        limit (int): The maximum number of characters per chunk.

    Returns:
        list: A list of text chunks.
    """

    def chunker(contexts: list):
        chunks = []
        all_contexts = ' '.join(contexts).split('.')
        chunk = []
        for context in all_contexts:
            chunk.append(context)
            if len(chunk) >= 3 and len('.'.join(chunk)) > limit:
                # surpassed limit so add to chunks and reset
                chunks.append('.'.join(chunk).strip() + '.')
                # add some overlap between passages
                chunk = chunk[-2:]
        # if we finish and still have a chunk, add it
        if chunk:
            chunks.append('.'.join(chunk).strip() + '.')
        return chunks

    # Split text into a list based on paragraphs or new lines
    contexts = text.split('\n\n')  # Assuming paragraphs are separated by double new lines
    return chunker(contexts)


class MarkdownExtractor:
    def __init__(self, markdown_string):
        self.markdown_string = markdown_string

    def extract_code_blocks(self):
        """
        Extracts code blocks wrapped in triple backticks from markdown.
        """
        code_block_pattern = r'```(.*?)```'
        code_blocks = re.findall(code_block_pattern, self.markdown_string, re.DOTALL)
        return code_blocks

    def extract_images(self):
        """
        Extracts image URLs from markdown.
        Markdown image format: ![alt_text](image_url)
        """
        image_pattern = r'!\[.*?\]\((.*?)\)'
        images = re.findall(image_pattern, self.markdown_string)
        res = []
        for image in images:
            if image and re.search(r'\.(jpeg|jpg|png|gif)$', image, re.IGNORECASE):
                cleaned_url = re.sub(r'/resize:[^/]+/', '/', image)
                res.append(cleaned_url)
        return res

    def extract_links(self):
        link_pattern = r'\[.*?\]\((?!.*\.(?:jpeg|jpg|png|gif))(?!.*---)(?!.*miro\.medium).*?\)'
        all_links = re.findall(link_pattern, self.markdown_string)
        return all_links

    def is_valid_link(self, url):
        """Checks if the link is valid by making a GET request."""
        try:
            response = requests.head(url, allow_redirects=True)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def extract_all(self):
        """
        Extracts all components: code blocks, links, and images.
        """
        code_blocks = self.extract_code_blocks()
        images = self.extract_images()
        links = self.extract_links()
        return {
            'code_blocks': code_blocks,
            'images': images,
            'links': links
        }