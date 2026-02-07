from typing import Dict, Any
import urllib.parse

from public.tools.util_classes import (
    _result_error,
    _result_ok,
    ToolSpec,
    ToolDefinition,
)
from public.tools.YoutubeController import PlaywrightController


# -----------------------------------------------------------
# Helper
# -----------------------------------------------------------


def _ensure_page(_controller: PlaywrightController):
    if _controller.page is None:
        _controller.start(headless=False)
    return _controller.page


# -----------------------------------------------------------
# Tool: Search places on Google Maps
# -----------------------------------------------------------


def tool_maps_where(
    _controller: PlaywrightController, args: Dict[str, Any]
) -> Dict[str, Any]:
    query = args.get("query")
    if not query:
        return _result_error("'query' parameter is required")

    try:
        page = _ensure_page(_controller)
        if page is None:
            return _result_error("failed to start browser")

        q = urllib.parse.quote_plus(str(query))
        url = f"https://www.google.com/maps/search/{q}"
        page.goto(url, timeout=args.get("timeout", 30000))

        try:
            page.wait_for_selector("div[role='article']", timeout=10000)
        except Exception:
            pass

        return _result_ok({"status": "searched", "query": query, "url": page.url})
    except Exception as e:
        return _result_error(e)


# -----------------------------------------------------------
# Tool: Open first place result from a search
# -----------------------------------------------------------


def tool_maps_open_place(
    _controller: PlaywrightController, args: Dict[str, Any]
) -> Dict[str, Any]:
    try:
        page = _ensure_page(_controller)

        # Click first search result card
        first = page.query_selector("div[role='article'] a")
        if not first:
            return _result_error("no place result found")

        first.click()

        page.wait_for_selector("h1", timeout=10000)

        name = page.query_selector("h1").inner_text()
        return _result_ok({"status": "opened", "place_name": name, "url": page.url})
    except Exception as e:
        return _result_error(e)


# -----------------------------------------------------------
# Tool: Get directions between two places
# -----------------------------------------------------------


def tool_maps_directions(
    _controller: PlaywrightController, args: Dict[str, Any]
) -> Dict[str, Any]:
    origin = args.get("from")
    destination = args.get("to")

    if not origin or not destination:
        return _result_error("'from' and 'to' parameters are required")

    try:
        page = _ensure_page(_controller)

        o = urllib.parse.quote_plus(str(origin))
        d = urllib.parse.quote_plus(str(destination))

        url = f"https://www.google.com/maps/dir/{o}/{d}"
        page.goto(url, timeout=args.get("timeout", 30000))

        page.wait_for_selector("div[role='main']", timeout=10000)

        return _result_ok(
            {
                "status": "directions_loaded",
                "from": origin,
                "to": destination,
                "url": page.url,
            }
        )
    except Exception as e:
        return _result_error(e)


# -----------------------------------------------------------
# Tool: Change travel mode (drive, walk, transit, bike)
# -----------------------------------------------------------


def tool_maps_set_mode(
    _controller: PlaywrightController, args: Dict[str, Any]
) -> Dict[str, Any]:
    mode = (args.get("mode") or "").lower()
    if mode not in ["drive", "walk", "transit", "bike"]:
        return _result_error("mode must be one of: drive, walk, transit, bike")

    try:
        page = _ensure_page(_controller)

        clicked = page.evaluate(
            """
            (mode) => {
                const labels = {
                    drive: ['Driving', 'Drive'],
                    walk: ['Walking', 'Walk'],
                    transit: ['Transit'],
                    bike: ['Bicycling', 'Bike']
                };

                const buttons = Array.from(document.querySelectorAll('button'));
                for (const btn of buttons) {
                    const txt = (btn.innerText || '').trim();
                    if (labels[mode].some(label => txt.includes(label))) {
                        btn.click();
                        return true;
                    }
                }
                return false;
            }
            """,
            mode,
        )

        if clicked:
            return _result_ok({"status": "mode_changed", "mode": mode})
        else:
            return _result_error("could not find mode button")
    except Exception as e:
        return _result_error(e)


# -----------------------------------------------------------
# Tool: Extract place details (name, rating, address)
# -----------------------------------------------------------


def tool_maps_extract_details(
    _controller: PlaywrightController, args: Dict[str, Any]
) -> Dict[str, Any]:
    try:
        page = _ensure_page(_controller)

        data = page.evaluate(
            """
            () => {
                const getText = (sel) => {
                    const el = document.querySelector(sel);
                    return el ? el.innerText : null;
                };

                return {
                    name: getText('h1'),
                    rating: getText('div[role="img"][aria-label*="stars"]'),
                    address: getText('button[data-item-id="address"]'),
                };
            }
            """
        )

        return _result_ok({"status": "extracted", "details": data, "url": page.url})
    except Exception as e:
        return _result_error(e)


_MAPS_TOOL_SPECS = {
    "maps_where": ToolSpec(
        name="maps_where",
        description="Where is place on Google Maps. Direction to location on google maps",
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string"}, "timeout": {"type": "integer"}},
        },
    ),
    "maps_open_place": ToolSpec(
        name="maps_open_place",
        description="Open the first place result from the current Google Maps search.",
        parameters={"type": "object", "properties": {}},
    ),
    "maps_directions": ToolSpec(
        name="maps_directions",
        description="Get directions between two locations.",
        parameters={
            "type": "object",
            "properties": {
                "from": {"type": "string"},
                "to": {"type": "string"},
                "timeout": {"type": "integer"},
            },
        },
    ),
    "maps_set_mode": ToolSpec(
        name="maps_set_mode",
        description="Set travel mode for current directions (drive, walk, transit, bike).",
        parameters={"type": "object", "properties": {"mode": {"type": "string"}}},
    ),
    "maps_extract_details": ToolSpec(
        name="maps_extract_details",
        description="Extract details (name, rating, address) from an open place page.",
        parameters={"type": "object", "properties": {}},
    ),
}

maps_tools = [
    ToolDefinition("maps_where", tool_maps_where, _MAPS_TOOL_SPECS["maps_where"]),
    ToolDefinition(
        "maps_open_place", tool_maps_open_place, _MAPS_TOOL_SPECS["maps_open_place"]
    ),
    ToolDefinition(
        "maps_directions", tool_maps_directions, _MAPS_TOOL_SPECS["maps_directions"]
    ),
    ToolDefinition(
        "maps_set_mode", tool_maps_set_mode, _MAPS_TOOL_SPECS["maps_set_mode"]
    ),
    ToolDefinition(
        "maps_extract_details",
        tool_maps_extract_details,
        _MAPS_TOOL_SPECS["maps_extract_details"],
    ),
]
