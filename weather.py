from typing import Any
import os
import httpx
from datetime import datetime
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables from .env file
load_dotenv()

# Initialize FastMCP server
weather_mcp = FastMCP("weather")

# Constants
NWS_API_BASE = "https://api.weather.gov"
OPENWEATHER_API_BASE = "https://api.openweathermap.org/data/2.5"
USER_AGENT = "weather-app/1.0"

def get_openweather_api_key() -> str | None:
    """Get OpenWeatherMap API key from .env file."""
    return os.getenv("OPENWEATHER_API_KEY")

async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

async def make_openweather_request(url: str) -> dict[str, Any] | None:
    """Make a request to the OpenWeatherMap API with proper error handling."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
Event: {props.get('event', 'Unknown')}
Area: {props.get('areaDesc', 'Unknown')}
Severity: {props.get('severity', 'Unknown')}
Description: {props.get('description', 'No description available')}
Instructions: {props.get('instruction', 'No specific instructions provided')}
"""

@weather_mcp.tool()
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state.

    Args:
        state: Two-letter US state code (e.g. CA, NY)
    """
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)

    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."

    if not data["features"]:
        return "No active alerts for this state."

    alerts = [format_alert(feature) for feature in data["features"]]
    return "\n---\n".join(alerts)

@weather_mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    api_key = get_openweather_api_key()
    if not api_key:
        return "Error: OPENWEATHER_API_KEY not found in .env file. Please add it to your .env file."

    # Use OpenWeatherMap forecast API
    forecast_url = f"{OPENWEATHER_API_BASE}/forecast?lat={latitude}&lon={longitude}&appid={api_key}&units=metric"
    forecast_data = await make_openweather_request(forecast_url)

    if not forecast_data:
        return "Unable to fetch forecast data for this location."

    if "cod" in forecast_data and forecast_data["cod"] != "200":
        error_msg = forecast_data.get("message", "Unknown error")
        return f"Unable to fetch forecast: {error_msg}"

    # Format the forecast periods
    forecasts = []
    city_name = forecast_data.get("city", {}).get("name", "Unknown")
    country = forecast_data.get("city", {}).get("country", "")
    
    location_info = f"Forecast for {city_name}"
    if country:
        location_info += f", {country}"
    forecasts.append(location_info)
    forecasts.append("=" * 50)

    # Group forecasts by day (OpenWeatherMap returns 3-hour intervals)
    periods = forecast_data.get("list", [])
    if not periods:
        return "No forecast data available."

    # Show next 5 periods (approximately 15 hours of forecast)
    for period in periods[:5]:
        dt = datetime.fromtimestamp(period["dt"])
        temp = period["main"]["temp"]
        feels_like = period["main"]["feels_like"]
        humidity = period["main"]["humidity"]
        weather_desc = period["weather"][0]["description"].title()
        wind_speed = period.get("wind", {}).get("speed", 0)
        wind_deg = period.get("wind", {}).get("deg", 0)
        
        # Convert wind direction from degrees to cardinal direction
        directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                     "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        wind_direction = directions[int((wind_deg + 11.25) / 22.5) % 16] if wind_deg else "N/A"
        
        forecast = f"""
{dt.strftime('%A, %B %d at %I:%M %p')}:
Temperature: {temp}°C (feels like {feels_like}°C)
Weather: {weather_desc}
Humidity: {humidity}%
Wind: {wind_speed} m/s {wind_direction}
"""
        forecasts.append(forecast)

    return "\n".join(forecasts)


