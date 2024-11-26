from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer, Horizontal, Vertical
from textual.widgets import Header, Label, RichLog, Button, Footer, Static, Tabs, Tab, Input
from textual.binding import Binding
from textual.reactive import reactive
from textual.message import Message
from textual import on
import subprocess
import threading
import signal
import os
import json
from pathlib import Path
from string import Template

class ScriptConfig:
    """Configuration for a script runner."""
    def __init__(self, name: str, command_template: str):
        self.name = name
        self.command_template = command_template

    def get_command(self, **kwargs) -> list[str]:
        """Get the command with template variables replaced."""
        # Use Template for safe substitution
        template = Template(self.command_template)
        try:
            command_str = template.safe_substitute(**kwargs)
            return command_str.split()
        except KeyError as e:
            raise ValueError(f"Missing required template variable: {e}")

class ScriptRunner(Static):
    """A widget that manages script execution and output display."""

    class RunningStatusChanged(Message):
        """Message sent when is_running state changes."""
        def __init__(self, runner: "ScriptRunner", value: bool) -> None:
            self.runner = runner
            self.value = value
            super().__init__()

    # Reactive properties
    script_name = reactive("Unnamed Script")
    is_running = reactive(False)

    def __init__(self, config: ScriptConfig, id: str, classes: str | None = None):
        super().__init__(id=id, classes=classes)
        self.script_name = config.name
        self.config = config
        self.process = None
        self.log_thread = None

    def watch_is_running(self, old_value: bool, new_value: bool) -> None:
        """Handle changes in is_running state."""
        self.post_message(self.RunningStatusChanged(self, new_value))

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield RichLog(id="output", wrap=True, markup=True, highlight=True)

    def launch_script(self, **kwargs):
        """Launch the script with template variables."""
        if self.process is not None:
            return
        
        try:
            command = self.config.get_command(**kwargs)
            self.app.log(f"Launching {self.script_name}", command=command)
            
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                preexec_fn=os.setsid,
                bufsize=1,
                universal_newlines=True
            )
            
            self.is_running = True
            
            # Start log monitoring thread
            self.log_thread = threading.Thread(target=self._monitor_output, daemon=True)
            self.log_thread.start()
            
            self.query_one("#output").write(f"[green]{self.script_name} launched successfully![/]")
        except Exception as e:
            self.app.log.error(f"Failed to launch {self.script_name}", error=str(e))
            self.query_one("#output").write(f"[red]Failed to launch {self.script_name}: {str(e)}[/]")

    def stop_script(self):
        """Stop the script."""
        if self.process is None:
            return
        
        try:
            self.app.log(f"Stopping {self.script_name}")
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            self.process = None
            self.is_running = False
            
            self.query_one("#output").write(f"[yellow]{self.script_name} stopped.[/]")
        except Exception as e:
            self.app.log.error(f"Error stopping {self.script_name}", error=str(e))
            self.query_one("#output").write(f"[red]Error stopping {self.script_name}: {str(e)}[/]")

    def _monitor_output(self):
        """Monitor and log the script output."""
        self.app.log.debug(f"Starting output monitoring for {self.script_name}")
        while self.is_running and self.process:
            try:
                line = self.process.stdout.readline()
                if not line and self.process:
                    if self.process.poll() is not None:
                        self.app.log.debug(f"{self.script_name} process ended")
                        self.is_running = False
                        self.process = None
                        self.app.call_from_thread(self._handle_process_exit)
                    break
                
                self.app.log.debug(f"Script output", script=self.script_name, output=line.strip())
                self.app.call_from_thread(self._write_output, line.strip())
            except Exception as e:
                self.app.log.error(f"Error reading output", script=self.script_name, error=str(e))
                self.app.call_from_thread(
                    self._write_output,
                    f"[red]Error reading output: {str(e)}[/]"
                )

    def _write_output(self, text: str):
        """Write text to the output log in a thread-safe way."""
        self.query_one("#output").write(text)

    def _handle_process_exit(self):
        """Handle cleanup when the process exits."""
        self.query_one("#output").write(f"[yellow]{self.script_name} process finished.[/]")
        self.app.log(f"{self.script_name} process cleanup completed")

    def clear_output(self):
        """Clear the output log."""
        self.query_one("#output").clear()
    
    def on_unmount(self) -> None:
        """Clean up when the widget is unmount."""
        self.stop_script()


