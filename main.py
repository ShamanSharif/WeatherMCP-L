from weather import weather_mcp

def main():
    # Run the server
    weather_mcp.run(transport='stdio')

if __name__ == "__main__":
    main()
