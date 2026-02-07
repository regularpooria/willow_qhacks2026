"""Playwright weather tool wrappers for LLM-facing tool metadata.

Provides:
- tool_curr_weather_location: Get current weather for a location
- tool_future_weather_location: Get future weather forecast for a location and date
"""

from typing import Dict, Any
import urllib.parse

from public.tools.util_classes import (
    _result_error,
    _result_ok,
    ToolSpec,
    ToolDefinition,
)
from public.tools.YoutubeController import PlaywrightController


def tool_curr_weather_location(
    _controller: PlaywrightController, args: Dict[str, Any]
) -> Dict[str, Any]:
    """Get current weather for a specified location."""
    location = args.get("location")
    if not location:
        return _result_error("'location' parameter is required")
    try:
        if _controller.page is None:
            _controller.start(headless=False)
        page = _controller.page
        if page is None:
            return _result_error("failed to start browser")

        q = urllib.parse.quote_plus(str(location))
        url = f"https://weather.com/weather/today/l/{q}"
        page.goto(url, timeout=args.get("timeout", 30000))

        # Wait for weather content to load
        try:
            page.wait_for_selector("[data-testid='TemperatureValue']", timeout=8000)
        except Exception:
            pass

        # Extract current weather info
        weather_info = page.evaluate(
            """
		() => {
			const temp = document.querySelector('[data-testid="TemperatureValue"]')?.innerText || 'N/A';
			const condition = document.querySelector('[data-testid="wxPhrase"]')?.innerText || 'N/A';
			const location = document.querySelector('h1')?.innerText || 'N/A';
			return { location, temperature: temp, condition };
		}
		"""
        )

        return _result_ok(
            {"status": "retrieved", "location": location, "data": weather_info}
        )
    except Exception as e:
        return _result_error(e)


def tool_future_weather_location(
    _controller: PlaywrightController, args: Dict[str, Any]
) -> Dict[str, Any]:
    """Get future weather forecast for a specified location on a given date."""
    location = args.get("location")
    date = args.get("date")
    if not location or not date:
        return _result_error("'location' and 'date' parameters are required")
    try:
        if _controller.page is None:
            _controller.start(headless=False)
        page = _controller.page
        if page is None:
            return _result_error("failed to start browser")

        q = urllib.parse.quote_plus(str(location))
        url = f"https://weather.com/weather/tenday/l/{q}"
        page.goto(url, timeout=args.get("timeout", 30000))

        # Wait for forecast section
        try:
            page.wait_for_selector("[data-testid='DailyForecast']", timeout=8000)
        except Exception:
            pass

        # Extract forecast info for the specified date
        forecast_info = page.evaluate(
            f"""
		() => {{
			const forecasts = document.querySelectorAll('[data-testid="DaypartDetails"]');
			const targetDate = '{date}'.toLowerCase();
			for (const forecast of forecasts) {{
				const dateEl = forecast.querySelector('[data-testid="detailsDateRange"]');
				const highTempEl = forecast.querySelector('[data-testid="highTempValue"]');
				const lowTempEl = forecast.querySelector('[data-testid="lowTempValue"]');
				const condEl = forecast.querySelector('[data-testid="wxPhrase"]');
				if (dateEl && dateEl.innerText.toLowerCase().includes(targetDate)) {{
					return {{
						date: dateEl?.innerText || 'N/A',
						high_temp: highTempEl?.innerText || 'N/A',
						low_temp: lowTempEl?.innerText || 'N/A',
						condition: condEl?.innerText || 'N/A'
					}};
				}}
			}}
			return {{ date: 'not found', high_temp: 'N/A', low_temp: 'N/A', condition: 'N/A' }};
		}}
		"""
        )

        return _result_ok(
            {
                "status": "retrieved",
                "location": location,
                "requested_date": date,
                "data": forecast_info,
            }
        )
    except Exception as e:
        return _result_error(e)


# Define specs for each weather tool
_WEATHER_TOOL_SPECS = {
    "curr_weather_location": ToolSpec(
        name="curr_weather_location",
        description="Get current weather for a specified location.",
        parameters={"type": "object", "properties": {"location": {"type": "string"}}},
    ),
    "future_weather_location": ToolSpec(
        name="future_weather_location",
        description="Get future weather forecast for a specified location on a given date.",
        parameters={
            "type": "object",
            "properties": {"location": {"type": "string"}, "date": {"type": "string"}},
        },
    ),
}

# Export tool definitions for registration in base tools.py
weather_tools = [
    ToolDefinition(
        name="curr_weather_location",
        func=tool_curr_weather_location,
        spec=_WEATHER_TOOL_SPECS["curr_weather_location"],
    ),
    ToolDefinition(
        name="future_weather_location",
        func=tool_future_weather_location,
        spec=_WEATHER_TOOL_SPECS["future_weather_location"],
    ),
]

# NOTE: Weather is broken since the weather.com/l needs a UUID instead of a location string.
