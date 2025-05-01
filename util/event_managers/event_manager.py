"""
Parent class for all event managers with some functions
that must be overridden
"""

from abc import ABC, abstractmethod
from typing import Callable, Dict, Final, Generator, List, Optional, Union

import m5
from gem5.simulate.exit_event import ExitEvent
from gem5.simulate.simulator import Simulator

from util.string import vprint

# The type of an event handler. Each time a handler is called, it generates
# a bool which tells gem5 whether to stop the simulation.
EventHandler = Generator[Optional[bool], None, None]

# The type that gem5's Simulator.on_exit_event parameter expects to receive.
# We only use Dict[ExitEvent, EventHandler] here.
EventHandlerDict = Optional[
    Dict[
        ExitEvent,
        Union[
            Generator[Optional[bool], None, None],
            List[Callable],
            Callable,
        ],
    ]
]


class EventTime:
    """Represent the time of an event in gem5.

    Event times consist of three units, any combination of
    which can be present:
        instruction : The instruction number of the event.
        cycle       : The cycle number of the event.
        tick        : The tick number of the event.

    If more than one unit is defined, the event time will represent when
    the first defined unit of time is reached.
    """

    def __init__(
        self,
        instruction: Optional[int] = None,
        cycle: Optional[int] = None,
        tick: Optional[int] = None,
    ) -> None:
        """Initialze the event time.

        :param instruction Instruction number of the event
        :param cycle Cycle number of the event
        :param tick Tick number of the event
        """
        self.instruction: Optional[int] = instruction
        self.cycle: Optional[int] = cycle
        self.tick: Optional[int] = tick

    def add(self, other: "EventTime"):
        """Add two event times together.

        :param other The other event time to add.
        """
        sum_instruction: Optional[int] = None
        sum_cycle: Optional[int] = None
        sum_tick: Optional[int] = None

        if self.instruction is not None and other.instruction is not None:
            sum_instruction = self.instruction + other.instruction

        if self.cycle is not None and other.cycle is not None:
            sum_cycle = self.cycle + other.cycle

        if self.tick is not None and other.tick is not None:
            sum_tick = self.tick + other.tick

        return EventTime(
            instruction=sum_instruction,
            cycle=sum_cycle,
            tick=sum_tick,
        )

    def __add__(self, other: "EventTime"):
        return self.add(other)

    def __str__(self):
        return f"EventTime(instruction={self.instruction}, cycle={self.cycle}, tick={self.tick})"


