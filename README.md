# Aloha Console

A terminal-based console application for managing Aloha platform scripts and processes. Built with Python and [Textual](https://textual.textualize.io/).

## Features

- Multi-tab interface for different script runners
- Real-time script output monitoring
- Episode-based data collection
- Beautiful TUI (Terminal User Interface)

## Setup

1. Create and activate a Python virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

The application uses a `config.json` file to define script configurations. Each script has a name and command template.

Example `config.json`:
```json
{
    "scripts": {
        "core": {
            "name": "Aloha Core",
            "command": "./mock_script.sh -c core"
        },
        "data": {
            "name": "Data Collection",
            "command": "./mock_script.sh -e ${episode}"
        },
        "sleep": {
            "name": "Sleep Arm",
            "command": "./mock_script.sh -s sleep"
        }
    }
}
```

Template variables (like `${episode}`) will be replaced with actual values when the script is launched.

## Usage

### Normal Mode

Run the application:
```bash
python console.py
```

### Development Mode

1. Start the Textual console in one terminal:
```bash
textual console
```

2. Run the application in dev mode in another terminal:
```bash
textual run --dev console.py
```

This will show debug logs in the Textual console.

## Controls

- **Core**
  - Launch/Stop Core: Control the core script
- **Data Collection**
  - Launch/Stop Data Collection: Control data collection
  - Episode Input: Set episode number
  - Next: Increment episode and launch data collection
- **Sleep Arm**
  - Launch/Stop Sleep Arm: Control sleep arm script

### Keyboard Shortcuts

- `Ctrl+C` or `Ctrl+Q`: Quit the application
- `Ctrl+K`: Clear current output

## Development

The application is built with Textual, a modern TUI framework for Python. Key components:

- `console.py`: Main application logic
- `console.tcss`: Textual CSS for styling
- `config.json`: Script configuration
- `mock_script.sh`: Example script for testing

## Troubleshooting

1. If scripts don't launch:
   - Check if script files exist and are executable
   - Verify script paths in `config.json`
   - Check console logs for error messages

2. If template variables don't work:
   - Ensure variables in config.json use `${variable}` format
   - Check if variables are being passed correctly

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
