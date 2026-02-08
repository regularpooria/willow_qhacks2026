from typing import Dict, Any, TYPE_CHECKING, Optional
import urllib.parse

from public.tools.util_classes import (
    _result_error,
    _result_ok,
    ToolSpec,
    ToolDefinition,
)

from public.tools.YoutubeController import PlaywrightController


def tool_youtube_search(
    _controller: PlaywrightController, args: Dict[str, Any]
) -> Dict[str, Any]:
    query = args.get("query")
    if not query:
        return _result_error("'query' parameter is required")
    try:
        # Ensure browser is running in headed mode per request
        if _controller.page is None:
            _controller.start(headless=False)
        page = _controller.page
        if page is None:
            return _result_error("failed to start browser")

        q = urllib.parse.quote_plus(str(query))
        url = f"https://www.youtube.com/results?search_query={q}"
        page.goto(url, timeout=args.get("timeout", 30000))

        # wait briefly for video items to render
        try:
            page.wait_for_selector(
                "ytd-video-renderer,ytd-grid-video-renderer", timeout=8000
            )
        except Exception:
            pass

        # Collect top results (title, url, duration if available)
        return _result_ok({"status": "searched", "query": query, "url": url})
    except Exception as e:
        return _result_error(e)

def tool_youtube_pause_play(
    _controller: PlaywrightController, args: Dict[str, Any]
) -> Dict[str, Any]:
    """Toggle play/pause on the currently open YouTube video.

    Clicks the play/pause button in the video player.
    """
    try:
        page = _controller.page
        if page is None:
            return _result_error("browser not started")
        if "youtube.com/watch" not in (page.url or ""):
            return _result_error("not on a YouTube video page")

        toggled = page.evaluate(
            """
			() => {
				// Look for play/pause button in the video player
				// YouTube uses various button structures, so we'll search multiple ways
				const candidates = Array.from(document.querySelectorAll('button, .ytp-play-button, [aria-label*="play"], [aria-label*="pause"]'));
				for (const el of candidates) {
					const label = (el.getAttribute && (el.getAttribute('aria-label')||'') || '').toLowerCase();
					const cls = (el.getAttribute && (el.getAttribute('class')||'') || '').toLowerCase();
					const title = (el.getAttribute && (el.getAttribute('title')||'') || '').toLowerCase();
					
					// Match play or pause in label/title
					if (label.includes('play') || label.includes('pause') || title.includes('play') || title.includes('pause') || cls.includes('play')) {
						// Prioritize buttons in the video container
						const playerContainer = document.querySelector('.html5-video-player, ytd-player');
						if (playerContainer && playerContainer.contains(el)) {
							el.click();
							return true;
						}
						// Fallback: click if it's the first match
						if (!el.offsetParent) continue; // Skip hidden elements
						el.click();
						return true;
					}
				}
				return false;
			}
			"""
        )
        if toggled:
            return _result_ok({"status": "toggled"})
        else:
            return _result_error("play/pause button not found")
    except Exception as e:
        return _result_error(e)


def tool_youtube_watch(
    _controller: PlaywrightController, args: Dict[str, Any]
) -> Dict[str, Any]:
    """Click on a YouTube video from search results to watch it.

    Can click by index (0-based for first result) or by matching text in the title.
    Use case 1: User says "pick the first one" -> index=0
    Use case 2: User says "watch [title text]" -> title="[title text]"
    """
    try:
        page = _controller.page
        if page is None:
            return _result_error("browser not started")
        if "youtube.com/results" not in (page.url or ""):
            return _result_error("not on a YouTube search results page")

        index = args.get("index")
        title_search = args.get("title")

        if index is None and title_search is None:
            return _result_error("Either 'index' (0-based) or 'title' parameter is required")

        # Use Playwright to find and click the video
        if index is not None:
            # Click by index (0-based)
            clicked = page.evaluate(
                f"""
                () => {{
                    const videos = Array.from(document.querySelectorAll('ytd-video-renderer, ytd-grid-video-renderer'));
                    if (videos.length > {index}) {{
                        const link = videos[{index}].querySelector('a#video-title');
                        if (link) {{
                            link.click();
                            return true;
                        }}
                    }}
                    return false;
                }}
                """
            )
        else:
            # Click by title match (case-insensitive substring match)
            escaped_search = title_search.replace('"', '\\"')
            clicked = page.evaluate(
                f"""
                () => {{
                    const query = "{escaped_search}".toLowerCase();
                    const videos = Array.from(document.querySelectorAll('ytd-video-renderer, ytd-grid-video-renderer'));
                    for (const video of videos) {{
                        const titleEl = video.querySelector('a#video-title');
                        if (titleEl && titleEl.textContent.toLowerCase().includes(query)) {{
                            titleEl.click();
                            return true;
                        }}
                    }}
                    return false;
                }}
                """
            )

        if clicked:
            return _result_ok(
                {{
                    "status": "clicked",
                    "method": "index" if index is not None else "title_match",
                }}
            )
        else:
            return _result_error(
                "Video not found"
                if index is None
                else f"No video at index {index}"
            )
    except Exception as e:
        return _result_error(e)


# Define specs for each YouTube tool
_YOUTUBE_TOOL_SPECS = {
    "yt_search": ToolSpec(
        name="yt_search",
        description="Navigate to YouTube search results for a query. USAGE: When the user asks to search YouTube for a topic. This ONLY navigates to the search page; it does NOT select or open a specific video. Use this to show search results, then use yt_watch to select a video from the results. EXAMPLE: User says 'search YouTube for MrBeast' → use yt_search with query='MrBeast' to display results.",
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string"}, "timeout": {"type": "integer"}},
        },
    ),
    "yt_pause_play": ToolSpec(
        name="yt_pause_play",
        description="Toggle play/pause on the currently-playing YouTube video. USAGE: Use ONLY when a video is already playing (user is on a YouTube watch page). Call this when the user says 'play', 'pause', 'resume', or 'stop'. Do NOT use this to select or open a new video. EXAMPLE: A video is playing, user says 'pause' → call yt_pause_play with no arguments.",
        parameters={"type": "object", "properties": {}},
    ),
    "yt_watch": ToolSpec(
        name="yt_watch",
        description="Click on a video from YouTube search results to watch it. USAGE: Use ONLY when on a YouTube search results page (after yt_search). Select a video by either: (1) index - 0 for first result, 1 for second, etc., or (2) title - search text that matches part of the video title. EXAMPLES: User says 'pick the first one' → call yt_watch with index=0. User says 'watch the one about cats' → call yt_watch with title='cats'.",
        parameters={
            "type": "object",
            "properties": {
                "index": {"type": "integer"},
                "title": {"type": "string"},
            },
        },
    ),
}

# Export tool definitions for registration in base tools.py
youtube_tools = [
    ToolDefinition(
        name="yt_search",
        func=tool_youtube_search,
        spec=_YOUTUBE_TOOL_SPECS["yt_search"],
    ),
    ToolDefinition(
        name="yt_pause_play",
        func=tool_youtube_pause_play,
        spec=_YOUTUBE_TOOL_SPECS["yt_pause_play"],
    ),
    ToolDefinition(
        name="yt_watch",
        func=tool_youtube_watch,
        spec=_YOUTUBE_TOOL_SPECS["yt_watch"],
    ),
]
