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

def _extract_video_list(page, max_results: int = 20):
    """Extract a list of visible video entries from a YouTube search or suggestions.

    Returns a list of dicts: {index, title, href, channel, duration, snippet}
    """
    js = f"""
    (maxResults) => {{
        const nodes = Array.from(document.querySelectorAll('ytd-video-renderer,ytd-grid-video-renderer'));
        const out = [];
        for (let i=0;i<Math.min(nodes.length,maxResults);i++){{
            const el = nodes[i];
            try{{
                const a = el.querySelector('a#video-title') || el.querySelector('a#video-title-link') || el.querySelector('a');
                const href = a ? (a.href || null) : null;
                const title = a ? (a.innerText||a.textContent||'').trim() : (el.querySelector('#title') ? el.querySelector('#title').innerText.trim() : '');
                const channelEl = el.querySelector('#channel-name') || el.querySelector('ytd-channel-name a') || el.querySelector('.yt-simple-endpoint.style-scope.yt-formatted-string');
                const channel = channelEl ? (channelEl.innerText||'').trim() : '';
                const durEl = el.querySelector('ytd-thumbnail-overlay-time-status-renderer') || el.querySelector('.ytd-thumbnail-overlay-time-status-renderer') || el.querySelector('.video-time');
                const duration = durEl ? (durEl.innerText||'').trim() : '';
                const snippetEl = el.querySelector('#description-text') || el.querySelector('#description') || el.querySelector('.yt-lockup-description');
                const snippet = snippetEl ? (snippetEl.innerText||'').trim() : '';
                out.push({title:title, href:href, channel:channel, duration:duration, snippet:snippet});
            }}catch(e){{ continue; }}
        }}
        return out;
    }}
    """
    try:
        return page.evaluate(js, max_results)
    except Exception:
        # Best-effort fallback: return empty list
        return []


def _score_match(entry: Dict[str, Any], query: str) -> int:
    q = (query or '').lower()
    if not q:
        return 0
    score = 0
    title = (entry.get('title') or '').lower()
    channel = (entry.get('channel') or '').lower()
    snippet = (entry.get('snippet') or '').lower()
    tokens = [t for t in q.split() if t]
    for t in tokens:
        if t in title:
            score += 30
        if t in channel:
            score += 25
        if t in snippet:
            score += 10
    # small boost for exact phrase
    if q in title:
        score += 10
    return score


def _parse_selection(selection: Any) -> Optional[int]:
    if selection is None:
        return None
    if isinstance(selection, int):
        return max(0, selection - 1)
    s = str(selection).strip().lower()
    ord_map = {
        'first': 0, '1st': 0, 'one': 0, '1': 0,
        'second': 1, '2nd': 1, 'two': 1, '2': 1,
        'third': 2, '3rd': 2, 'three': 2, '3': 2,
        'fourth': 3, '4th': 3, '4': 3,
    }
    if s in ord_map:
        return ord_map[s]
    # try to parse an integer
    try:
        n = int(''.join(ch for ch in s if ch.isdigit()))
        return max(0, n-1)
    except Exception:
        return None