class EventCoordinator:
    """Manage multiple event managers for a simulator."""

    def __init__(
        self,
        event_managers: List["EventManager"],
        verbose: bool = False,
    ):
        """Initialize the event coordinator.

        :param managers List of event managers to coordiante
        :param verbose Whether to print verbose information
        """
        self._managers: Final[List[EventManager]] = event_managers
        self._verbose: Final[bool] = verbose

        # To be set in register()
        self._simulator: Optional[Simulator] = None

        # To be populated in register()
        # event manager -> event type -> generator
        self._handlers: List[EventHandlerDict] = []

        # Tracks total number of instructions executed, regardless of
        # stats resets.
        self.total_instructions: int = 0
        self.total_cycles: int = 0

    def get_event_handlers(self) -> EventHandlerDict:
        """Get dictionary of event types -> handlers.

        :return Dictionary of event handler functions
        """
        return {
            ExitEvent.CHECKPOINT: self._handle_unscheduled(ExitEvent.CHECKPOINT),
            ExitEvent.MAX_INSTS: self._handle_max_insts(),
            ExitEvent.SIMPOINT_BEGIN: self._handle_unscheduled(
                ExitEvent.SIMPOINT_BEGIN
            ),
            ExitEvent.WORKBEGIN: self._handle_unscheduled(ExitEvent.WORKBEGIN),
            ExitEvent.WORKEND: self._handle_unscheduled(ExitEvent.WORKEND),
            ExitEvent.EXIT: self._handle_unscheduled(ExitEvent.EXIT),
        }

    def register(self, simulator: Simulator) -> None:
        """Register a simulator to this coordinator.

        :param simulator The simulator to register
        """
        vprint("Registering simulator")
        self._simulator = simulator

        # Register managers and get their handlers
        for manager in self._managers:
            manager.register(self)
            self._handlers.append(manager.get_event_handlers())

        # Schedule first event(s)
        self._schedule()

    def reset_stats(self) -> None:
        """Reset the simulator's stats."""
        if self._simulator is None:
            vprint("Can't reset stats, no simulator")
            return

        # Track total instructions and cycles
        # TODO: Use v24.0 get_simstat() function instead
        stats = self._simulator.get_simstats()

        self.total_instructions += int(stats["simInsts"].value)
        self.total_cycles += 0  # TODO: Implement cycles

        vprint(f"Simulation instructions: {stats['simInsts'].value}")
        vprint(f"Total instructions: {self.total_instructions}")
        m5.stats.reset()

    def dump_stats(self) -> None:
        """Dump the simulator's stats."""
        if self._simulator is None:
            vprint("Can't dump stats, no simulator")
            return

        vprint("Dumping stats")
        m5.stats.dump()

    def get_current_time(self) -> EventTime:
        """Get the current time for this coordinator's simulator.

        :return The current time of the simulator
        """
        if self._simulator is None or not self._simulator._instantiated:
            # Simulator not instantiated
            return EventTime(instruction=0, cycle=0, tick=0)

        # TODO: Use v24.0 get_simstat() function instead
        stats = self._simulator.get_simstats()

        return EventTime(
            instruction=self.total_instructions + int(stats["simInsts"].value),
            cycle=self.total_cycles,  # TODO: Implement cycles
            tick=0,  # TODO: Implement ticks
        )

    def _schedule(self) -> None:
        """Schedule the next event from the underlying managers."""
        current_time: Final[EventTime] = self.get_current_time()

        # For each time unit, find the closest event and schedule it
        closest_event: EventTime = EventTime()

        for manager in self._managers:
            next_event: EventTime = manager.get_next_event()

            if next_event.instruction is not None and (
                closest_event.instruction is None
                or closest_event.instruction > next_event.instruction
            ):
                closest_event.instruction = next_event.instruction

            if next_event.cycle is not None and (
                closest_event.cycle is None or closest_event.cycle > next_event.cycle
            ):
                closest_event.cycle = next_event.cycle

            if next_event.tick is not None and (
                closest_event.tick is None or closest_event.tick > next_event.tick
            ):
                closest_event.tick = next_event.tick

        vprint(f"Current time: {current_time}")
        vprint(f"Next event time: {closest_event}")

        # Schedule the next event for each type
        if (
            closest_event.instruction is not None
            and current_time.instruction is not None
            and self._simulator is not None
        ):
            # Schedule the next event
            #
            # Have a small minimum time to avoid imprecision of KVM core
            self._simulator.schedule_max_insts(closest_event.instruction)

        if closest_event.cycle is not None and current_time.cycle is not None:
            raise NotImplementedError("Cycle scheduling not implemented yet.")

        if closest_event.tick is not None and current_time.tick is not None:
            raise NotImplementedError("Tick scheduling not implemented yet.")

    def _handle_max_insts(self) -> EventHandler:
        """Handle MAX_INSTS events.

        :yield True if the simulation should end, false otherwise
        """
        while True:
            curr_time: EventTime = self.get_current_time()
            res: bool = False
            vprint(f"Current time: {curr_time}")

            # Loop through each event manager
            for manager_index in range(len(self._managers)):
                event_time = self._managers[manager_index].get_next_event()
                event_handlers = self._handlers[manager_index]

                # See if the event manager supports this event type
                # and it's time to handle an event.
                #
                # If so, handle the event.
                if (
                    event_handlers is not None
                    and ExitEvent.MAX_INSTS in event_handlers
                    and event_time is not None
                    and event_time.instruction is not None
                    and curr_time.instruction is not None
                    and event_time.instruction <= curr_time.instruction
                ):
                    # Trigger event
                    manager_res: Optional[bool] = next(
                        event_handlers[ExitEvent.MAX_INSTS]  # type: ignore
                    )
                    res = res | (manager_res or False)

            # Schedule the next event
            self._schedule()

            # Yield result
            vprint("Ending simulation" if res else "Continuing simulation")
            yield res

    def _handle_unscheduled(self, event_type: ExitEvent) -> EventHandler:
        """Handle unscheduled events (workend, workbegin, etc.)

        :yield Whether the simulation should end after this event
        """
        while True:
            res: bool = False
            vprint(f"Received event {event_type}")

            # Loop through each event manager
            for manager_index in range(len(self._managers)):
                event_handlers = self._handlers[manager_index]

                # See if the event manager supports this event type.
                # If so, handle the event.
                if event_handlers is not None and event_type in event_handlers:
                    manager_res: Optional[bool] = next(
                        self._handlers[manager_index][event_type]  # type: ignore
                    )
                    res = res | (True if manager_res is None else manager_res)

            # Schedule the next event
            self._schedule()

            # Yield result
            vprint("Ending simulation" if res else "Continuing simulation")
            yield res


