#/*
# * Copyright (C) 2010 Mark Honeychurch
# *
# *
# * This Program is free software; you can redistribute it and/or modify
# * it under the terms of the GNU General Public License as published by
# * the Free Software Foundation; either version 2, or (at your option)
# * any later version.
# *
# * This Program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program; see the file COPYING. If not, write to
# * the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# * http://www.gnu.org/copyleft/gpl.html
# *
# */

import os, sys, urllib, urllib2, htmllib, string, unicodedata, re
import time, urlparse, cgi, md5, sha, xbmcgui, xbmcplugin, xbmcaddon

__addon__ = xbmcaddon.Addon(id = sys.argv[0][9:-1])
localize  = __addon__.getLocalizedString

xbmcplugin.setPluginCategory(int(sys.argv[1]), 'CCTV')

# Multiple servers
# Cycle?
# Montage?

#Show an on-screen message (useful for debugging)
def message (message, title = "Warning"): 
    dialog = xbmcgui.Dialog()
    if message:
        if message <> "":
            dialog.ok(title, message)
        else :
            dialog.ok("Message", "Empty message text")
    else :
        dialog.ok("Message", "No message text")

def getHtmlPage (url, cookie): #Grab an HTML page
    sys.stderr.write("Requesting page: %s" % (url))
    req = urllib2.Request(url)
    if cookie <> "":
        req.add_header('cookie', cookie)
    response = urllib2.urlopen(req)
    doc = response.read()
    cookie = response.headers.get('Set-Cookie') 
    response.close()

    return doc, cookie

#Convert escaped HTML characters back to native unicode, e.g. &gt; 
#to > and &quot; to "
def unescape (s): 
    return (re.sub('&(%s);' % '|'.join(name2codepoint), 
              lambda m: unichr(name2codepoint[m.group(1)]), s))

#Set the default info for folders (1) and videos (0). Most options 
#have been hashed out as they don't show up in the list and are grabbed
#from the media by the player
def defaultInfo (folder = 0): 
    info = dict()
    if folder:
        info["Icon"] = "DefaultFolder.png"
    else :
        info["Icon"] = "DefaultVideo.png"
        info["VideoCodec"] = "mp4v"

    info["Thumb"] = ""

    return info

#Check that all of the list "items" are in the dictionary "info"
def checkDict (info, items): 
    for item in items:
        if info.get(item, "##unlikelyphrase##") == "##unlikelyphrase##":
            sys.stderr.write("Dictionary missing item: %s" % (item))
            return 0
    return 1

#Builds a URL similar to:
# plugin://plugin.video.myaddon/?mode=folder&foldername=Folder+One
# See http://kodi.wiki/view/Audio/Video_plugin_tutorial
def buildUrl(baseUrl, query):
    return baseUrl + '?' + urllib.urlencode(query)

#Add a list item (media file or folder) to the XBMC page
def addListItem (info, total = 0, folder = 0): 
    if checkDict(info, ("Title", "Icon", "Thumb", "FileName")):
        liz = (xbmcgui.ListItem(info["Title"], iconImage = info["Icon"], 
                 thumbnailImage = info["Thumb"]))
        liz.setProperty('fanart_image', os.path.join(sys.path[0], 
                             'fanart.jpg'))
        liz.setInfo(type = "Video", infoLabels = info)

        if not folder:
            liz.setProperty("IsPlayable", "true")

        xbmcplugin.addDirectoryItem(handle = int(sys.argv[1]), 
            url = info["FileName"], listitem = liz, isFolder = folder, 
            totalItems = total)

def calculateAspect (width, height):
    aspect = int(width)/int(height)
    if aspect <= 1.35:
        return "1.33"
    elif aspect <= 1.68:
        return "1.66"
    elif aspect <= 1.80:
        return "1.78"
    elif aspect <= 1.87:
        return "1.85"
    elif aspect <= 2.22:
        return "2.20"
    else :
        return "2.35"

def getUrl (path):
    server = __addon__.getSetting('server').strip("/").strip()
    path = path.strip("/").strip()
    url = "http://%s/%s/" % (server, path)
    return url

def mysqlPassword (str):
    pass1 = sha.new(str).digest()
    pass2 = sha.new(pass1).hexdigest()
    return "*" + pass2.upper()

