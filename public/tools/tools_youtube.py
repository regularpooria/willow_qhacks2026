from typing import Dict, Any, TYPE_CHECKING
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


def tool_youtube_watch(
    _controller: PlaywrightController, args: Dict[str, Any]
) -> Dict[str, Any]:
    """Search YouTube for `title` and open the first matching video.

    Args: title (string)
    """
    title = args.get("title") or args.get("query")
    if not title:
        return _result_error("'title' parameter is required")
    try:
        if _controller.page is None:
            _controller.start(headless=False)
        page = _controller.page
        if page is None:
            return _result_error("failed to start browser")

        q = urllib.parse.quote_plus(str(title))
        search_url = f"https://www.youtube.com/results?search_query={q}"
        page.goto(search_url, timeout=args.get("timeout", 30000))
        try:
            page.wait_for_selector(
                "ytd-video-renderer,ytd-grid-video-renderer", timeout=8000
            )
        except Exception:
            pass

        # Try to click the first video result
        first = page.query_selector(
            "ytd-video-renderer a#video-title,ytd-grid-video-renderer a#video-title"
        )
        if not first:
            # fallback: attempt to extract href via evaluate
            href = page.evaluate(
                "() => { const a = document.querySelector('ytd-video-renderer a#video-title, ytd-grid-video-renderer a#video-title'); return a ? a.href : null; }"
            )
            if not href:
                return _result_error("no video result found")
            page.goto(href)
        else:
            first.click()

        # Wait for video page to load
        try:
            page.wait_for_selector("ytd-player", timeout=10000)
        except Exception:
            # best-effort wait
            page.wait_for_load_state("networkidle")

        current = page.url
        title_actual = page.title()
        return _result_ok(
            {
                "status": "playing",
                "requested": title,
                "title": title_actual,
                "url": current,
            }
        )
    except Exception as e:
        return _result_error(e)


def tool_youtube_like(
    _controller: PlaywrightController, args: Dict[str, Any]
) -> Dict[str, Any]:
    """Like the currently open YouTube video page.

    Performs a best-effort search for a Like button and clicks it.
    """
    try:
        page = _controller.page
        if page is None:
            return _result_error("browser not started")
        if "youtube.com/watch" not in (page.url or ""):
            return _result_error("not on a YouTube video page")

        clicked = page.evaluate(
            """
			() => {
				const candidates = Array.from(document.querySelectorAll('button, tp-yt-paper-icon-button, ytd-toggle-button-renderer'));
				for (const el of candidates) {
					const label = (el.getAttribute && (el.getAttribute('aria-label')||'') || '').toLowerCase();
					const title = (el.getAttribute && (el.getAttribute('title')||'') || '').toLowerCase();
					const txt = (el.innerText||'').toLowerCase();
					if (label.includes('like') || title.includes('like') || txt.includes('like')) {
						el.click();
						return true;
					}
				}
				return false;
			}
			"""
        )
        if clicked:
            return _result_ok({"status": "liked"})
        else:
            return _result_error("like button not found")
    except Exception as e:
        return _result_error(e)


def tool_youtube_subscribe(
    _controller: PlaywrightController, args: Dict[str, Any]
) -> Dict[str, Any]:
    """Subscribe to the channel when on a YouTube video or channel page.

    Best-effort: clicks the first element containing 'subscribe'.
    """
    try:
        page = _controller.page
        if page is None:
            return _result_error("browser not started")

        clicked = page.evaluate(
            """
			() => {
				// Look for elements whose text content or aria-label contains 'subscribe'
				const candidates = Array.from(document.querySelectorAll('tp-yt-paper-button, yt-formatted-string, button, a, ytd-subscribe-button-renderer'));
				for (const el of candidates) {
					const label = (el.getAttribute && (el.getAttribute('aria-label')||'') || '').toLowerCase();
					const txt = (el.innerText||'').toLowerCase();
					if (label.includes('subscribe') || txt.includes('subscribe')) {
						// avoid clicking 'subscribed' state
						if (txt.includes('subscribed')) return false;
						el.click();
						return true;
					}
				}
				return false;
			}
			"""
        )
        if clicked:
            return _result_ok({"status": "subscribed"})
        else:
            return _result_error("subscribe button not found or already subscribed")
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


# Define specs for each YouTube tool
_YOUTUBE_TOOL_SPECS = {
    "yt_search": ToolSpec(
        name="yt_search",
        description="Search YouTube for videos. Opens headed browser and navigates to search results.",
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string"}, "timeout": {"type": "integer"}},
        },
    ),
    "yt_watch": ToolSpec(
        name="yt_watch",
        description="Search YouTube for a video by title and open the first result.",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "query": {"type": "string"},
                "timeout": {"type": "integer"},
            },
        },
    ),
    "yt_like": ToolSpec(
        name="yt_like",
        description="Like the currently open YouTube video. Must be on a video page.",
        parameters={"type": "object", "properties": {}},
    ),
    "yt_subscribe": ToolSpec(
        name="yt_subscribe",
        description="Subscribe to the channel on a YouTube video or channel page.",
        parameters={"type": "object", "properties": {}},
    ),
    "yt_pause_play": ToolSpec(
        name="yt_pause_play",
        description="Toggle the current video (pause or play), if a video is open.",
        parameters={"type": "object", "properties": {}},
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
        name="yt_watch",
        func=tool_youtube_watch,
        spec=_YOUTUBE_TOOL_SPECS["yt_watch"],
    ),
    ToolDefinition(
        name="yt_like",
        func=tool_youtube_like,
        spec=_YOUTUBE_TOOL_SPECS["yt_like"],
    ),
    ToolDefinition(
        name="yt_subscribe",
        func=tool_youtube_subscribe,
        spec=_YOUTUBE_TOOL_SPECS["yt_subscribe"],
    ),
    ToolDefinition(
        name="yt_pause_play",
        func=tool_youtube_pause_play,
        spec=_YOUTUBE_TOOL_SPECS["yt_pause_play"],
    ),
]