class EventManager(ABC):
    """Abstract class for managing events in a simulator.

    Child classes must implement get_event_handlers()
    """

    def __init__(self, verbose: bool = False) -> None:
        """Initialize the event manager.

        :param verbose Whether to print verbose information"""
        self._coordinator: Optional[EventCoordinator] = None
        self._next_event: EventTime = EventTime()
        self._verbose: Final[bool] = verbose

    @abstractmethod
    def get_event_handlers(self) -> EventHandlerDict:
        """Get dictionary of event types -> handlers.

        :return A dictionary of this manager's event handlers
        """
        pass

    def set_next_event(self, interval: EventTime) -> None:
        """Set the time of the next event.

        :param interval The time, relative to the current time, at which
                        this manager's next event should happen
        """
        self._next_event = interval

    def clear_next_event(self) -> None:
        """Clear the time of the next event."""
        self._next_event = EventTime()

    def get_next_event(self) -> EventTime:
        """Get the time of the next event.

        :return The time at which this manager's next event should happen
        """
        return self._next_event

    def get_current_time(self) -> EventTime:
        """Get the current time of the simulator.

        :return The current time of the simulator
        """
        return (
            self._coordinator.get_current_time()
            if self._coordinator
            else EventTime(instruction=0, cycle=0, tick=0)
        )

    def register(self, coordinator: EventCoordinator) -> None:
        """Register an event coordinator with this manager.

        :param simulator The simulator to register
        """
        self._coordinator = coordinator

    def reset_stats(self) -> None:
        """Reset the stats."""
        if self._coordinator is None:
            vprint("Can't reset stats, no coordinator")
            return

        self._coordinator.reset_stats()

    def dump_stats(self) -> None:
        """Dump the stats."""
        if self._coordinator is None:
            vprint("Can't dump stats, no coordinator")
            return

        self._coordinator.dump_stats()

    def switch_processor(self) -> None:
        """Switch the processor type, if using a switchable processor

        :raise ValueError If the processor is not switchable

        TODO: Move this method to EventCoordinator
        """
        # Validate simulator
        self.validate_simulator()

        # Get processor
        processor = self._coordinator._simulator._board.get_processor()  # type: ignore

        # Validate processor
        if not getattr(processor, "switch") or not callable(processor.switch):
            raise ValueError(
                f"Processor {processor} does not have a valid switch() method."
            )

        # Switch
        processor.switch()

    def validate_simulator(self) -> None:
        """Validate that the Simulator is ready.

        :raise ValueError If the simulator is not ready

        TODO: Move this method to EventCoordinator
        """
        if self._coordinator is None:
            raise ValueError(
                "EventCoordinator is not set. Register this manager with a "
                "coordinator before calling simulator.run()."
            )
        if self._coordinator._simulator is None:
            raise ValueError("EventCoordinator's simulator is not set.")
        if not self._coordinator._simulator._instantiated:
            raise ValueError("EventCoordinator's simulator is not instantiated.")
