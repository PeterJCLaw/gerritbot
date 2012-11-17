#!/usr/bin/python

'''
    Copyright 2010, The Android Open Source Project

    Licensed under the Apache License, Version 2.0 (the "License"); 
    you may not use this file except in compliance with the License. 
    You may obtain a copy of the License at 

        http://www.apache.org/licenses/LICENSE-2.0 

    Unless required by applicable law or agreed to in writing, software 
    distributed under the License is distributed on an "AS IS" BASIS, 
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
    See the License for the specific language governing permissions and 
    limitations under the License.
'''

# bridge script to irc channel from gerrit livestream
# written by jeff sharkey and kenny root


import re, os, sys, ConfigParser
import socket, paramiko
import threading, time, random
import simplejson
import irclib
import subprocess

# config file section titles
GERRIT = "GerritServer"
IRC = "IrcServer"
BRANCHES = "Branches"
GENERAL = "General"

config = ConfigParser.ConfigParser()
config.read("gerritbot.conf")


NONE, BLACK, NAVY, GREEN, RED, BROWN, PURPLE, OLIVE, YELLOW, LIME, TEAL, AQUA, BLUE, PINK, GREY, SILVER, WHITE = range(17)

def color(fg=None, bg=None, bold=False, underline=False):
    # generate sequence for irc formatting
    result = "\x0f"
    if not fg is None: result += "\x03%d" % (fg)
    if not bg is None: result += ",%s" % (bg)
    if bold: result += "\x02"
    if underline: result += "\x1f"
    return result

branch_colors = {}
branch_ignore = []
for name, value in config.items(BRANCHES):
    if value == "IGNORE":
        branch_ignore.append(name)
    else:
        branch_colors[name] = color(globals()[value])



def shorten_project(project):
    # shorten long project names by omitting middle
    reinner = re.compile('^([^/]+)/(.+?)/([^/]+)$')
    match = reinner.match(project)
    if match is None: return project

    first, middle, last = match.groups()
    if len(middle) < 16: return project
    return "%s/../%s" % (first, last)

def trigger(event):
    if event["type"] == "comment-added":
        comment_added(event)
    elif event["type"] == "change-merged":
        change_merged(event)
    elif event["type"] == "patchset-created":
        patchset_created(event)
    else:
        pass

class GerritThread(threading.Thread):
    def __init__(self, config):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.config = config

    def run(self):
        while True:
            self.run_internal()
            print self, "sleeping and wrapping around"
            time.sleep(5)

    def run_internal(self):
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        host = self.config.get(GERRIT, "host")
        port = self.config.getint(GERRIT, "port")
        user = self.config.get(GERRIT, "user")
        privkey = self.config.get(GERRIT, "privkey")

        try:
            print self, "connecting to", host
            client.connect(host, port, user, key_filename=privkey, timeout=60)
            client.get_transport().set_keepalive(60)

            stdin, stdout, stderr = client.exec_command("gerrit stream-events")
            for line in stdout:
                print line
                try:
                    event = simplejson.loads(line)
                    trigger(event)
                except ValueError:
                    pass
            client.close()
        except Exception, e:
            print self, "unexpected", e

def username_from_person(person):
    username = re.compile(r'@.+').sub("", person["email"])
    return username

def project_from_change(change):
    project = re.compile(r'^platform/').sub("", change["project"])
    return project

def link_from_change(change):
    link = config.get(GENERAL, "shortlink") % (change["number"])
    return link

def change_merged(event):
    change = event["change"]

    branch = change["branch"]
    if branch in branch_ignore: return

    project = project_from_change(change)
    owner = username_from_person(change["owner"])
    subject = change["subject"]
    link = link_from_change(change)

    project = shorten_project(project)
    branch_color = branch_colors.get(branch, color(GREY))

    msg_branch = branch_color + branch + color(GREY)
    msg_project = color(TEAL,bold=True) + project + color(GREY)
    msg_owner = color(GREEN) + owner + color(GREY)
    msg_subject = color() + subject + color(GREY)
    msg_link = color(NAVY, underline=True) + link + color(GREY)

    message = "%s | %s | %s > %s %s" % (msg_branch, msg_project, msg_owner, msg_subject, msg_link)
    subprocess.call(['./pipebot/say', message])

def comment_added(event):
    change = event["change"]

    branch = change["branch"]
    if branch in branch_ignore: return

    author = event["author"]

    project = project_from_change(change)
    author = username_from_person(author)
    subject = change["subject"]
    link = link_from_change(change)

    project = shorten_project(project)
    branch_color = branch_colors.get(branch, color(GREY))

    msg_author = color(GREEN) + author + color(BLACK)
    msg_project = color(TEAL,bold=True) + project + color(GREY)
    msg_branch = branch_color + branch + color(GREY)
    msg_subject = color() + subject + color(GREY)
    msg_link = color(NAVY, underline=True) + link + color(GREY)

    message = "%s reviewed %s | %s : %s %s" % (msg_author, msg_project, msg_branch, msg_subject, msg_link)
    subprocess.call(['./pipebot/say', message])

def patchset_created(event):
    change = event["change"]

    branch = change["branch"]
    if branch in branch_ignore: return

    project = project_from_change(change)
    uploader = username_from_person(event["uploader"])
    owner = username_from_person(change["owner"])
    subject = change["subject"]
    link = link_from_change(change)

    project = shorten_project(project)
    branch_color = branch_colors.get(branch, color(GREY))

    msg_owner = color(GREEN) + uploader + color(BLACK)
    if uploader != owner:
        msg_owner += ' (for ' + color(GREEN) + owner + color(BLACK) + ')'
    msg_project = color(TEAL,bold=True) + project + color(GREY)
    msg_branch = branch_color + branch + color(GREY)
    msg_subject = color() + subject + color(GREY)
    msg_link = color(NAVY, underline=True) + link + color(GREY)

    message = "%s submitted %s | %s : %s %s" % (msg_owner, msg_project, msg_branch, msg_subject, msg_link)
    subprocess.call(['./pipebot/say', message])

if __name__ == '__main__':
    gerrit = GerritThread(config); gerrit.start()

    while True:
        try:
            line = sys.stdin.readline()
        except KeyboardInterrupt:
            break