def tool_youtube_watch(
    _controller: PlaywrightController, args: Dict[str, Any]
) -> Dict[str, Any]:
    """Pick and open a YouTube video from the currently-open YouTube search or watch page.

    Precondition: the current `_controller.page` must be set and must be a YouTube
    search results page (`/results`) or a watch page (`/watch`). This tool will
    NOT start or navigate to YouTube automatically.

    Args (optional):
      - query: loose-match string to choose a video by title or channel
      - selection: ordinal or semantic selection (e.g. "first", "the second one", or an index)
      - timeout: integer milliseconds for waits

    Behavior:
      - When on a search page: extract visible results and cache them to
        `_controller.last_yt_results` so a follow-up call can select by index.
      - If `query` present: choose best fuzzy match and open it.
      - If `selection` present: interpret ordinal/index or perform fuzzy match.
      - Returns `_result_ok` with `status` and `match` or `ambiguous`.
    """
    try:
        page = _controller.page
        if page is None:
            return _result_error("browser not started; yt_watch requires an open YouTube page")

        url = (page.url or '').lower()
        if 'youtube.com/results' not in url and 'youtube.com/watch' not in url:
            return _result_error("yt_watch may only be called when a YouTube search or video page is open")

        timeout = int(args.get('timeout', 10000))
        query = args.get('query') or args.get('title')
        selection = args.get('selection')

        # If we're on a search results page, extract and cache the visible results
        if 'youtube.com/results' in url:
            results = _extract_video_list(page, max_results=20)
            _controller.last_yt_results = results

            if not results:
                return _result_error('no video entries found on the search page')

            # If no parameters, return the short list so the LLM can ask the user
            if not query and not selection:
                # Return top 6 to avoid huge payloads
                return _result_ok({'status': 'listed', 'results': results[:6]})

            # Handle selection (ordinal / index)
            sel_index = _parse_selection(selection)
            if sel_index is not None and 0 <= sel_index < len(results):
                entry = results[sel_index]
                href = entry.get('href')
                if href:
                    try:
                        page.goto(href, timeout=timeout)
                    except Exception:
                        try:
                            # best-effort click via evaluate
                            page.evaluate("(h)=>{ const a = Array.from(document.querySelectorAll('a')).find(x=>x.href===h); if(a) a.click(); }", href)
                        except Exception:
                            pass
                    try:
                        page.wait_for_selector('ytd-player', timeout=timeout)
                    except Exception:
                        page.wait_for_load_state('networkidle')
                    return _result_ok({'status': 'playing', 'match': entry})
                else:
                    return _result_error('selected entry has no href')

            # If a query is provided, fuzzy match against cached results
            if query:
                best = None
                best_score = -1
                for r in results:
                    s = _score_match(r, query)
                    if s > best_score:
                        best_score = s
                        best = r
                if best and best_score >= 5:
                    href = best.get('href')
                    if href:
                        try:
                            page.goto(href, timeout=timeout)
                        except Exception:
                            pass
                        try:
                            page.wait_for_selector('ytd-player', timeout=timeout)
                        except Exception:
                            page.wait_for_load_state('networkidle')
                        return _result_ok({'status': 'playing', 'match': best, 'score': best_score})
                # ambiguous or not found: return top options for disambiguation
                # sort by score and return first 4
                scored = [(r, _score_match(r, query)) for r in results]
                scored.sort(key=lambda x: x[1], reverse=True)
                options = [r for r,s in scored[:4]]
                return _result_ok({'status': 'ambiguous', 'query': query, 'options': options})

        # If we're on a watch page and selection requested, attempt to pick from suggestions
        if 'youtube.com/watch' in url:
            # If selection is omitted but query provided, try to match against suggestions
            # Extract sidebar suggestions (compact renderers)
            try:
                js = """
                (maxResults) => {
                    const nodes = Array.from(document.querySelectorAll('ytd-compact-video-renderer, ytd-compact-autoplay-renderer'));
                    const out = [];
                    for (let i=0;i<Math.min(nodes.length,maxResults);i++){
                        const el = nodes[i];
                        try{
                            const a = el.querySelector('a#video-title') || el.querySelector('a');
                            const href = a ? (a.href || null) : null;
                            const title = a ? (a.innerText||'').trim() : '';
                            const channelEl = el.querySelector('#channel-name') || el.querySelector('ytd-channel-name a');
                            const channel = channelEl ? (channelEl.innerText||'').trim() : '';
                            out.push({title:title, href:href, channel:channel});
                        }catch(e){ continue; }
                    }
                    return out;
                }
                """
                suggestions = page.evaluate(js, 20)
            except Exception:
                suggestions = []

            if not suggestions:
                return _result_error('no suggestions found on watch page')

            _controller.last_yt_results = suggestions

            sel_index = _parse_selection(selection)
            if sel_index is not None and 0 <= sel_index < len(suggestions):
                entry = suggestions[sel_index]
                href = entry.get('href')
                if href:
                    try:
                        page.goto(href, timeout=timeout)
                    except Exception:
                        pass
                    try:
                        page.wait_for_selector('ytd-player', timeout=timeout)
                    except Exception:
                        page.wait_for_load_state('networkidle')
                    return _result_ok({'status': 'playing', 'match': entry})

            if query:
                best = None
                best_score = -1
                for r in suggestions:
                    s = _score_match(r, query)
                    if s > best_score:
                        best_score = s
                        best = r
                if best and best_score >= 5:
                    try:
                        page.goto(best.get('href'), timeout=timeout)
                    except Exception:
                        pass
                    try:
                        page.wait_for_selector('ytd-player', timeout=timeout)
                    except Exception:
                        page.wait_for_load_state('networkidle')
                    return _result_ok({'status': 'playing', 'match': best, 'score': best_score})

            # If we reach here, return options for disambiguation
            return _result_ok({'status': 'ambiguous', 'options': suggestions[:6]})

        return _result_error('unhandled YouTube page type')

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
        name="yt_pause_play",
        func=tool_youtube_pause_play,
        spec=_YOUTUBE_TOOL_SPECS["yt_pause_play"],
    ),
]
