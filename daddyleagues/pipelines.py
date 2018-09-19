# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
import sqlite3
import requests
import imgkit
from scrapy.exceptions import NotConfigured
from scrapy.exceptions import DropItem



class DaddyleaguesPipeline(object):

    def __init__(self, chat_id=None, template=None):
        if chat_id is None or template is None:
            raise NotConfigured()
        else:
            self.chat_id = chat_id
            self.template = template

    def open_spider(self, spider):
        self.conn = sqlite3.connect('daddyleagues.db')

    def close_spider(self, spider):
        self.conn.close()

    def process_item(self, item, spider):
        # import pdb; pdb.set_trace()
        if len(item) == 0:
            raise DropItem()
        c = self.conn.cursor()
        #c.execute('drop table  team')
        c.execute('CREATE TABLE IF NOT EXISTS  team (id, name)')
        new_item = False
        team1 = c.execute('select id, name from team where name = ?',
                          (item['team1'],)).fetchone()
        team2 = c.execute('select id, name from team where name = ?',
                          (item['team2'],)).fetchone()
        if team1 is not None and team2 is not None:
            persist = c.execute("""
select week from games where week = ? and team1_id = ? and team2_id = ? and sended = ?
            """, (item['week'], team1[1], team2[1], 1)).fetchone()
            if persist is None:
                c.execute('insert into games values (?, ?, ?, ?, ?, ?, ?)',
                          (item['week'], team1[1], item['score1'],
                           item['score2'], team2[1], item['vs'], 0))
                new_item = True

        else:
            if team1 is None:
                c.execute('insert into team values (null, ?)', (item['team1'],))
                team1 = c.execute('select id, name from team where name = ?',
                                  (item['team1'],)).fetchone()
            if team2 is None:
                c.execute('insert into team values (null, ?)', (item['team2'],))
                team2 = c.execute('select id, name from team where name = ?',
                                  (item['team2'],)).fetchone()
            c.execute('insert into games values (?, ?, ?, ?, ?, ?, ?)',
                      (item['week'], team1[1], item['score1'],
                       item['score2'], team2[1], item['vs'], 0))
            new_item = True
        if new_item:
            config = imgkit.config(wkhtmltoimage='/usr/local/bin/wkhtmltoimage')
            #config = imgkit.config(wkhtmltoimage='/usr/bin/wkhtmltoimage')

            options = {
                'crop-x': 3450,
                'crop-y': 200,
                'quality': 100,
                'height': 600,
                'width': 4400
            }
            imgkit.from_url(item['vs'], 'gameRecap.png', options=options, config=config)

            try:

                r = requests.post("https://api.telegram.org/<key>/sendMessage",
                                  data={
                                      u"chat_id": self.chat_id,
                                      u"text": self.template.format(
                                          item['week']+1,
                                          team1[1],
                                          item['score1'],
                                          item['vs'],
                                          item['score2'],
                                          team2[1]),
                                      u"parse_mode": u"Markdown"})

                js = r.json()
                if u"ok" in js and js["ok"]:
                    url = "https://api.telegram.org/<key>/sendPhoto";
                    files = {'photo': open('gameRecap.png', 'rb')}
                    data = {'chat_id' : self.chat_id}
                    requests.post(url, files=files, data=data)
                    c.execute('update games set sended = 1 where week = ? and team1_id = ? and team2_id = ?',
                              (item['week'], team1[1], team2[1]))
                    self.conn.commit()

                    #    requests.post("https://api.telegram.org/<>/sendMessage",
                #                  data={
                #                      u"chat_id": -1001120201652,
                #                      u"text": self.template.format(
                #                          team1[1],
                #                          item['score1'],
                #                          item['vs'],
                #                          item['score2'],
                #                          team2[1]),
                #                      u"parse_mode": u"Markdown"})
            except:
                self.conn.rollback()
        return item

    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        return cls(**settings.getdict('TELEGRAM'))
