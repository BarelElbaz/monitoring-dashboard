# Monitoring Dashboard

A cross-platform monitoring dashboard that automatically rotates between configured web pages using Selenium.

## Features
- Multi-tab support for monitoring multiple pages
- Automatic page scrolling
- Periodic refresh to prevent timeouts
- Automatic browser session management
- Support for Nagios authentication

## Prerequisites
- Python 3.7 or higher
- Chrome browser installed
- pip (Python package manager)

## Quick Start

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Build the executable:
```bash
python build.py
```
4. Find the executable in the `dist` directory
5. Run the executable - it will use settings from `config.json`

## Configuration

Edit `config.json` to customize:
- URLs to monitor
- Browser settings
- Refresh intervals
- Scroll behavior
- Nagios credentials (if needed)

## Troubleshooting

If you encounter any issues:
1. Check the log file (`dashboard_rotator.log`)
2. Verify Chrome is installed and accessible
3. Ensure `config.json` is in the same directory as the executable
