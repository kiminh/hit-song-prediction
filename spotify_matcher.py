import pandas as pd
import re
from fuzzywuzzy import fuzz
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from tqdm import tqdm


def remove_bracketed_text(text):
    return re.sub("[\(\[].*?[\)\]]", "", text)


if __name__ == "__main__":

    # read charts / songs file
    df = pd.read_csv("datasets/billboard.csv")
    df = df.drop(
        [c for c in df.columns if "0.1" in c], axis=1
    )  # remove some Unnamed cols
    df["SongID"] = df["title"] + df["artist"]

    # remove duplicates
    df = df.drop_duplicates(subset="SongID", keep="first")

    # create empty dataframes for Spotify / unmatched songs
    spotify_df = pd.DataFrame(columns=[])
    unmatched_df = pd.DataFrame(columns=[])

    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials())
    try:
        for idx, row in tqdm(df.iterrows(), total=len(df)):
            matched = False

            # search for a track using the track title.
            # subsequently compare the artist(s) of the track and its title using Levenshtein distance
            results = sp.search(row.title, type="track")
            for r in results["tracks"]["items"]:
                artists = r["artists"]
                popularity = r["popularity"]
                name = r["name"]
                artist_names = ", ".join([a["name"] for a in artists])

                title_levenshtein = fuzz.ratio(
                    remove_bracketed_text(row.title.lower()),
                    remove_bracketed_text(name.lower()),
                )
                artist_levenshtein = fuzz.ratio(
                    remove_bracketed_text(row.artist.lower().replace("featuring", "")),
                    remove_bracketed_text(artist_names.lower()),
                )

                if title_levenshtein > 90 and artist_levenshtein > 80:
                    d = {
                        "title_levenshtein": title_levenshtein,
                        "artist_levenshtein": artist_levenshtein,
                        "popularity": popularity,
                        "name": name,
                        "artists": artist_names,
                        "id": r["id"],
                        "uri": r["uri"],
                        "album": r["album"]["name"],
                        "preview_url": r["preview_url"],
                    }

                    row_dict = dict(row)
                    row_dict = {"billboard_" + k: v for k, v in dict(row).items()}
                    d = {**d, **row_dict}
                    spotify_df = spotify_df.append(d, ignore_index=True)
                    matched = True
                    break

            if not matched:
                unmatched_df = unmatched_df.append(row)

    except Exception as e:
        print(e)
        pass

    print("Unmatched tracks:", len(unmatched_df))
    spotify_df.to_csv("datasets/spotify_billboard.csv")
    unmatched_df.to_csv("datasets/unmatched_spotify_billboard.csv")
