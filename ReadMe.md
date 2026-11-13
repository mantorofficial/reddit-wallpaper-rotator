# Reddit Wallpaper Rotator

A lightweight Linux desktop application that automatically rotates your desktop wallpaper using image submissions from Reddit communities.

## Overview

Reddit Wallpaper Rotator is a personal, non-commercial desktop application designed to make discovering and enjoying community-shared wallpapers easier.

Users choose one or more subreddits, and the application retrieves eligible image submissions and uses them as desktop wallpapers. Wallpapers rotate automatically at a configurable interval.

The project aims to provide a simple way to enjoy images shared by Reddit communities without manually browsing and downloading individual posts.

## Planned Features

- **Subreddit selection:** Enter any supported subreddit to use as a wallpaper source.
- **Automatic rotation:** Change the desktop wallpaper at a configurable interval (60 seconds by default).
- **Image filtering:** Only use supported image submissions.
- **Local caching:** Temporarily cache downloaded wallpapers to reduce repeated downloads.
- **Manual controls:** Skip to the next wallpaper, pause rotation, or resume it.
- **Multiple sources:** Support multiple user-selected subreddits.
- **Desktop integration:** Apply wallpapers through the user's Linux desktop environment.
- **Configurable settings:** Adjust rotation intervals and local cache behavior.

## Example Usage

1. Launch the application.
2. Enter a subreddit, such as `r/wallpaper`.
3. The application retrieves eligible image submissions.
4. Selected images are downloaded and cached locally.
5. The application changes the desktop wallpaper automatically.
6. A new wallpaper is selected at the configured interval.

## Reddit API Usage

The project intends to use Reddit as a read-only source of publicly available image submissions.

Planned API usage is limited to:

- Retrieving public subreddit listings.
- Reading image submission URLs and relevant post metadata.
- Downloading eligible images for local wallpaper display.

The application will not:

- Submit posts or comments.
- Vote on submissions.
- Send messages or interact with Reddit users.
- Perform moderation actions.
- Collect or analyze Reddit user profiles.
- Operate as a public-facing Reddit service.

**API access is subject to Reddit's approval and applicable policies.** No unauthorized API access or scraping is intended.

## Why Not Devvit?

Devvit is designed for applications operating within Reddit's ecosystem.

This project requires functionality outside Reddit, including:

- Access to the local filesystem.
- Downloading and caching image files.
- Integrating with Linux desktop wallpaper-management systems.
- Running as a background desktop application.
- Providing native desktop controls.

These requirements make a standalone Linux application more appropriate than a Devvit application.

## Intended Subreddits

Initial examples include:

- [r/wallpaper](https://www.reddit.com/r/wallpaper/)
- [r/wallpapers](https://www.reddit.com/r/wallpapers/)
- [r/WQHD_Wallpaper](https://www.reddit.com/r/WQHD_Wallpaper/)
- [r/EarthPorn](https://www.reddit.com/r/EarthPorn/)
- [r/wallpaperdump](https://www.reddit.com/r/wallpaperdump/)

Users will be able to choose which communities the application accesses.

## Platform

- **Target operating system:** Linux
- **Application type:** Standalone desktop application
- **Intended use:** Personal and non-commercial
- **Interface:** Native desktop interface (planned)

## Development Status

<escape>🚧</escape> Early development / planning.

The application is currently being designed. Reddit API access has not yet been obtained, and implementation of Reddit integration is pending approval and clarification of permitted access methods.

## Compliance

The project intends to comply with:

- [Reddit Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy)
- [Reddit Developer Terms](https://www.redditinc.com/policies/developer-terms)
- [Reddit Data API Terms](https://www.redditinc.com/policies/data-api-terms)

The application will respect applicable API rate limits, attribution requirements, content restrictions, and data-retention requirements.

## License

License to be determined.
