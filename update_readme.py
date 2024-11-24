import os
import feedparser

RSS_URL = os.getenv('RSS_URL')
README_PATH = os.getenv('READ_ME_PATH')

START_MARKER = '<!-- BLOG-POST-LIST:START -->'
END_MARKER = '<!-- BLOG-POST-LIST:END -->'

def fetch_blog_posts(rss_url, limit=5):
    feed = feedparser.parse(rss_url)
    posts = []
    for entry in feed.entries[:limit]:
        title = entry.title
        link = entry.link
        posts.append(f'- [{title}]({link})')
    return '\n'.join(posts)

def update_readme(readme_path, new_content):
    with open(readme_path, 'r', encoding='utf-8') as file:
        content = file.read()

    start_index = content.find(START_MARKER)
    end_index = content.find(END_MARKER)

    if start_index == -1 or end_index == -1:
        raise Exception("Start or end marker not found in README.md")

    new_section = f"{START_MARKER}\n{new_content}\n{END_MARKER}"
    updated_content = content[:start_index] + new_section + content[end_index:]

    with open(readme_path, 'w', encoding='utf-8') as file:
        file.write(updated_content)

def main():
    try:
        posts = fetch_blog_posts(RSS_URL)
        update_readme(README_PATH, posts)
        print("README.md updated successfully.")
    except Exception as e:
        print(f"Error updating README.md: {e}")
        exit(1)

if __name__ == "__main__":
    main()
