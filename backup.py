#!/usr/bin/env python3

import sqlite3
import sys
import click
import datetime

import discord

client = discord.Client()

global_filename = ''
global_guildid = 0

@click.command()
@click.option('--bot', '-B', default=False, is_flag=True)
@click.option('--token', '-t', default='')
@click.argument('guildid')
@click.argument('filename')
def main(bot, token, guildid, filename):
    global global_guildid, global_filename
    global_guildid = guildid
    global_filename = filename
    if token == '':
        try:
            client.run(open('token.txt','r').read().split('\n')[0], bot=bot)
        except discord.errors.LoginFailure as e:
            print(e, 'Try adding the `--bot` flag.')
    else:
        try:
            client.run(token, bot=bot)
        except discord.errors.LoginFailure as e:
            print(e, 'Try adding the `--bot` flag.')

@client.event
async def on_ready():
    print("Backup bot logged in.")
    await make_logs()
    await client.logout()
    
async def make_logs():
    database = None
    def scrub(s):
        while "-" in s:
            s = s.replace("-", "")
        return s
    def check_table_exists(tablename):
        dbcur = database.cursor()
        dbcur.execute("""
            SELECT name FROM sqlite_master WHERE type='table' AND name='{0}';
            """.format(str(tablename).replace('\'', '\'\'')))
        if dbcur.fetchone():
            dbcur.close()
            return True

        dbcur.close()
        return False
    
    guild = client.get_guild(int(global_guildid))
    database = sqlite3.connect("{}.sqlite".format(global_filename))
    
    cursor = database.cursor()
    if check_table_exists('channels'):
        cursor.execute("""DROP TABLE channels""")
    cursor.execute("""CREATE TABLE channels(cid INTEGER, position INTEGER, name TEXT, topic TEXT, type TEXT)""")
    cursor.close()
    database.commit()
    for channel in guild.channels:
        if isinstance(channel, discord.TextChannel):
            cursor = database.cursor()
            cursor.execute(
                """INSERT INTO channels(cid, position, name, topic, type) VALUES (?, ?, ?, ?, ?)""",
                (channel.id, channel.position, channel.name, str(channel.topic), 'discord.TextChannel')
            )
            cursor.close()
            database.commit()
            if channel.permissions_for(guild.get_member(client.user.id)).read_message_history:
                sys.stdout.write("Logging {0}: Counting".format(channel.name))
                sys.stdout.flush()
                cursor = database.cursor()
                after = datetime.datetime(2015,3,1)
                if check_table_exists(channel.id):
                    cursor.execute("""SELECT timestamp FROM `{0}` ORDER BY timestamp DESC LIMIT 1""".format(channel.id))
                    try:
                        after = datetime.datetime.strptime(cursor.fetchone()[0], "%Y-%m-%d %H:%M:%S.%f")
                    except TypeError:
                        pass
                else:
                    cursor.execute("""CREATE TABLE `{0}`(uid INTEGER, mid INTEGER, message TEXT, files TEXT, timestamp TEXT)""".format(channel.id))
                database.commit()
                count = 0
                msg_c = 0
                async for message in channel.history(limit=None,after=after):
                    msg_c += 1
                print("\rLogging {0}: 0/{1}         ".format(channel.name, msg_c), end="")
                async for message in channel.history(limit=None,after=after):
                    at = ",".join([i.url for i in message.attachments])
                    cursor.execute("""
                        INSERT INTO `{0}`(uid, mid, message, files, timestamp)
                        VALUES (?, ?, ?, ?, ?)""".format(channel.id), (message.author.id, message.id, message.content, at, message.created_at))
                    count += 1
                    if count % 200 == 0:
                        database.commit()
                        print("\rLogging {0}: {1}/{2}".format(channel.name, count, msg_c), end="")
                database.commit()
                print("\rLogging {0}: [DONE]            ".format(channel.name))
        elif isinstance(channel, discord.VoiceChannel):
            cursor = database.cursor()
            cursor.execute(
                """INSERT INTO channels(cid, position, name, topic, type) VALUES (?, ?, ?, ?, ?)""",
                (channel.id, channel.position, channel.name, '', 'discord.VoiceChannel')
            )
            cursor.close()
            database.commit()
    print("LOGS FINISHED")

if __name__ == '__main__':
    #bot=False may have to be changed if you are using a bot
    #client.run(open('token.txt','r').read().split('\n')[0], bot=False)
    main()
