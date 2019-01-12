print()

import json
import os
import requests
import pathlib
import shutil

#
# SETTINGS & INPUT DATA
#

CACHE_DIR = "cache"


p = pathlib.Path("./youtube-api-key.txt")
MY_API_KEY = p.read_text().strip()

VIDEOS_ID = set()
with open("./videos-id.txt") as fp:
    for line in fp:
        VIDEOS_ID.add(line.strip())

# Création du répertoire de cache
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

#
# HELPERS
#


def makeYoutubeVideoURL(
    videoId): return f"https://www.youtube.com/watch?v={videoId}"


makeVideosURL = (
    lambda videoId: f"https://www.googleapis.com/youtube/v3/videos?id={videoId}&part=snippet%2CcontentDetails%2Cstatistics&key={MY_API_KEY}"
)
makeCommentThreadsURL = (
    lambda videoId, pageToken: f"https://www.googleapis.com/youtube/v3/commentThreads?part=snippet%2Creplies&videoId={videoId}&key={MY_API_KEY}&maxResults=100&order=time"
    + (f"&pageToken={pageToken}" if pageToken else "")
)
makeCommentsURL = (
    lambda parentId, pageToken: f"https://www.googleapis.com/youtube/v3/comments?part=snippet&parentId={parentId}&key={MY_API_KEY}"
    + (f"&pageToken={pageToken}" if pageToken else "")
)

#
# SERVICE FUNCTIONS
#


def getVideoMetadata(videoId):
    r = requests.get(makeVideosURL(videoId))
    json = r.json()
    data = json["items"][0]
    return data


def getSomeComments(videoId, nextPageToken):
    r = requests.get(makeCommentThreadsURL(videoId, nextPageToken))
    json = r.json()
    return json


def getSomeReplies(commentThreadId, nextPageToken):
    r = requests.get(makeCommentsURL(commentThreadId, nextPageToken))
    return r.json()


#
# MAIN LOOP
#

DATA = {}

for i, videoId in enumerate(VIDEOS_ID):

    # Check the cache
    p = pathlib.Path(CACHE_DIR, f"{videoId}.json")
    if p.exists():
        print(f"{videoId} already in cache")
        continue

    # Video

    print(f"{i + 1}/{len(VIDEOS_ID)} — {videoId} — {makeYoutubeVideoURL(videoId)}")
    videoMetadata = getVideoMetadata(videoId)
    DATA[videoId] = videoMetadata
    DATA[videoId]["commentThreads"] = {}

    # Comment threads

    comments = []
    nextPageToken = ""
    while True:
        someComments = getSomeComments(videoId, nextPageToken)
        nextPageToken = (
            someComments["nextPageToken"] if "nextPageToken" in someComments else None
        )
        comments.extend(someComments["items"])
        print(
            f"    {len(someComments['items'])} {'+' if nextPageToken is not None else ''}"
        )
        if nextPageToken is None:
            break
    print(f"    = {len(comments)} comment threads in this video", end="")
    for c in comments:
        DATA[videoId]["commentThreads"][c["id"]] = c

    # Replies
    commentThreadsWithReplies = list(
        filter(lambda x: "replies" in x, comments))
    print(f", {len(commentThreadsWithReplies)} with replies")
    for i, comment in enumerate(commentThreadsWithReplies):
        DATA[videoId]["commentThreads"][c["id"]]["replies"] = {}
        print(
            f"    {i}/{len(commentThreadsWithReplies)} commentThread {comment['id']} — will fetch {comment['snippet']['totalReplyCount']} replies: "
        )
        replies = []
        nextPageToken = ""
        while True:
            someReplies = getSomeReplies(comment["id"], nextPageToken)
            nextPageToken = (
                someReplies["nextPageToken"] if "nextPageToken" in someReplies else None
            )
            print(
                f"        {len(someReplies['items'])} {'+' if nextPageToken is not None else ''}"
            )
            replies.extend(someReplies["items"])
            for r in replies:
                DATA[videoId]["commentThreads"][comment["id"]
                                                ]["replies"][r["id"]] = r
            if nextPageToken is None:
                break

    p = pathlib.Path(CACHE_DIR, f"{videoId}.json")
    with open(p, "w") as fp:
        json.dump(DATA[videoId], fp)
