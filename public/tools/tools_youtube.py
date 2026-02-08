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



# -----------------------------
# YouTube helpers for yt_watch
# -----------------------------

def _extract_videos_from_page(page, max_results: int = 20):
    """Extract all visible videos from the current YouTube search/results page.
    
    Handles regular videos (ytd-video-renderer, ytd-grid-video-renderer) and shorts.
    Returns list of dicts: {index, title, channel, description, element_index}
    """
    js = """
    (maxResults) => {
        // Select both regular videos and shorts
        const videoSelectors = 'ytd-video-renderer, ytd-grid-video-renderer, ytd-reel-item-renderer';
        const nodes = Array.from(document.querySelectorAll(videoSelectors));
        const out = [];
        
        for (let i = 0; i < Math.min(nodes.length, maxResults); i++) {
            const el = nodes[i];
            try {
                // Extract title
                const titleEl = el.querySelector('a#video-title, a#video-title-link, .yt-simple-endpoint');
                const title = titleEl ? (titleEl.innerText || titleEl.textContent || '').trim() : '';
                
                // Extract channel/creator name
                const channelEl = el.querySelector('#channel-name, ytd-channel-name a, .ytd-channel-name');
                const channel = channelEl ? (channelEl.innerText || '').trim().split('\\n')[0] : '';
                
                // Extract description/snippet
                const descEl = el.querySelector('#description-text, #description, .yt-lockup-description');
                const description = descEl ? (descEl.innerText || '').trim() : '';
                
                if (title) {
                    out.push({
                        index: i + 1,
                        title: title,
                        channel: channel,
                        description: description,
                        element_index: i
                    });
                }
            } catch (e) {
                continue;
            }
        }
        return out;
    }
    """
    try:
        return page.evaluate(js, max_results)
    except Exception:
        return []


def _score_match(entry: Dict[str, Any], query: str) -> int:
    """Score how well a query matches a video entry."""
    q = (query or '').lower()
    if not q:
        return 0
    
    score = 0
    title = (entry.get('title') or '').lower()
    channel = (entry.get('channel') or '').lower()
    description = (entry.get('description') or '').lower()
    
    tokens = [t.strip() for t in q.split() if t.strip()]
    
    for token in tokens:
        if token in title:
            score += 30
        elif token in channel:
            score += 25
        elif token in description:
            score += 10
    
    return score


def _parse_ordinal(selection: str) -> Optional[int]:
    """Parse ordinal words like 'first', 'second', 'the first one', etc. to index.
    
    Returns 0-based index or None if not parseable.
    """
    if not selection:
        return None
    
    s = str(selection).strip().lower()
    
    # Map ordinal words to indices
    ordinal_map = {
        'first': 0, '1st': 0, 'one': 0,
        'second': 1, '2nd': 1, 'two': 1,
        'third': 2, '3rd': 2, 'three': 2,
        'fourth': 3, '4th': 3, 'four': 3,
        'fifth': 4, '5th': 4, 'five': 4,
    }
    
    # Try exact match
    if s in ordinal_map:
        return ordinal_map[s]
    
    # Try phrases like "the first one", "the second video", etc.
    for word, idx in ordinal_map.items():
        if word in s:
            return idx
    
    # Try to parse a number
    try:
        num = int(''.join(ch for ch in s if ch.isdigit()))
        if num > 0:
            return num - 1
    except (ValueError, IndexError):
        pass
    
    return None



