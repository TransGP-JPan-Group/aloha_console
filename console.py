from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer, Horizontal, Vertical
from textual.widgets import Header, Label, RichLog, Button, Footer, Static
from textual.binding import Binding
from textual.reactive import reactive
from textual.message import Message
import subprocess
import threading
import signal
import os
from pathlib import Path


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
    script_command = reactive([])
    is_running = reactive(False)

    def __init__(self, name: str, command: list[str], id: str | None = None):
        super().__init__(id=id)
        self.script_name = name
        self.script_command = command
        self.process = None
        self.log_thread = None

    def watch_is_running(self, old_value: bool, new_value: bool) -> None:
        """Handle changes in is_running state."""
        self.post_message(self.RunningStatusChanged(self, new_value))

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield RichLog(id="output", wrap=True, markup=True, highlight=True)

    def launch_script(self):
        """Launch the script."""
        if self.process is not None:
            return
        
        try:
            self.app.log(f"Launching {self.script_name}", command=self.script_command)
            self.process = subprocess.Popen(
                self.script_command,
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
        self.app.log(f"Starting output monitoring for {self.script_name}")
        while self.is_running and self.process:
            try:
                line = self.process.stdout.readline()
                if not line and self.process:
                    if self.process.poll() is not None:
                        self.app.log(f"{self.script_name} process ended")
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

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        with Horizontal(id="control-panel"):
            yield Button("Launch Core", id="launch", variant="success")
            yield Button("Stop Core", id="stop", variant="error")
        yield ScriptRunner(
            "Aloha Core",
            ["./mock_script.sh"],
            id="core-runner"
        )
        yield Footer()

    def on_mount(self) -> None:
        """Handle the app start up"""
        self.query_one("#core-runner #output").write("Welcome to Aloha Console! 🌺\n")
        # Initialize button states
        self.query_one("#stop").disabled = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        runner = self.query_one(ScriptRunner)
        if event.button.id == "launch":
            runner.launch_script()
        elif event.button.id == "stop":
            runner.stop_script()

    def on_script_runner_running_status_changed(self, event: ScriptRunner.RunningStatusChanged) -> None:
        """Handle script runner state changes."""
        is_running = event.value
        launch_button = self.query_one("#launch")
        stop_button = self.query_one("#stop")
        
        # Toggle visibility using CSS classes
        launch_button.disabled = is_running
        stop_button.disabled = not is_running
        launch_button. set_class(is_running, "hidden")
        stop_button. set_class(not is_running, "hidden")

    def action_clear(self) -> None:
        """Clear the console output."""
        pass

    def on_unmount(self) -> None:
        """Clean up when the app is closing."""
        pass


if __name__ == "__main__":
    app = AlohaConsole()
    app.run()
