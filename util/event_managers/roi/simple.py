"""
Handle ROIs in a simple manner.

- On any m5 workbegin, switch CPU and begin collecting stats
- On any m5 workend, cease stat collection and switch back to the
  fast-forward processor
"""

from typing import override

from gem5.simulate.exit_event import ExitEvent
from termcolor import colored

from util.event_managers.event_manager import (
    EventHandler,
    EventHandlerDict,
    EventManager,
    EventTime,
)


class SimpleROIManager(EventManager):
    def __init__(self, verbose: bool = False) -> None:
        """Initialize the SimpleROIManager.

        :param verbose: Whether to print verbose information"""
        super().__init__(verbose=verbose)

    def _handle_workbegin(self) -> EventHandler:
        """Handle workbegin event, by switching to the timing processor
        and collecting stats.

        :yield True if the simulation should end, false otherwise
        """
        while True:
            current_time: EventTime = self.get_current_time()
            current_ins: int = current_time.instruction or 0

            print(
                colored(
                    f"***Instruction {current_ins:,}:",
                    color="blue",
                    attrs=["bold"],
                ),
                colored(
                    "Entering ROI, switching to detailed processor on m5.workbegin.",
                    color="blue",
                ),
            )

            self.switch_processor()
            self.reset_stats()
            yield False  # Continue simulation

    def _handle_workend(self) -> EventHandler:
        """Handle workend event, by switching to the fast-forward
        processor and ceasing stat collection.

        :yield True if the simulation should end, false otherwise
        """
        while True:
            current_time: EventTime = self.get_current_time()
            current_ins: int = current_time.instruction or 0

            print(
                colored(
                    f"***Instruction {current_ins:,}:",
                    color="blue",
                    attrs=["bold"],
                ),
                colored(
                    "Exiting ROI, switching to fast-forward processor on m5.workend",
                    color="blue",
                ),
            )

            self.dump_stats()
            self.reset_stats()
            self.switch_processor()
            yield False  # Continue simulation

    def _handle_exit(self) -> EventHandler:
        """Handle exit event, by ending the simulation.

        :yield True if the simulation should end, false otherwise
        """
        current_time = self.get_current_time()
        current_ins: int = current_time.instruction or 0

        print(
            colored(
                f"***Instruction {current_ins:,}:",
                color="blue",
                attrs=["bold"],
            ),
            colored(
                "Exiting simulation on m5.exit.",
                color="blue",
            ),
        )

        self.dump_stats()
        yield True

    @override
    def get_event_handlers(self) -> EventHandlerDict:
        """Get a dictionary of event types -> handlers.

        :return A dictionary of this manager's event handlers
        """
        return {
            ExitEvent.WORKBEGIN: self._handle_workbegin(),
            ExitEvent.WORKEND: self._handle_workend(),
            ExitEvent.EXIT: self._handle_exit(),
        }