class AlohaConsole(App):
    """A mini console application for Aloha platform."""
    
    CSS_PATH = "console.tcss"

    BINDINGS = [
        Binding("ctrl+c,ctrl+q", "quit", "Quit", show=True),
        Binding("ctrl+k", "clear", "Clear", show=True),
    ]

    # Current episode number
    episode = reactive(0)

    def __init__(self):
        super().__init__()
        self.script_configs = self._load_config()

    def _load_config(self) -> dict[str, ScriptConfig]:
        """Load script configurations from config file."""
        try:
            with open("config.json", "r") as f:
                config_data = json.load(f)
            
            configs = {}
            for script_id, script_config in config_data["scripts"].items():
                configs[script_id] = ScriptConfig(
                    name=script_config["name"],
                    command_template=script_config["command"]
                )
            return configs
        except Exception as e:
            self.log.error(f"Failed to load config: {e}")
            return {}

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        with Horizontal(classes="control-panel"):
            yield Button("Launch Core", id="launch-core", variant="success")
            yield Button("Stop Core", id="stop-core", variant="error", classes="hidden")
            yield Button("Launch Sleep Arm", id="launch-sleep", variant="success")
            yield Button("Stop Sleep Arm", id="stop-sleep", variant="error", classes="hidden")
        with Horizontal(classes="control-panel"):
            yield Button("Launch Data Collection", id="launch-data", variant="success")
            yield Button("Stop Data Collection", id="stop-data", variant="error", classes="hidden")
            yield Label("Episode:")
            yield Input(id="episode-input", value="0", type="integer")
            yield Button("Next", id="next-button", variant="primary")
            
        yield Tabs(
            Tab("Core", id="core-tab"),
            Tab("Data Collection", id="data-tab"),
            Tab("Sleep Arm", id="sleep-tab"), 
        )
        yield ScriptRunner(
            self.script_configs["core"],
            id="core-runner",
        )
        yield ScriptRunner(
            self.script_configs["data"],
            id="data-runner",
            classes="hidden"
        )
        yield ScriptRunner(
            self.script_configs["sleep"],
            id="sleep-runner",
            classes="hidden"
        )
        yield Footer()

    def on_mount(self) -> None:
        """Handle the app start up"""
        # Welcome messages
        self.query_one("#core-runner #output").write("Welcome to Aloha Core! 🚀\n")
        self.query_one("#data-runner #output").write("Welcome to Data Collection! 📊\n")
        self.query_one("#sleep-runner #output").write("Welcome to Sleep Arm! 💤\n")

        # Set initial tab
        self._show_runner_for_tab("core-tab")

    def watch_episode(self, old_value: int, new_value: int) -> None:
        """Update episode input when episode number changes."""
        self.query_one("#episode-input").value = str(new_value)

    @on(Input.Changed, "#episode-input")
    def handle_episode_input(self, event: Input.Changed) -> None:
        """Handle episode input changes."""
        try:
            if event.validation_result.is_valid:
                self.episode = int(event.value)
        except ValueError:
            # Reset to previous value on invalid input
            self.app.log.error("Invalid episode number")
            event.input.value = str(self.episode)

    @on(Button.Pressed, "#next-button")
    def handle_next_button(self) -> None:
        """Handle next button press."""
        self.episode += 1
        self._launch_data_collection()
        self.query_one(Tabs).active = "data-tab"

    @on(Button.Pressed, "#launch-data")
    def handle_launch_data_button(self) -> None:
        """Handle launch data collection button press."""
        self._launch_data_collection()
        self.query_one(Tabs).active = "data-tab"

    @on(Button.Pressed, "#stop-data")
    def handle_stop_data_button(self) -> None:
        """Handle stop data collection button press."""
        runner = self.query_one("#data-runner", ScriptRunner)
        runner.stop_script()

    @on(Button.Pressed, "#launch-core")
    def handle_launch_core_button(self) -> None:
        """Handle launch core button press."""
        runner = self.query_one("#core-runner", ScriptRunner)
        runner.launch_script()
        self.query_one(Tabs).active = "core-tab"

    @on(Button.Pressed, "#stop-core")
    def handle_stop_core_button(self) -> None:
        """Handle stop core button press."""
        runner = self.query_one("#core-runner", ScriptRunner)
        runner.stop_script()

    @on(Button.Pressed, "#launch-sleep")
    def handle_launch_sleep_button(self) -> None:
        """Handle launch sleep arm button press."""
        runner = self.query_one("#sleep-runner", ScriptRunner)
        runner.launch_script()
        self.query_one(Tabs).active = "sleep-tab"

    @on(Button.Pressed, "#stop-sleep")
    def handle_stop_sleep_button(self) -> None:
        """Handle stop sleep arm button press."""
        runner = self.query_one("#sleep-runner", ScriptRunner)
        runner.stop_script()

    def _launch_data_collection(self) -> None:
        """Launch data collection with current episode number."""
        runner = self.query_one("#data-runner", ScriptRunner)
        runner.launch_script(episode=str(self.episode))

    @on(Tabs.TabActivated)
    def handle_tab_switch(self, event: Tabs.TabActivated) -> None:
        """Handle tab switching."""
        if event.tab:
            self._show_runner_for_tab(event.tab.id)

    def _show_runner_for_tab(self, tab_id: str) -> None:
        """Show the runner for the selected tab and hide others."""
        # Query all script runners
        script_runners = self.query(ScriptRunner)
        runner_id = tab_id.replace("-tab", "-runner")

        # Show the selected runner and hide others
        for runner in script_runners:
            runner.set_class(runner.id != runner_id, "hidden")

    @on(ScriptRunner.RunningStatusChanged)
    def handle_runner_status(self, event: ScriptRunner.RunningStatusChanged) -> None:
        """Handle script runner state changes."""
        runner_id = event.runner.id
        if not runner_id:
            return
            
        runner_type = runner_id.replace("-runner", "")
        launch_button = self.query_one(f"#launch-{runner_type}", Button)
        stop_button = self.query_one(f"#stop-{runner_type}", Button)
        
        # Toggle visibility using CSS classes
        launch_button.disabled = event.value
        stop_button.disabled = not event.value
        launch_button.set_class(event.value, "hidden")
        stop_button.set_class(not event.value, "hidden")

    def action_clear(self) -> None:
        """Clear the console output."""
        visible_runner = self.query(ScriptRunner).exclude(".hidden").first()
        if visible_runner:
            visible_runner.clear_output()

    def on_unmount(self) -> None:
        """Clean up when the app is closing."""
        pass


if __name__ == "__main__":
    app = AlohaConsole()
    app.run()
