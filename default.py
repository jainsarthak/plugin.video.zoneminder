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

import os, sys, urllib, urllib2, re
import time, urlparse, md5, sha, xbmcgui, xbmcplugin, xbmcaddon

REMOTE_DBG = False

# append pydev remote debugger. 
# Ref. http://kodi.wiki/view/HOW-TO:Debug_Python_Scripts_with_Eclipse
if REMOTE_DBG:
    # Make pydev debugger works for auto reload.
    # Note pydevd module need to be copied in XBMC\system\python\Lib\pysrc
    try :
        #import pysrc.pydevd as pydevd 
        import sys
        sys.path.append('full_path_to_pysrc')
        import pydevd
        # stdoutToServer and stderrToServer redirect stdout and stderr 
        # to eclipse console. Copy this line to where you want the
        # debugger to initially stop.
        #pydevd.settrace('localhost', stdoutToServer=True, 
        #                stderrToServer=True)
    except ImportError:
        sys.stderr.write("Error: " +
            "You must add org.python.pydev.debug.pysrc to your PYTHONPATH.")
        sys.exit(1)
       

__addon__ = xbmcaddon.Addon(id = sys.argv[0][9:-1])
localize  = __addon__.getLocalizedString
baseUrl = sys.argv[0]

xbmcplugin.setPluginCategory(int(sys.argv[1]), 'CCTV')

# Multiple servers
# Cycle?
# Montage?

#Show an on-screen message (useful for debugging)
def showMessage (message, title = "Warning"): 
    dialog = xbmcgui.Dialog()
    if message:
        if message <> "":
            dialog.ok(title, message)
        else :
            dialog.ok("Message", "Empty message text")
    else :
        dialog.ok("Message", "No message text")

def getHtmlPage (url, cookie): #Grab an HTML page
    sys.stdout.write("Requesting page: %s" % (url))
    req = urllib2.Request(url)
    if cookie <> "":
        req.add_header('cookie', cookie)
    response = urllib2.urlopen(req)
    doc = response.read()
    cookie = response.headers.get('Set-Cookie') 
    response.close()

    return doc, cookie

#Set the default info for folders (1) and videos (0). Most options 
#have been hashed out as they don't show up in the list and are grabbed
#from the media by the player
def defaultInfo (folder = False): 
    info = dict()
    if folder:
        info["Icon"] = "DefaultFolder.png"
    else :
        info["Icon"] = "DefaultVideo.png"
        info["VideoCodec"] = "mp4v"

    info["Thumb"] = ""
    info["CameraId"] = 0

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
def buildUrl(query):
    return baseUrl + '?' + urllib.urlencode(query)