def tool_youtube_watch(
    _controller: PlaywrightController, args: Dict[str, Any]
) -> Dict[str, Any]:
    """Select and play a YouTube video from the current search results page.
    
    MUST be called when a YouTube search results page (/results) is already open.
    
    Args:
      - query (optional): loose text to match against video title, channel, or description
      - selection (optional): ordinal word like "first", "second", "the first one", etc.
      - timeout (optional): milliseconds to wait
      
    Behavior:
      1. Extracts all visible videos from the current page
      2. If query provided: finds best fuzzy match
      3. If selection provided: picks by ordinal (1st, 2nd, etc.)
      4. Clicks the video container to open it
      5. Verifies the page navigated to a watch URL
      6. Returns success only if video actually loaded
    """
    try:
        page = _controller.page
        if page is None:
            return _result_error("browser not started; yt_watch requires an open YouTube page")
        
        url = (page.url or '').lower()
        if 'youtube.com/results' not in url:
            return _result_error("yt_watch only works on YouTube search results pages (/results)")
        
        timeout = int(args.get('timeout', 15000))
        query = args.get('query')
        selection = args.get('selection')
        
        # Extract all visible videos from the page
        videos = _extract_videos_from_page(page, max_results=30)
        if not videos:
            return _result_error('no videos found on this page')
        
        # Cache for potential follow-up calls
        _controller.last_yt_results = videos
        
        # If no query or selection, return the list so LLM can ask user which one
        if not query and not selection:
            preview = [{'index': v['index'], 'title': v['title'], 'channel': v['channel']} for v in videos[:6]]
            return _result_ok({'status': 'listed', 'count': len(videos), 'preview': preview})
        
        # Determine which video to click
        target_video = None
        
        # Try selection first (ordinal like "first", "second")
        if selection:
            idx = _parse_ordinal(selection)
            if idx is not None and 0 <= idx < len(videos):
                target_video = videos[idx]
        
        # If no selection match, try query (fuzzy text match)
        if not target_video and query:
            best = None
            best_score = -1
            for v in videos:
                score = _score_match(v, query)
                if score > best_score:
                    best_score = score
                    best = v
            if best and best_score >= 5:
                target_video = best
            else:
                # No good match found
                scored = [(v, _score_match(v, query)) for v in videos]
                scored.sort(key=lambda x: x[1], reverse=True)
                top_options = [v for v, _ in scored[:4]]
                return _result_ok({
                    'status': 'no_match',
                    'query': query,
                    'message': f"No clear match for '{query}'. Found {len(videos)} videos.",
                    'suggestions': top_options
                })
        
        # If still no target, something went wrong
        if not target_video:
            return _result_error('could not determine which video to play')
        
        # Click the video by its container position
        element_idx = target_video['element_index']
        try:
            js = f"""
            (idx) => {{
                const videoSelectors = 'ytd-video-renderer, ytd-grid-video-renderer, ytd-reel-item-renderer';
                const nodes = Array.from(document.querySelectorAll(videoSelectors));
                if (idx < nodes.length) {{
                    const el = nodes[idx];
                    // Click anywhere on the video container to open it
                    el.click();
                    return true;
                }}
                return false;
            }}
            """
            clicked = page.evaluate(js, element_idx)
            if not clicked:
                return _result_error('failed to locate video element on page')
        except Exception as e:
            return _result_error(f'error clicking video: {e}')
        
        # Wait for the watch page to load
        try:
            page.wait_for_url('**/watch?v=**', timeout=timeout)
        except Exception:
            # Try waiting for the player instead
            try:
                page.wait_for_selector('ytd-player', timeout=5000)
            except Exception:
                # Last resort: just wait for network to settle
                try:
                    page.wait_for_load_state('networkidle', timeout=5000)
                except Exception:
                    return _result_error('timeout: video page did not load')
        
        # Final check: are we actually on a watch page?
        final_url = (page.url or '').lower()
        if 'youtube.com/watch' not in final_url and 'youtube.com/shorts' not in final_url:
            return _result_error('video did not load; still on search page')
        
        # Success!
        return _result_ok({
            'status': 'playing',
            'title': target_video.get('title'),
            'channel': target_video.get('channel')
        })
        
    except Exception as e:
        return _result_error(f'unexpected error: {e}')



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
        description="Navigate to YouTube search results for a query. USAGE: When the user asks to search YouTube for a topic. This ONLY navigates to the search page; it does NOT select or open a specific video. Use this to show search results, then use yt_watch to select a video from the results. EXAMPLE: User says 'search YouTube for MrBeast' → use yt_search with query='MrBeast' to display results.",
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string"}, "timeout": {"type": "integer"}},
        },
    ),
    "yt_watch": ToolSpec(
        name="yt_watch",
        description="Select and open a YouTube video from the currently-displayed search results or suggestions page. USAGE: Use this ONLY when a YouTube search results page or video page is already open (e.g., after yt_search). With 'query', fuzzy-match a video by title/channel (e.g., 'MrBeast' finds videos by that creator). With 'selection', use ordinal words like 'first', 'second', 'the one from X'. Returns status='playing' on success or 'ambiguous' if multiple matches exist. EXAMPLES: (1) After search results show, user says 'watch the first one' → call yt_watch with selection='first'. (2) User says 'watch the one from MrBeast' → call yt_watch with query='MrBeast'.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "selection": {"type": "string"},
                "timeout": {"type": "integer"},
            },
        },
    ),
    "yt_pause_play": ToolSpec(
        name="yt_pause_play",
        description="Toggle play/pause on the currently-playing YouTube video. USAGE: Use ONLY when a video is already playing (user is on a YouTube watch page). Call this when the user says 'play', 'pause', 'resume', or 'stop'. Do NOT use this to select or open a new video. EXAMPLE: A video is playing, user says 'pause' → call yt_pause_play with no arguments.",
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
        name="yt_pause_play",
        func=tool_youtube_pause_play,
        spec=_YOUTUBE_TOOL_SPECS["yt_pause_play"],
    ),
]
