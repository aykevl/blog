#!/usr/bin/python3

# Small script to convert my old blog database to the newer Markdown based blog.

from datetime import datetime
import json
import os
import sqlite3

def main():
    con = sqlite3.connect('blog.sqlite3')
    cur = con.cursor()
    for (text, name, title, published, modified, summary) in cur.execute('SELECT text, name, title, published, modified, summary FROM pages ORDER BY published, modified'):
        print(published, modified, name, title)
        text = text.replace('\r\n', '\n').strip() + '\n'

        f = open('converted/%s.md' % name, 'w')
        f.write('---\n')
        f.write('title: %s\n' % json.dumps(title))
        if published:
            f.write('date: %s\n' % datetime.fromtimestamp(published).strftime('%Y-%m-%d'))
        else:
            f.write('draft: true\n')
        f.write('lastmod: %s\n' % datetime.fromtimestamp(modified).strftime('%Y-%m-%d'))
        f.write('summary: %s\n' % json.dumps(summary))
        f.write('---\n')
        f.write(text)

if __name__ == '__main__':
    main()