#Add a list item (media file or folder) to the XBMC page
def addListItem (addonHandle, info, total = 0, folder = False): 
    keyTypes = ("Title", "Icon", "Thumb", "FileName", "Mode", "CameraId")
    if checkDict(info, keyTypes):
        liz = xbmcgui.ListItem (info["Title"], iconImage = info["Icon"], 
                 thumbnailImage = info["Thumb"])
        liz.setProperty('fanart_image', os.path.join(sys.path[0], 
                             'fanart.jpg'))
        liz.setInfo(type = "Video", infoLabels = info)

        if not folder:
            liz.setProperty("IsPlayable", "true")

            xbmcplugin.addDirectoryItem(handle = addonHandle, 
                url = info["FileName"], listitem = liz, isFolder = False, 
                totalItems = total)
        else :
            # This is a folder. Pass info to the plugin to allow
            # ease of folder processing if selected.
            url = buildUrl (
                {'Mode' : info["Mode"], 'CameraId' : info["CameraId"]})
            xbmcplugin.addDirectoryItem(handle = addonHandle, 
                url = url, listitem = liz, isFolder = True, 
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
    if __addon__.getSetting('https') == 'true':                
       protocol="https"
    else:         
       protocol="http"
    url = "%s://%s/%s/" % (protocol, server, path)
    return url 

def mysqlPassword (seedPw):
    pass1 = sha.new(seedPw).digest()
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
            sys.stdout.write("Time (for hash): %s" % hashtime)
            hashable = ("%s%s%s%s%s" % (__addon__.getSetting('secret'), 
                        __addon__.getSetting('username'), 
                        mysqlPassword(__addon__.getSetting('password')), 
                        myIP, hashtime))
            newHash = md5.new(hashable).hexdigest()
            authurl = "&auth=%s" % (newHash)
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
 
def listCameras (addonHandle):
    zmurl = getUrl(__addon__.getSetting('zmurl'))
    cgiurl = getUrl(__addon__.getSetting('cgiurl'))
    authurl, videoauthurl = createAuthString()
    url = "%s?skin=classic%s" % (zmurl, authurl)
    sys.stdout.write("ListCameras grabbing URL: %s" % url)
    cookie = ""
    doc, cookie = getHtmlPage (url, cookie)
    match = re.compile('<form name="loginForm"').findall(doc)

    if len(match) > 0:
        sys.stderr.write(localize(30200))
        showMessage(localize(30201), localize(30200))
        __addon__.openSettings(url = sys.argv[0])
        sys.exit()
    else :
        # OK, logged in, now get index.php for camera list
        url = "%s/index.php" % (zmurl)

        doc, cookie = getHtmlPage (url, cookie)  
        match = re.compile(
            "'zmWatch([0-9]+)', 'watch', ([1-9][0-9]+), ([1-9][0-9]+) \); "
            "return\( false \);\">(.*?)</a>").findall(doc)

        NumCameras = len(match)

        if NumCameras > 0:
            qualityurl = ("&bitrate=%s&maxfps=%s" % 
                (__addon__.getSetting('bitrate'),
                __addon__.getSetting('fps')))

            #Add live view for all cameras, plus for any cameras with 
            #events, add a folder for this as well.
            for camId, width, height, name in match:
                # Add the Live View item
                info = defaultInfo ()
                info["Title"] = name + " " + localize (30205)
                info["VideoResolution"] = width
                info["Videoaspect"] = calculateAspect(width, height)
                info["FileName"] = ("%snph-zms?monitor=%s&format=avi%s%s" % 
                                  (cgiurl, camId, qualityurl, videoauthurl))
                info["Thumb"] =    ("%snph-zms?monitor=%s&mode=single%s" % 
                                       (cgiurl, camId, videoauthurl))
                info["Mode"] = "TopLevel" #not currently used
                addListItem (addonHandle, info, len(match), False)

                #List events (of any)
                listEventsFolder (addonHandle, camId, url, info, doc, name)

            #If at least 2 cameras are available, add montage list item. 
            #Note that video setup is done in the configuration menu.
            if NumCameras >= 2:
                # Add the Montage item to the end of the list.
                info = defaultInfo ()
                info["Title"] = localize (30300)
                info["Mode"] = "Montage"
                #TODO Remove hard-coded test code
                info["FileName"] = ("%snph-zms?mode=jpeg&monitor=1&scale=25&"
                   "maxfps=10%s" % (cgiurl, videoauthurl))
                info["Thumb"] = ""
                info["NumCameras"] = NumCameras
                addListItem (addonHandle, info, NumCameras, False)

        else :
            #Display "No cameras found"
            sys.stderr.write(localize(30202))
            showMessage(localize(30202))

def listEventsFolder (addonHandle, thisCameraId, baseUrl, info, doc, name):
    # Now get index.php for camera events list
    match = re.compile(
        "=([0-9]+)', 'zmEvents', 'events' \); "
        "return\( false \);\">([0-9]+)").findall(doc)

    if len(match) > 0:

        for camId, totalEvents in match:
            #Match events for the current camera ID only.
            if camId != thisCameraId :
                continue

            totalEventInt = int (totalEvents)

            #Skip this camera if no events are present
            if totalEventInt < 1 :
                continue

            # Add the event item to the menu
            info = defaultInfo (folder = True)
            info["FileName"] = ""
            info["Thumb"] = ""

            # Add the Events(x) listitem, where x is the number of 
            # recorded events.
            info["Title"] = ("%s %s (%i)" % 
                            (name, localize(30204), totalEventInt))
            info["Mode"] = "EventsList"
            info["CameraId"] = int (thisCameraId)
            info["NumEvents"] = totalEventInt

            # Add the events view item
            addListItem (addonHandle, info, len(match), True)
            break

    else : #this is not an error since cameras may have no events
        sys.stdout.write("No events found for camera %d" 
                        % (int (thisCameraId)))

def listEvents (addonHandle, thisCameraId, numEvents):
    # Now get the camera events list
    zmurl = getUrl(__addon__.getSetting('zmurl'))
    authurl, videoauthurl = createAuthString()
    url = ("%s?%s&view=events&page=%s&filter[terms][0][attr]=MonitorId"
           "&filter[terms][0][op]=%%3D&filter[terms][0][val]=%i"
           % (zmurl, authurl, "all", int (thisCameraId)))

    sys.stdout.write("ListEvents grabbing URL: %s" % url)
    cookie = ""
    doc, cookie = getHtmlPage (url, cookie)  
    cgiurl = getUrl(__addon__.getSetting('cgiurl'))
    qualityurl = ("bitrate=%s&maxfps=%s" % 
        (__addon__.getSetting('bitrate'),
        __addon__.getSetting('fps')))

    eventSearchStr = (
        "'zmEvent', 'event', ([1-9][0-9]+), ([1-9][0-9]+) \); "
        "return\( false \);\">(Event-%s)</a>")
    eventRe = re.compile (eventSearchStr % ("[0-9]+"))
    eventDateRe = re.compile ('<td class="colTime">([0-9/ :]+)</td>')
    eventDurationRe = re.compile ('<td class="colDuration">([0-9(\:|\.)]+)</td>')

    htmlContents = doc.split ('\n')

    sys.stdout.write("Doc contains %d lines" % (len (htmlContents)))

    #Search the HMTL doc line-by-line to read the events and timestamps.
    if len (htmlContents) > 0 :
        for n, line in enumerate (htmlContents, start=0) :
            eventMatch = eventRe.search (line)
            if eventMatch:
                width = eventMatch.group(1)
                height = eventMatch.group(1)
                eventName = eventMatch.group(3)

                #Parse from the eventName
                eventNumRe = re.compile ('Event-([0-9]+)')
                eventNumMatch = eventNumRe.search (eventName)

                #Try to find the date/time stamp for the event. The
                #date/time is 3 lines ahead of the event name.
                dateMatch = eventDateRe.search (htmlContents[n+3])

                #Try to find the duration of the event. The
                #duration is 4 lines ahead of the event name.
                durationMatch = eventDurationRe.search (htmlContents[n+4])

                if dateMatch and eventNumMatch and durationMatch :
                    #Event number
                    eventId = int (eventNumMatch.group(1))
                    #Date time stamp
                    eventTimestamp = dateMatch.group(1)
                    #Event duration
                    eventDuration = durationMatch.group(1)

                    sys.stdout.write("ListEvents processing ID %i" % 
                        (eventId))

                    # Add the event item to the menu
                    info = defaultInfo ()
                    info["VideoResolution"] = width
                    info["Videoaspect"] = calculateAspect(width, height)

                    # http://192.168.1.107/cgi-bin/nph-zms?source=event
                    # &event=84&monitor=1&format=avi&bitrate=10
                    # &maxfps=25&user=admin&pass=PASS

                    info["FileName"] = (
                        "%snph-zms?source=event&event=%i&monitor=%i"
                        "&format=avi&%s&%s" % (cgiurl, eventId, 
                        thisCameraId, qualityurl, videoauthurl))

                    sys.stdout.write("Event CGI URL: %s" % 
                        (info["FileName"]))

                    info["Thumb"] = ""

                    # Add the Event listitem
                    info["Title"] = ("%s  %s:  %s (%s %s)" % 
                                    (eventName, localize(30203), 
                                    eventTimestamp, eventDuration,
                                    localize (30206)))
                    info["Mode"] = "Event"

                    # Add the events view item
                    addListItem (addonHandle, info, numEvents, False)

            else : 
                #Debugging 
                #sys.stdout.write("Line %d: %s" % (n, line))
                pass
    else : 
        #No detailed events information was retrieved.
        sys.stderr.write("No detailed events info received for camera %d" 
                        % (int (thisCameraId)))

def convertMontageScale (userScale):
    if userScale == '4x':
        return 400
    elif userScale == '3x':
        return 300
    elif userScale == '2x':
        return 200
    elif userScale == '1.5x':
        return 150
    elif userScale == 'Actual':
        return 100
    elif userScale == '3/4':
        return 75
    elif userScale == '1/2':
        return 50
    elif userScale == '1/3':
        return 33
    elif userScale == '1/4':
        return 25
    else :
        return 100

def convertMontageLayout (userLayout):
    return userLayout

def ShowMontageView (addonHandle, NumCameras) :
    sys.stdout.write("Montage view")

    cgiurl = getUrl(__addon__.getSetting('cgiurl'))
    authurl, videoauthurl = createAuthString()
    qualityurl = ("&maxfps=%s" % (__addon__.getSetting('fps')))
    urlScale = convertMontageScale (__addon__.getSetting('scale'))
    layout = convertMontageLayout (__addon__.getSetting('layout'))

    for camera in NumCameras :
        # Add the Live View item
        info = defaultInfo ()
        info["Title"] = "%s %s" % (localize (30300), localize (30303))

        #Sample montage video URL
        #"http://192.168.1.107/cgi-bin/nph-zms?mode=jpeg&monitor=1&scale=25&
        # maxfps=10&user=admin&pass=PASS"
        info["FileName"] = ("%snph-zms?mode=jpeg&monitor=%i&scale=%i&%s%s" %
                         (cgiurl, camera, urlScale, qualityurl, videoauthurl))
        info["Thumb"] = ""
        info["Mode"] = "MontageVideo" #not currently used
        addListItem (addonHandle, info, NumCameras, False)


################
# Main program #
################
addonHandle = int(sys.argv[1])
queryStr = sys.argv[2]
args = urlparse.parse_qs(queryStr[1:])
queryMode = args.get('Mode', None)

if queryMode is None :
    #Top level view of all cameras plus those with Events.
    listCameras (addonHandle)

    xbmcplugin.setContent(addonHandle, 'movies')

    xbmcplugin.addSortMethod(handle = addonHandle, 
         sortMethod = xbmcplugin.SORT_METHOD_UNSORTED)

    xbmcplugin.addSortMethod(handle = addonHandle, 
         sortMethod = xbmcplugin.SORT_METHOD_LABEL)

    xbmcplugin.endOfDirectory(addonHandle)

elif queryMode[0] == 'EventsList' :
    CameraId = int (args.get('CameraId', '0')[0])
    NumEvents = int (args.get('NumEvents', '0')[0])
    listEvents (addonHandle, CameraId, NumEvents)

    xbmcplugin.setContent(addonHandle, 'movies')

    xbmcplugin.addSortMethod(handle = addonHandle, 
         sortMethod = xbmcplugin.SORT_METHOD_UNSORTED)

    xbmcplugin.addSortMethod(handle = addonHandle, 
         sortMethod = xbmcplugin.SORT_METHOD_LABEL)

    xbmcplugin.endOfDirectory(addonHandle)

elif queryMode[0] == 'Event' :
    #Video playback of an event has been selected.
    #Nothing to do here, the CGI URL is embedded in the filename
    #of the menu item.
    pass

elif queryMode[0] == 'Montage' :
    NumCameras = int (args.get('NumCameras', '0')[0])

    ShowMontageView (addonHandle, NumCameras)

    xbmcplugin.setContent(addonHandle, 'movies')

    xbmcplugin.addSortMethod(handle = addonHandle, 
         sortMethod = xbmcplugin.SORT_METHOD_UNSORTED)

    xbmcplugin.addSortMethod(handle = addonHandle, 
         sortMethod = xbmcplugin.SORT_METHOD_LABEL)

    xbmcplugin.endOfDirectory(addonHandle)