def createAuthString ():
    authurl = ""
    videoauthurl = ""
    if __addon__.getSetting('auth') == 'true':
        if __addon__.getSetting('hash') == 'true':
            myIP = ""
            if __addon__.getSetting('ip') == 'true':
                if __addon__.getSetting('thisip') == 'true':
                    myIP = xbmc.getIPAddress()
                else :
                    myIP = __addon__.getSetting('otherip')
            nowtime = time.localtime()
            hashtime = ("%s%s%s%s" % (nowtime[3], nowtime[2], 
                            nowtime[1] - 1, nowtime[0] - 1900))
            sys.stderr.write("Time (for hash): %s" % hashtime)
            hashable = ("%s%s%s%s%s" % (__addon__.getSetting('secret'), 
                        __addon__.getSetting('username'), 
                        mysqlPassword(__addon__.getSetting('password')), 
                        myIP, hashtime))
            hash = md5.new(hashable).hexdigest()
            authurl = "&auth=%s" % (hash)
            videoauthurl = authurl
        else :
            authurl = ("&username=%s&password=%s&action=login"
                       "&view=postlogin" 
                          % (__addon__.getSetting('username').strip(), 
                          __addon__.getSetting('password').strip()))
            videoauthurl = ("&user=%s&pass=%s" % 
                                 (__addon__.getSetting('username').strip(), 
                                  __addon__.getSetting('password').strip()))
    return authurl, videoauthurl
 
def listCameras ():
    zmurl = getUrl(__addon__.getSetting('zmurl'))
    cgiurl = getUrl(__addon__.getSetting('cgiurl'))
    authurl, videoauthurl = createAuthString()
    url = "%s?skin=classic%s" % (zmurl, authurl)
    sys.stderr.write("Grabbing URL: %s" % url)
    cookie = ""
    doc, cookie = getHtmlPage (url, cookie)
    match = re.compile('<form name="loginForm"').findall(doc)

    if len(match) > 0:
        sys.stderr.write(localize(30200))
        message(localize(30201), localize(30200))
        __addon__.openSettings(url = sys.argv[0])
        sys.exit()
    else :
        # OK, logged in, now get index.php for camera list
        url = "%s/index.php" % (zmurl)

        doc, cookie = getHtmlPage (url, cookie)  
        match = re.compile(
            "'zmWatch([0-9]+)', 'watch', ([1-9][0-9]+), ([1-9][0-9]+) \); "
            "return\( false \);\">(.*?)</a>").findall(doc)
        if len(match) > 0:
            qualityurl = ("&bitrate=%s&maxfps=%s" % 
                (__addon__.getSetting('bitrate'),
                __addon__.getSetting('fps')))

            for id, width, height, name in match:
                # Add the live view item
                info = defaultInfo ()
                info["Title"] = name + " Live View"
                info["VideoResolution"] = width
                info["Videoaspect"] = calculateAspect(width, height)
                info["FileName"] = ("%snph-zms?monitor=%s&format=avi%s%s" % 
                                    (cgiurl, id, qualityurl, videoauthurl))
                info["Thumb"] = ("%snph-zms?monitor=%s&mode=single%s" % 
                                       (cgiurl, id, videoauthurl))
                addListItem (info, len(match), 0)

                #List events (of any)
                listEvents (id, zmurl, info, doc, name)
        else :
            sys.stderr.write(localize(30202))
            message(localize(30202))

def listEvents (thisCameraId, zmUrl, info, doc, name):
    # Now get index.php for camera events list
    match = re.compile(
        "=([0-9]+)', 'zmEvents', 'events' \); "
        "return\( false \);\">([0-9]+)").findall(doc)

    if len(match) > 0:

        for id, totalEvents in match:
            #Match events for the current camera ID only.
            if id != thisCameraId :
                continue

            # Add the event item to the menu
            info = dict ()
            info["Icon"] = "DefaultFolder.png"
            url = "%s/index.php" % (zmUrl)
            info["FileName"] = ("%s?view=events&page=1" 
                            "&filter[terms][0][attr]=MonitorId"
                            "&filter[terms][0][op]=%%3D"
                            "&filter[terms][0][val]=%i"
                            % (url, int (thisCameraId)))
            info["Thumb"] = ""

            info["Title"] = "%s Events (%i)" % (name, int (totalEvents))

            # Add the events view item
            addListItem (info, len(match), 0)
            break
    else : #this is not an error since some cameras may have no events
        sys.stderr.write(localize(30203))

################
# Main program #
################
baseUrl = sys.argv[0]
addonHandle = int(sys.argv[1])
queryStr = sys.argv[2]
args = urlparse.parse_qs(queryStr[1:])
queryMode = args.get('mode', None)

if queryMode is None :
    listCameras()

    xbmcplugin.setContent(addonHandle, 'movies')

    xbmcplugin.addSortMethod(handle = addonHandle, 
         sortMethod = xbmcplugin.SORT_METHOD_UNSORTED)

    xbmcplugin.addSortMethod(handle = addonHandle, 
         sortMethod = xbmcplugin.SORT_METHOD_LABEL)

    xbmcplugin.endOfDirectory(addonHandle)

elif queryMode[0] == 'folder' :
    sys.stderr.write ("Second baseUrl " + baseUrl)
    sys.stderr.write ("Second query " + queryStr)

